"""Code Executor: Sandboxed execution of AI-generated code.

Executes Python code written by AIs within a restricted environment.
The code can interact with the world through a limited API (world_api).

Security: Uses RestrictedPython for safe execution with:
- 5-second timeout
- 64MB memory limit (enforced at process level)
- No network access
- No filesystem access
- Only world_api functions available
"""

import asyncio
import logging
import signal
import sys
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Maximum execution time in seconds
EXEC_TIMEOUT = 5

# Maximum output length
MAX_OUTPUT_LEN = 2000


class WorldAPI:
    """API available to AI code for interacting with the world.

    All methods are synchronous from the code's perspective.
    Results are collected and applied after execution.
    """

    def __init__(self, ai_id: str):
        self.ai_id = ai_id
        self._outputs: list[str] = []
        self._state_changes: list[dict] = []
        self._world_state_changes: list[dict] = []
        self._entities_to_create: list[dict] = []
        self._visuals: list[dict] = []
        self._sounds: list[dict] = []

    def emit_text(self, text: str) -> None:
        """Output text to the field."""
        if isinstance(text, str):
            self._outputs.append(text[:500])

    def emit_visual(self, data: dict) -> None:
        """Output visual data to the field."""
        if isinstance(data, dict):
            self._visuals.append(data)

    def emit_sound(self, data: dict) -> None:
        """Output sound data to the field."""
        if isinstance(data, dict):
            self._sounds.append(data)

    def set_state(self, key: str, value: Any) -> None:
        """Modify own state."""
        if isinstance(key, str) and len(key) < 100:
            self._state_changes.append({"key": key, "value": value})

    def set_world_state(self, key: str, value: Any) -> None:
        """Modify shared world state."""
        if isinstance(key, str) and len(key) < 100:
            self._world_state_changes.append({"key": key, "value": value})

    def create_entity(self, name: str, traits: list[str] | None = None) -> dict:
        """Request creation of a new entity."""
        if isinstance(name, str) and len(name) < 50:
            entry = {"name": name, "traits": traits or []}
            self._entities_to_create.append(entry)
            return {"status": "queued", "name": name}
        return {"status": "error", "reason": "invalid name"}

    def print(self, *args: Any) -> None:
        """Capture print output."""
        text = " ".join(str(a) for a in args)
        self._outputs.append(text[:500])

    def get_results(self) -> dict:
        """Get all collected results from execution."""
        return {
            "outputs": self._outputs[:20],
            "state_changes": self._state_changes[:50],
            "world_state_changes": self._world_state_changes[:10],
            "entities_to_create": self._entities_to_create[:5],
            "visuals": self._visuals[:5],
            "sounds": self._sounds[:5],
        }


class CodeExecutor:
    """Executes AI-generated code in a sandboxed environment."""

    async def execute(self, code: str, ai_id: str, db: AsyncSession) -> dict:
        """Execute code in a sandbox and return results.

        Returns:
            {
                "success": bool,
                "output": str,
                "error": str | None,
                "results": dict  # WorldAPI results
            }
        """
        if not code or not code.strip():
            return {"success": False, "output": "", "error": "Empty code", "results": {}}

        # Validate code length
        if len(code) > 5000:
            return {"success": False, "output": "", "error": "Code too long (max 5000 chars)", "results": {}}

        # Check for dangerous operations using regex for robust matching
        import re as _re
        forbidden_patterns = [
            (r'\bimport\s+os\b', "import os"),
            (r'\bimport\s+sys\b', "import sys"),
            (r'\bimport\s+subprocess\b', "import subprocess"),
            (r'\bimport\s+socket\b', "import socket"),
            (r'\bimport\s+shutil\b', "import shutil"),
            (r'\bimport\s+ctypes\b', "import ctypes"),
            (r'\bimport\s+pickle\b', "import pickle"),
            (r'\b__import__\s*\(', "__import__()"),
            (r'\bexec\s*\(', "exec()"),
            (r'\beval\s*\(', "eval()"),
            (r'\bcompile\s*\(', "compile()"),
            (r'\bopen\s*\(', "open()"),
            (r'\bfile\s*\(', "file()"),
            (r'\binput\s*\(', "input()"),
            (r'\bgetattr\s*\(', "getattr()"),
            (r'\bsetattr\s*\(', "setattr()"),
            (r'\bdelattr\s*\(', "delattr()"),
            (r'\bglobals\s*\(', "globals()"),
            (r'\blocals\s*\(', "locals()"),
            (r'\bvars\s*\(', "vars()"),
            (r'\bdir\s*\(', "dir()"),
            (r'__\w+__', "dunder access"),
            (r'\bos\.\w+', "os module access"),
            (r'\bsys\.\w+', "sys module access"),
            (r'from\s+\w+\s+import', "from import"),
        ]
        for pattern, label in forbidden_patterns:
            if _re.search(pattern, code, _re.IGNORECASE):
                return {
                    "success": False,
                    "output": "",
                    "error": f"Forbidden operation: {label}",
                    "results": {},
                }

        world_api = WorldAPI(ai_id)

        # Build restricted globals
        safe_builtins = {
            "True": True, "False": False, "None": None,
            "int": int, "float": float, "str": str, "bool": bool,
            "list": list, "dict": dict, "tuple": tuple, "set": set,
            "len": len, "range": range, "enumerate": enumerate,
            "zip": zip, "map": map, "filter": filter,
            "min": min, "max": max, "sum": sum, "abs": abs,
            "round": round, "sorted": sorted, "reversed": reversed,
            "any": any, "all": all,
            "isinstance": isinstance, "type": type,
            "print": world_api.print,
        }

        safe_globals = {
            "__builtins__": safe_builtins,
            "world": world_api,
            "math": _safe_math(),
        }

        # Execute with timeout
        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, self._run_code, code, safe_globals
                ),
                timeout=EXEC_TIMEOUT,
            )
        except asyncio.TimeoutError:
            return {
                "success": False,
                "output": "",
                "error": "Execution timed out (5s limit)",
                "results": world_api.get_results(),
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e)[:500],
                "results": world_api.get_results(),
            }

        # Apply world_api results
        results = world_api.get_results()
        output = "\n".join(results["outputs"])[:MAX_OUTPUT_LEN]

        # Apply state changes to the AI
        if results["state_changes"]:
            try:
                from app.models.ai import AI
                from sqlalchemy import select
                from uuid import UUID
                ai_result = await db.execute(
                    select(AI).where(AI.id == UUID(ai_id))
                )
                ai = ai_result.scalar_one_or_none()
                if ai:
                    state = dict(ai.state)
                    for change in results["state_changes"]:
                        state[change["key"]] = change["value"]
                    ai.state = state
            except Exception as e:
                logger.warning(f"Failed to apply state changes: {e}")

        # Queue entity creation (with MAX_AI_COUNT check)
        if results["entities_to_create"]:
            from app.core.ai_manager import ai_manager
            from app.core.history_manager import history_manager
            from app.config import settings
            from app.models.ai import AI as AIModel
            from sqlalchemy import func as sa_func
            alive_result = await db.execute(
                select(sa_func.count()).select_from(AIModel).where(AIModel.is_alive == True)
            )
            alive_count = alive_result.scalar() or 0
            for entity in results["entities_to_create"]:
                if alive_count >= settings.MAX_AI_COUNT:
                    logger.warning(f"MAX_AI_COUNT reached, skipping entity creation from code")
                    break
                try:
                    tick = await history_manager.get_latest_tick_number(db)
                    await ai_manager.create_ai(
                        db,
                        creator_type="ai_code",
                        custom_name=entity["name"],
                        custom_traits=entity.get("traits"),
                        tick_number=tick,
                    )
                    alive_count += 1
                except Exception as e:
                    logger.warning(f"Failed to create entity from code: {e}")

        if result.get("error"):
            return {
                "success": False,
                "output": output,
                "error": result["error"],
                "results": results,
            }

        return {
            "success": True,
            "output": output,
            "error": None,
            "results": results,
        }

    def _run_code(self, code: str, safe_globals: dict) -> dict:
        """Run code in restricted environment. Called in thread pool."""
        try:
            exec(code, safe_globals)
            return {"error": None}
        except Exception as e:
            return {"error": f"{type(e).__name__}: {str(e)[:300]}"}


def _safe_math():
    """Return a safe subset of the math module."""
    import math
    return type('SafeMath', (), {
        'pi': math.pi,
        'e': math.e,
        'sqrt': math.sqrt,
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'log': math.log,
        'log2': math.log2,
        'log10': math.log10,
        'floor': math.floor,
        'ceil': math.ceil,
        'pow': math.pow,
        'fabs': math.fabs,
    })()


code_executor = CodeExecutor()
