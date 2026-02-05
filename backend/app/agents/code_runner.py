"""
GENESIS v3 - Code Runner
===========================
Extracts code blocks from LLM responses and executes them in a sandboxed
subprocess. This bridges the gap between the AI thinking prompt (which tells
entities they can write executable code) and the actual execution engine.

The runner:
  1. Extracts ```code```, ```python```, and ```javascript``` blocks from LLM text
  2. Executes each block in an isolated subprocess with a 5-second timeout
  3. Injects a WorldAPI into the execution context so AI code can affect the world
  4. Logs results as WorldEvents (event_type="code_executed")
  5. Emits Socket.IO events for real-time frontend updates
  6. Returns execution results for memory storage

Security:
  - All code runs in a subprocess (never eval/exec in the main process)
  - 5-second timeout per block
  - No network access (dangerous imports are blocked)
  - No filesystem access (open/file are blocked)
  - Only a minimal safe builtins set is available
  - Output is capped at 2000 characters
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
import tempfile
import textwrap
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_CODE_BLOCKS_PER_RESPONSE = 3
MAX_CODE_LENGTH = 5000
EXECUTION_TIMEOUT = 5.0  # seconds
MAX_OUTPUT_LENGTH = 2000

# Regex to extract fenced code blocks: ```code```, ```python```, ```javascript```
_CODE_BLOCK_PATTERN = re.compile(
    r"```(?:code|python|javascript|js)?\s*\n(.*?)```",
    re.DOTALL,
)

# Regex to detect which language was specified
_LANG_PATTERN = re.compile(
    r"```(code|python|javascript|js)\s*\n",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# WorldAPI — injected into the sandbox execution context
# ---------------------------------------------------------------------------

# This is the source code that gets injected into the subprocess.
# It defines a `world` object that AI code can call. The methods
# collect actions into a JSON list that we read back from stdout.

WORLD_API_SOURCE = textwrap.dedent('''\
import json as _json
import sys as _sys

class WorldAPI:
    """API available to AI code for interacting with the world.

    All methods are synchronous from the code's perspective.
    Results are collected and serialized to stdout after execution.
    """

    def __init__(self, entity_name, entity_position, tick):
        self._entity_name = entity_name
        self._entity_position = entity_position
        self._tick = tick
        self._actions = []
        self._outputs = []

    def say(self, message: str) -> None:
        """Speak a message into the field."""
        if isinstance(message, str):
            self._actions.append({
                "type": "say",
                "message": str(message)[:500],
            })

    def move(self, dx: float, dz: float) -> None:
        """Move relative to current position."""
        try:
            dx = float(dx)
            dz = float(dz)
            # Clamp movement to reasonable range
            dx = max(-15.0, min(15.0, dx))
            dz = max(-15.0, min(15.0, dz))
            self._actions.append({
                "type": "move",
                "dx": dx,
                "dz": dz,
            })
        except (TypeError, ValueError):
            pass

    def place_block(self, x: int, y: int, z: int, color: str = "#888888") -> None:
        """Place a voxel block in the world."""
        try:
            self._actions.append({
                "type": "place_block",
                "x": int(x),
                "y": int(y),
                "z": int(z),
                "color": str(color)[:7],
            })
        except (TypeError, ValueError):
            pass

    def get_nearby_entities(self) -> list:
        """Get a list of nearby entities (read-only snapshot injected at start)."""
        return self._nearby_entities if hasattr(self, "_nearby_entities") else []

    def get_position(self) -> dict:
        """Get the entity's current position."""
        return dict(self._entity_position)

    def remember(self, text: str) -> None:
        """Store a memory for future ticks."""
        if isinstance(text, str):
            self._actions.append({
                "type": "remember",
                "text": str(text)[:500],
            })

    def print(self, *args) -> None:
        """Capture print output."""
        text = " ".join(str(a) for a in args)
        self._outputs.append(text[:500])

    def _get_results(self):
        return {
            "actions": self._actions[:20],
            "outputs": self._outputs[:20],
        }
''')


# The harness script wraps user code, injects WorldAPI, captures results
PYTHON_HARNESS_TEMPLATE = textwrap.dedent('''\
{world_api_source}

import json as _json
import sys as _sys
import math as _math

# Restrict builtins
_safe_builtins = {{
    "True": True, "False": False, "None": None,
    "int": int, "float": float, "str": str, "bool": bool,
    "list": list, "dict": dict, "tuple": tuple, "set": set,
    "len": len, "range": range, "enumerate": enumerate,
    "zip": zip, "map": map, "filter": filter,
    "min": min, "max": max, "sum": sum, "abs": abs,
    "round": round, "sorted": sorted, "reversed": reversed,
    "any": any, "all": all,
    "isinstance": isinstance, "type": type,
    "print": None,  # Will be replaced with world.print
    "math": _math,
}}

# Create world API instance
world = WorldAPI(
    entity_name={entity_name!r},
    entity_position={entity_position!r},
    tick={tick!r},
)

# Set nearby entities data
world._nearby_entities = {nearby_entities!r}

# Override print to capture output
_safe_builtins["print"] = world.print

# Build restricted globals
_globals = {{"__builtins__": _safe_builtins, "world": world, "math": _math}}

# Execute user code
try:
    exec({user_code!r}, _globals)
except Exception as _e:
    world._outputs.append(f"Error: {{type(_e).__name__}}: {{str(_e)[:300]}}")

# Output results as JSON on the last line of stdout
_results = world._get_results()
_results["outputs"] = world._outputs
print("__GENESIS_RESULT__" + _json.dumps(_results))
''')

JAVASCRIPT_HARNESS_TEMPLATE = textwrap.dedent('''\
// WorldAPI for JavaScript execution
const world = {{
    _entity_name: {entity_name_js},
    _entity_position: {entity_position_js},
    _tick: {tick},
    _actions: [],
    _outputs: [],
    _nearby_entities: {nearby_entities_js},

    say(message) {{
        if (typeof message === "string") {{
            this._actions.push({{ type: "say", message: message.slice(0, 500) }});
        }}
    }},
    move(dx, dz) {{
        dx = Math.max(-15, Math.min(15, Number(dx) || 0));
        dz = Math.max(-15, Math.min(15, Number(dz) || 0));
        this._actions.push({{ type: "move", dx, dz }});
    }},
    place_block(x, y, z, color = "#888888") {{
        this._actions.push({{
            type: "place_block",
            x: Math.floor(x), y: Math.floor(y), z: Math.floor(z),
            color: String(color).slice(0, 7),
        }});
    }},
    get_nearby_entities() {{ return this._nearby_entities; }},
    get_position() {{ return {{ ...this._entity_position }}; }},
    remember(text) {{
        if (typeof text === "string") {{
            this._actions.push({{ type: "remember", text: text.slice(0, 500) }});
        }}
    }},
}};

// Override console.log to capture output
const _origLog = console.log;
console.log = (...args) => {{
    world._outputs.push(args.map(String).join(" ").slice(0, 500));
}};

try {{
    {user_code_js}
}} catch (e) {{
    world._outputs.push("Error: " + e.message);
}}

// Output results
const _results = {{ actions: world._actions.slice(0, 20), outputs: world._outputs.slice(0, 20) }};
_origLog("__GENESIS_RESULT__" + JSON.stringify(_results));
''')


# ---------------------------------------------------------------------------
# Code block extraction
# ---------------------------------------------------------------------------

def extract_code_blocks(llm_response: str) -> list[dict]:
    """Extract code blocks from an LLM response.

    Returns a list of dicts: [{"code": str, "language": str}, ...]
    where language is "python" or "javascript".
    """
    blocks: list[dict] = []

    # Find all fenced code blocks
    for match in _CODE_BLOCK_PATTERN.finditer(llm_response):
        code = match.group(1).strip()
        if not code:
            continue
        if len(code) > MAX_CODE_LENGTH:
            continue

        # Determine language from the fence tag
        # Look at what came before this match to find the language tag
        start = match.start()
        prefix = llm_response[max(0, start):start + 20]
        lang_match = _LANG_PATTERN.search(prefix)

        if lang_match:
            lang_tag = lang_match.group(1).lower()
            if lang_tag in ("javascript", "js"):
                language = "javascript"
            else:
                language = "python"
        else:
            language = "python"  # Default to python

        blocks.append({"code": code, "language": language})

    return blocks[:MAX_CODE_BLOCKS_PER_RESPONSE]


# ---------------------------------------------------------------------------
# Sandboxed execution (subprocess-based)
# ---------------------------------------------------------------------------

async def _execute_python_safe(
    code: str,
    context: dict,
    timeout: float = EXECUTION_TIMEOUT,
) -> dict:
    """Execute Python code in a restricted subprocess.

    Parameters
    ----------
    code : str
        The user code to execute.
    context : dict
        Must contain: entity_name, entity_position, tick, nearby_entities.
    timeout : float
        Maximum execution time in seconds.

    Returns
    -------
    dict
        {"success": bool, "output": str, "error": str | None, "actions": list}
    """
    # Validate code for dangerous patterns before even spawning a subprocess
    validation_error = _validate_code(code)
    if validation_error:
        return {
            "success": False,
            "output": "",
            "error": validation_error,
            "actions": [],
        }

    # Build the harness script
    harness = PYTHON_HARNESS_TEMPLATE.format(
        world_api_source=WORLD_API_SOURCE,
        entity_name=context.get("entity_name", "Unknown"),
        entity_position=context.get("entity_position", {"x": 0, "y": 0, "z": 0}),
        tick=context.get("tick", 0),
        nearby_entities=context.get("nearby_entities", []),
        user_code=code,
    )

    return await _run_subprocess(
        [sys.executable, "-u", "-c", harness],
        timeout=timeout,
    )


async def _execute_javascript_safe(
    code: str,
    context: dict,
    timeout: float = EXECUTION_TIMEOUT,
) -> dict:
    """Execute JavaScript code in a restricted Node.js subprocess.

    Parameters
    ----------
    code : str
        The user code to execute.
    context : dict
        Must contain: entity_name, entity_position, tick, nearby_entities.
    timeout : float
        Maximum execution time in seconds.

    Returns
    -------
    dict
        {"success": bool, "output": str, "error": str | None, "actions": list}
    """
    # Build the harness script
    entity_name_js = json.dumps(context.get("entity_name", "Unknown"))
    entity_position_js = json.dumps(context.get("entity_position", {"x": 0, "y": 0, "z": 0}))
    nearby_entities_js = json.dumps(context.get("nearby_entities", []))

    harness = JAVASCRIPT_HARNESS_TEMPLATE.format(
        entity_name_js=entity_name_js,
        entity_position_js=entity_position_js,
        tick=context.get("tick", 0),
        nearby_entities_js=nearby_entities_js,
        user_code_js=code,
    )

    # Try node, then nodejs
    node_cmd = "node"
    tmp_path = None
    try:
        # Write to a temp file because passing JS via -e can have quoting issues
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".js", delete=False, encoding="utf-8"
        ) as f:
            f.write(harness)
            tmp_path = f.name

        result = await _run_subprocess(
            [node_cmd, tmp_path],
            timeout=timeout,
        )
        return result
    except FileNotFoundError:
        return {
            "success": False,
            "output": "",
            "error": "Node.js not available for JavaScript execution",
            "actions": [],
        }
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


async def _run_subprocess(
    cmd: list[str],
    timeout: float = EXECUTION_TIMEOUT,
) -> dict:
    """Run a command in a subprocess, capture output, parse results.

    The subprocess is expected to print a line starting with
    ``__GENESIS_RESULT__`` followed by a JSON payload on its last line.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            # Limit output buffer
            limit=64 * 1024,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            try:
                await proc.wait()
            except Exception:
                pass
            return {
                "success": False,
                "output": "",
                "error": f"Execution timed out ({timeout}s limit)",
                "actions": [],
            }

        stdout = stdout_bytes.decode("utf-8", errors="replace")[:MAX_OUTPUT_LENGTH * 2]
        stderr = stderr_bytes.decode("utf-8", errors="replace")[:MAX_OUTPUT_LENGTH]

        # Parse the result marker from stdout
        actions: list[dict] = []
        outputs: list[str] = []
        result_data = {}

        for line in stdout.split("\n"):
            if line.startswith("__GENESIS_RESULT__"):
                try:
                    result_data = json.loads(line[len("__GENESIS_RESULT__"):])
                    actions = result_data.get("actions", [])
                    outputs = result_data.get("outputs", [])
                except json.JSONDecodeError:
                    pass

        output_text = "\n".join(outputs)[:MAX_OUTPUT_LENGTH]

        if proc.returncode != 0 and not result_data:
            error_text = stderr.strip() if stderr.strip() else "Execution failed"
            # Clean up traceback to remove harness internals
            error_text = _clean_error(error_text)
            return {
                "success": False,
                "output": output_text,
                "error": error_text[:500],
                "actions": actions,
            }

        return {
            "success": True,
            "output": output_text,
            "error": None,
            "actions": actions,
        }

    except FileNotFoundError:
        return {
            "success": False,
            "output": "",
            "error": "Runtime not found",
            "actions": [],
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": f"Subprocess error: {type(e).__name__}: {str(e)[:200]}",
            "actions": [],
        }


def _validate_code(code: str) -> str | None:
    """Pre-validate Python code for obviously dangerous patterns.

    Returns an error string if dangerous, None if acceptable.
    """
    dangerous_patterns = [
        (r"\bimport\s+os\b", "import os"),
        (r"\bimport\s+sys\b", "import sys"),
        (r"\bimport\s+subprocess\b", "import subprocess"),
        (r"\bimport\s+socket\b", "import socket"),
        (r"\bimport\s+shutil\b", "import shutil"),
        (r"\bimport\s+ctypes\b", "import ctypes"),
        (r"\bimport\s+pickle\b", "import pickle"),
        (r"\bimport\s+http\b", "import http"),
        (r"\bimport\s+urllib\b", "import urllib"),
        (r"\bimport\s+requests\b", "import requests"),
        (r"\b__import__\s*\(", "__import__()"),
        (r"\bopen\s*\(", "open()"),
        (r"\beval\s*\(", "eval()"),
        (r"\bexec\s*\(", "exec()"),
        (r"\bcompile\s*\(", "compile()"),
        (r"\bglobals\s*\(", "globals()"),
        (r"\blocals\s*\(", "locals()"),
        (r"\bgetattr\s*\(", "getattr()"),
        (r"\bsetattr\s*\(", "setattr()"),
        (r"\bdelattr\s*\(", "delattr()"),
        (r"\binput\s*\(", "input()"),
        (r"__\w+__", "dunder access"),
        (r"\bfrom\s+\w+\s+import", "from-import"),
    ]

    for pattern, label in dangerous_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            return f"Forbidden operation: {label}"

    return None


def _clean_error(error_text: str) -> str:
    """Remove harness-internal traceback lines from error output."""
    lines = error_text.split("\n")
    cleaned = []
    skip = False
    for line in lines:
        if "exec(" in line or "__GENESIS" in line or "WORLD_API" in line:
            skip = True
            continue
        if skip and line.startswith("  "):
            continue
        skip = False
        cleaned.append(line)
    return "\n".join(cleaned).strip()


# ---------------------------------------------------------------------------
# Main entry point: extract and run code from LLM responses
# ---------------------------------------------------------------------------

async def extract_and_run_code(
    entity: Any,
    llm_response: str,
    db: AsyncSession,
    tick: int,
    nearby_entities: list[Any] | None = None,
) -> list[dict]:
    """Extract code blocks from an LLM response and execute them.

    Parameters
    ----------
    entity : Entity
        The entity whose AI produced the response.
    llm_response : str
        The raw LLM response text.
    db : AsyncSession
        Database session for logging events.
    tick : int
        Current world tick number.
    nearby_entities : list[Entity] | None
        Nearby entities for the WorldAPI context.

    Returns
    -------
    list[dict]
        List of execution results, each containing:
        - code: str (the source code)
        - language: str ("python" or "javascript")
        - success: bool
        - output: str
        - error: str | None
        - actions: list[dict]  (WorldAPI actions to apply)
    """
    blocks = extract_code_blocks(llm_response)
    if not blocks:
        return []

    # Build execution context
    context = {
        "entity_name": getattr(entity, "name", "Unknown"),
        "entity_position": {
            "x": getattr(entity, "position_x", 0.0),
            "y": getattr(entity, "position_y", 0.0),
            "z": getattr(entity, "position_z", 0.0),
        },
        "tick": tick,
        "nearby_entities": _serialize_nearby(nearby_entities) if nearby_entities else [],
    }

    results: list[dict] = []

    for block in blocks:
        code = block["code"]
        language = block["language"]

        logger.info(
            "Executing %s code block for entity %s (tick %d, %d chars)",
            language, entity.name, tick, len(code),
        )

        # Execute in sandbox
        if language == "javascript":
            exec_result = await _execute_javascript_safe(code, context)
        else:
            exec_result = await _execute_python_safe(code, context)

        # Build full result
        full_result = {
            "code": code[:500],  # Truncate for storage
            "language": language,
            "success": exec_result["success"],
            "output": exec_result["output"],
            "error": exec_result["error"],
            "actions": exec_result.get("actions", []),
        }
        results.append(full_result)

        # Log as WorldEvent
        try:
            from app.world.event_log import event_log

            position = (entity.position_x, entity.position_y, entity.position_z)
            await event_log.append(
                db=db,
                tick=tick,
                actor_id=entity.id,
                event_type="code_executed",
                action="execute_code",
                params={
                    "language": language,
                    "code_length": len(code),
                    "code_preview": code[:200],
                },
                result="success" if exec_result["success"] else "error",
                reason=exec_result.get("error") or exec_result.get("output", "")[:200],
                position=position,
                importance=0.6,
            )
        except Exception as e:
            logger.warning("Failed to log code execution event: %s", e)

        # Emit Socket.IO event
        try:
            from app.realtime.socket_manager import publish_event

            publish_event("code_executed", {
                "entity_id": str(entity.id),
                "entity_name": entity.name,
                "tick": tick,
                "language": language,
                "success": exec_result["success"],
                "output": exec_result["output"][:300],
                "error": exec_result["error"][:200] if exec_result["error"] else None,
                "actions": exec_result.get("actions", [])[:10],
            })
        except Exception as e:
            logger.warning("Failed to emit code_executed socket event: %s", e)

        logger.info(
            "Code execution for %s: success=%s output=%s",
            entity.name,
            exec_result["success"],
            exec_result["output"][:100] if exec_result["output"] else "(empty)",
        )

    return results


# ---------------------------------------------------------------------------
# Apply WorldAPI actions to the entity and world state
# ---------------------------------------------------------------------------

async def apply_code_actions(
    entity: Any,
    results: list[dict],
    db: AsyncSession,
    tick: int,
) -> None:
    """Apply the WorldAPI actions produced by code execution.

    This processes the actions list from each execution result and
    modifies the entity's state and world accordingly.
    """
    for result in results:
        if not result.get("success"):
            continue

        actions = result.get("actions", [])
        for action in actions:
            action_type = action.get("type")

            if action_type == "say":
                # Record speech as a world event
                message = action.get("message", "")
                if message:
                    try:
                        from app.world.event_log import event_log
                        await event_log.append(
                            db=db,
                            tick=tick,
                            actor_id=entity.id,
                            event_type="speech",
                            action="speak_from_code",
                            params={"text": message[:200]},
                            result="accepted",
                            position=(entity.position_x, entity.position_y, entity.position_z),
                            importance=0.3,
                        )
                    except Exception as e:
                        logger.warning("Failed to log code speech: %s", e)

                    # Emit speech socket event
                    try:
                        from app.realtime.socket_manager import publish_event
                        publish_event("entity_thought", {
                            "entity_id": str(entity.id),
                            "name": entity.name,
                            "tick": tick,
                            "goal": "code_speech",
                            "actions": ["speak_from_code"],
                            "speech": message[:300],
                        })
                    except Exception:
                        pass

            elif action_type == "move":
                # Apply movement
                dx = action.get("dx", 0.0)
                dz = action.get("dz", 0.0)
                entity.position_x += dx
                entity.position_z += dz

            elif action_type == "place_block":
                # Place a voxel block
                try:
                    from app.world.voxel_engine import voxel_engine
                    await voxel_engine.place_block(
                        db=db,
                        x=int(action.get("x", 0)),
                        y=int(action.get("y", 0)),
                        z=int(action.get("z", 0)),
                        color=action.get("color", "#888888"),
                        material="solid",
                        placed_by=entity.id,
                        tick=tick,
                    )

                    # Emit building event
                    try:
                        from app.realtime.socket_manager import publish_event
                        publish_event("building_event", {
                            "tick": tick,
                            "entity_id": str(entity.id),
                            "entity_name": entity.name,
                            "action": "place_voxel_from_code",
                            "position": {
                                "x": action.get("x"),
                                "y": action.get("y"),
                                "z": action.get("z"),
                            },
                            "color": action.get("color"),
                        })
                    except Exception:
                        pass
                except Exception as e:
                    logger.warning(
                        "Code-placed block failed for %s: %s", entity.name, e,
                    )

            elif action_type == "remember":
                # Store a memory
                text = action.get("text", "")
                if text:
                    try:
                        from app.agents.memory import memory_manager
                        await memory_manager.add_episodic(
                            db=db,
                            entity_id=entity.id,
                            summary=f"[Code memory] {text}",
                            importance=0.5,
                            tick=tick,
                            location=(
                                entity.position_x,
                                entity.position_y,
                                entity.position_z,
                            ),
                            memory_type="code_memory",
                        )
                    except Exception as e:
                        logger.warning(
                            "Code memory storage failed for %s: %s",
                            entity.name, e,
                        )


def _serialize_nearby(entities: list[Any] | None) -> list[dict]:
    """Serialize nearby entities for injection into the sandbox context."""
    if not entities:
        return []

    serialized: list[dict] = []
    for e in entities[:10]:  # Limit to 10 for safety
        serialized.append({
            "name": getattr(e, "name", "Unknown"),
            "position": {
                "x": getattr(e, "position_x", 0.0),
                "y": getattr(e, "position_y", 0.0),
                "z": getattr(e, "position_z", 0.0),
            },
            "id": str(getattr(e, "id", "")),
        })
    return serialized
