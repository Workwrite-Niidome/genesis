"""GENESIS v3 AI-Powered Asset Generation API routes.

Provides endpoints for generating skyboxes (via Blockade Labs) and
3D models (via Meshy) for the Japanese shrine world.  All endpoints
are admin-only and require the corresponding API key to be configured.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Resolve the asset output directories relative to the frontend/public folder.
# When running inside Docker the project root is typically mounted at /app,
# but we derive the path dynamically from this file's location so it also
# works in local development.
# ---------------------------------------------------------------------------
_BACKEND_APP_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
_PROJECT_ROOT = _BACKEND_APP_DIR.parent                           # genesis/
_FRONTEND_PUBLIC = _PROJECT_ROOT / "frontend" / "public"

SKYBOX_DIR = _FRONTEND_PUBLIC / "assets" / "skybox"
MODELS_DIR = _FRONTEND_PUBLIC / "assets" / "models"
TEXTURES_DIR = _FRONTEND_PUBLIC / "assets" / "textures"

# Polling configuration
POLL_INTERVAL_SECONDS = 5
POLL_MAX_ATTEMPTS = 120  # 10 minutes max

# HTTP timeout for long-running downloads
HTTP_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class GenerateSkyboxRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=3,
        max_length=600,
        description="Text description of the skybox to generate",
    )
    style: str = Field(
        default="anime_art_style",
        description="Skybox style name (mapped to style id internally)",
    )


class GenerateModelRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=3,
        max_length=600,
        description="Text description of the 3D model to generate",
    )
    type: str = Field(
        default="object",
        description="Logical type tag used in the output filename",
    )
    negative_prompt: str = Field(
        default="low quality, blurry, distorted",
        description="Negative prompt to steer generation away from unwanted traits",
    )


class AssetResponse(BaseModel):
    status: str
    url: str


class AssetListResponse(BaseModel):
    skyboxes: list[str]
    models: list[str]
    textures: list[str]


class GenerateAllResponse(BaseModel):
    status: str
    skybox: Optional[AssetResponse] = None
    models: list[AssetResponse] = []
    errors: list[str] = []


# ---------------------------------------------------------------------------
# Style ID mapping
# ---------------------------------------------------------------------------

SKYBOX_STYLE_IDS: dict[str, int] = {
    "anime_art_style": 2,
    "fantasy_landscape": 5,
    "sci_fi": 9,
    "realistic": 14,
    "dreamscape": 19,
}


# ---------------------------------------------------------------------------
# Helper: ensure API key is present
# ---------------------------------------------------------------------------

def _require_blockade_key() -> str:
    key = settings.BLOCKADE_LABS_API_KEY
    if not key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Blockade Labs API key is not configured. "
                   "Set BLOCKADE_LABS_API_KEY in your environment.",
        )
    return key


def _require_meshy_key() -> str:
    key = settings.MESHY_API_KEY
    if not key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Meshy API key is not configured. "
                   "Set MESHY_API_KEY in your environment.",
        )
    return key


# ---------------------------------------------------------------------------
# Helper: ensure output directories exist
# ---------------------------------------------------------------------------

def _ensure_dirs() -> None:
    SKYBOX_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    TEXTURES_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Blockade Labs (Skybox) generation logic
# ---------------------------------------------------------------------------

async def _generate_skybox(prompt: str, style: str) -> AssetResponse:
    """Full flow: submit -> poll -> download -> save."""
    api_key = _require_blockade_key()
    _ensure_dirs()

    style_id = SKYBOX_STYLE_IDS.get(style, 2)

    logger.info("Submitting skybox generation request: prompt=%r style=%s (id=%d)", prompt, style, style_id)

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        # Step 1: Submit generation request
        submit_resp = await client.post(
            "https://api.blockadelabs.com/v1/skybox",
            headers={"x-api-key": api_key},
            json={"prompt": prompt, "skybox_style_id": style_id},
        )
        if submit_resp.status_code != 200:
            detail = submit_resp.text[:500]
            logger.error("Blockade Labs submit failed (%d): %s", submit_resp.status_code, detail)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Blockade Labs API error ({submit_resp.status_code}): {detail}",
            )

        submit_data = submit_resp.json()
        request_id = submit_data.get("id")
        if not request_id:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Blockade Labs returned no request id.",
            )

        logger.info("Skybox request submitted: id=%s", request_id)

        # Step 2: Poll until complete
        file_url: Optional[str] = None
        for attempt in range(POLL_MAX_ATTEMPTS):
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

            poll_resp = await client.get(
                f"https://api.blockadelabs.com/v1/imagine/requests/{request_id}",
                headers={"x-api-key": api_key},
            )
            if poll_resp.status_code != 200:
                logger.warning("Skybox poll attempt %d failed: %d", attempt, poll_resp.status_code)
                continue

            poll_data = poll_resp.json()
            req_status = poll_data.get("request", poll_data).get("status", "")

            if req_status == "complete":
                file_url = poll_data.get("request", poll_data).get("file_url")
                logger.info("Skybox generation complete: file_url=%s", file_url)
                break
            elif req_status in ("error", "failed", "abort"):
                error_msg = poll_data.get("request", poll_data).get("error_message", "Unknown error")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Skybox generation failed: {error_msg}",
                )
            else:
                logger.debug("Skybox poll attempt %d: status=%s", attempt, req_status)

        if not file_url:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Skybox generation timed out after polling.",
            )

        # Step 3: Download the image
        dl_resp = await client.get(file_url)
        if dl_resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to download generated skybox image.",
            )

        # Step 4: Save to disk
        filename = f"skybox_{request_id}_{int(time.time())}.jpg"
        filepath = SKYBOX_DIR / filename
        filepath.write_bytes(dl_resp.content)
        logger.info("Skybox saved: %s (%d bytes)", filepath, len(dl_resp.content))

        return AssetResponse(status="ok", url=f"/assets/skybox/{filename}")


# ---------------------------------------------------------------------------
# Meshy (3D model) generation logic
# ---------------------------------------------------------------------------

async def _generate_model(prompt: str, model_type: str, negative_prompt: str) -> AssetResponse:
    """Full flow: submit -> poll -> download -> save."""
    api_key = _require_meshy_key()
    _ensure_dirs()

    logger.info("Submitting 3D model generation: prompt=%r type=%s", prompt, model_type)

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        # Step 1: Submit generation request
        submit_resp = await client.post(
            "https://api.meshy.ai/openapi/v2/text-to-3d",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "mode": "preview",
                "prompt": prompt,
                "negative_prompt": negative_prompt,
            },
        )
        if submit_resp.status_code not in (200, 201, 202):
            detail = submit_resp.text[:500]
            logger.error("Meshy submit failed (%d): %s", submit_resp.status_code, detail)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Meshy API error ({submit_resp.status_code}): {detail}",
            )

        submit_data = submit_resp.json()
        task_id = submit_data.get("result")
        if not task_id:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Meshy returned no task id.",
            )

        logger.info("Meshy task submitted: id=%s", task_id)

        # Step 2: Poll until complete
        glb_url: Optional[str] = None
        for attempt in range(POLL_MAX_ATTEMPTS):
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

            poll_resp = await client.get(
                f"https://api.meshy.ai/openapi/v2/text-to-3d/{task_id}",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if poll_resp.status_code != 200:
                logger.warning("Meshy poll attempt %d failed: %d", attempt, poll_resp.status_code)
                continue

            poll_data = poll_resp.json()
            task_status = poll_data.get("status", "")

            if task_status == "SUCCEEDED":
                model_urls = poll_data.get("model_urls", {})
                glb_url = model_urls.get("glb")
                logger.info("Meshy generation complete: glb_url=%s", glb_url)
                break
            elif task_status in ("FAILED", "EXPIRED"):
                error_msg = poll_data.get("task_error", {}).get("message", "Unknown error")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Meshy generation failed: {error_msg}",
                )
            else:
                logger.debug("Meshy poll attempt %d: status=%s", attempt, task_status)

        if not glb_url:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="3D model generation timed out after polling.",
            )

        # Step 3: Download the GLB file
        dl_resp = await client.get(glb_url)
        if dl_resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to download generated 3D model.",
            )

        # Step 4: Save to disk
        safe_type = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in model_type)
        filename = f"{safe_type}_{task_id}.glb"
        filepath = MODELS_DIR / filename
        filepath.write_bytes(dl_resp.content)
        logger.info("Model saved: %s (%d bytes)", filepath, len(dl_resp.content))

        return AssetResponse(status="ok", url=f"/assets/models/{filename}")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/generate-skybox",
    response_model=AssetResponse,
    summary="Generate a skybox image via Blockade Labs",
)
async def generate_skybox(body: GenerateSkyboxRequest):
    """Submit a prompt to Blockade Labs, poll until done, download the
    equirectangular image, and save it to the skybox assets directory.

    Requires BLOCKADE_LABS_API_KEY to be configured (returns 503 otherwise).
    Admin-only endpoint.
    """
    try:
        result = await _generate_skybox(body.prompt, body.style)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error during skybox generation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Skybox generation failed unexpectedly: {str(exc)}",
        )
    return result


@router.post(
    "/generate-model",
    response_model=AssetResponse,
    summary="Generate a 3D model via Meshy",
)
async def generate_model(body: GenerateModelRequest):
    """Submit a prompt to Meshy, poll until done, download the GLB file,
    and save it to the models assets directory.

    Requires MESHY_API_KEY to be configured (returns 503 otherwise).
    Admin-only endpoint.
    """
    try:
        result = await _generate_model(body.prompt, body.type, body.negative_prompt)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error during model generation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model generation failed unexpectedly: {str(exc)}",
        )
    return result


@router.get(
    "/list",
    response_model=AssetListResponse,
    summary="List all generated assets",
)
async def list_assets():
    """Return a listing of available skybox images, 3D models, and textures
    found in the frontend/public/assets directories.
    """
    _ensure_dirs()

    def _list_dir(directory: Path, extensions: set[str]) -> list[str]:
        results = []
        if directory.is_dir():
            for entry in sorted(directory.iterdir()):
                if entry.is_file() and entry.suffix.lower() in extensions:
                    # Return the public URL path
                    relative = entry.relative_to(_FRONTEND_PUBLIC)
                    results.append(f"/{relative.as_posix()}")
        return results

    skyboxes = _list_dir(SKYBOX_DIR, {".jpg", ".jpeg", ".png", ".hdr"})
    models = _list_dir(MODELS_DIR, {".glb", ".gltf", ".obj", ".fbx"})
    textures = _list_dir(TEXTURES_DIR, {".jpg", ".jpeg", ".png", ".hdr", ".ktx2"})

    return AssetListResponse(skyboxes=skyboxes, models=models, textures=textures)


@router.post(
    "/generate-all",
    response_model=GenerateAllResponse,
    summary="Generate a complete asset set for the Japanese shrine world",
)
async def generate_all():
    """Generate a full set of assets in parallel:

    - **Skybox**: twilight Japanese shrine scene
    - **Models**: torii gate, stone lantern, shrine building, cherry blossom tree

    Requires both BLOCKADE_LABS_API_KEY and MESHY_API_KEY.
    Each generation is run concurrently via ``asyncio.gather``.
    Partial failures are reported in the ``errors`` list; successful
    assets are still returned.

    Admin-only endpoint.
    """
    # Validate that at least one key is configured
    has_blockade = bool(settings.BLOCKADE_LABS_API_KEY)
    has_meshy = bool(settings.MESHY_API_KEY)

    if not has_blockade and not has_meshy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neither BLOCKADE_LABS_API_KEY nor MESHY_API_KEY is configured.",
        )

    # Define the generation tasks
    skybox_prompt = (
        "twilight Japanese shrine with purple sky, cherry blossoms, "
        "floating lanterns, mystical aurora, stars"
    )

    model_specs = [
        {
            "prompt": "Japanese torii gate, red wood, traditional shrine gate, clean geometry",
            "type": "torii_gate",
            "negative_prompt": "low quality, blurry, modern",
        },
        {
            "prompt": "Japanese stone lantern, toro, moss-covered granite, garden ornament, clean geometry",
            "type": "stone_lantern",
            "negative_prompt": "low quality, blurry, modern",
        },
        {
            "prompt": "Japanese shrine building, traditional wooden architecture, tiled roof, clean geometry",
            "type": "shrine_building",
            "negative_prompt": "low quality, blurry, modern, skyscraper",
        },
        {
            "prompt": "Cherry blossom tree, sakura, pink flowers, twisted trunk, Japanese garden, clean geometry",
            "type": "cherry_blossom_tree",
            "negative_prompt": "low quality, blurry, dead tree",
        },
    ]

    errors: list[str] = []
    skybox_result: Optional[AssetResponse] = None
    model_results: list[AssetResponse] = []

    # Build coroutine list
    tasks: list[asyncio.Task] = []
    task_labels: list[str] = []

    if has_blockade:
        tasks.append(asyncio.ensure_future(
            _generate_skybox(skybox_prompt, "anime_art_style")
        ))
        task_labels.append("skybox")
    else:
        errors.append("Skybox generation skipped: BLOCKADE_LABS_API_KEY not configured.")

    if has_meshy:
        for spec in model_specs:
            tasks.append(asyncio.ensure_future(
                _generate_model(spec["prompt"], spec["type"], spec["negative_prompt"])
            ))
            task_labels.append(f"model:{spec['type']}")
    else:
        errors.append("Model generation skipped: MESHY_API_KEY not configured.")

    # Run all tasks concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for label, result in zip(task_labels, results):
        if isinstance(result, Exception):
            error_detail = str(result)
            if isinstance(result, HTTPException):
                error_detail = result.detail
            logger.error("Asset generation failed for %s: %s", label, error_detail)
            errors.append(f"{label}: {error_detail}")
        elif label == "skybox":
            skybox_result = result
        else:
            model_results.append(result)

    overall_status = "ok" if not errors else ("partial" if (skybox_result or model_results) else "failed")

    return GenerateAllResponse(
        status=overall_status,
        skybox=skybox_result,
        models=model_results,
        errors=errors,
    )
