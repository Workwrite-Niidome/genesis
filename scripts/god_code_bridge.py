"""GOD AI ↔ Claude Code Bridge

Host-side service that bridges GOD AI (running in Docker) with Claude Code CLI
(running on the host). GOD AI posts code change requests to Redis, this script
picks them up, runs Claude Code, and writes results back.

Usage:
    python scripts/god_code_bridge.py

Requires:
    - Redis running (default: localhost:6379)
    - Claude Code CLI installed and authenticated
    - GENESIS project at the configured path
"""

import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

# --- Configuration ---
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
GENESIS_ROOT = os.environ.get("GENESIS_ROOT", str(Path(__file__).resolve().parent.parent))
REQUEST_QUEUE = "genesis:god_code_requests"
RESULT_PREFIX = "genesis:god_code_result:"
POLL_INTERVAL = 5  # seconds
REQUEST_TIMEOUT = 300  # 5 minutes max for Claude Code execution
CLAUDE_CMD = os.environ.get("CLAUDE_CMD", "claude")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [GOD-BRIDGE] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def get_redis():
    import redis
    return redis.from_url(REDIS_URL)


def run_claude_code(prompt: str, allowed_tools: str = "Edit,Write,Read,Bash,Glob,Grep") -> dict:
    """Run Claude Code CLI with the given prompt and return the result."""
    cmd = [
        CLAUDE_CMD,
        "-p", prompt,
        "--output-format", "text",
        "--max-turns", "20",
    ]

    logger.info(f"Running Claude Code: prompt={prompt[:200]}...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=REQUEST_TIMEOUT,
            cwd=GENESIS_ROOT,
            encoding="utf-8",
        )

        output = result.stdout.strip()
        error = result.stderr.strip()

        if result.returncode != 0:
            logger.error(f"Claude Code failed (exit {result.returncode}): {error[:500]}")
            return {
                "success": False,
                "error": error[:2000] or f"Exit code {result.returncode}",
                "output": output[:2000],
            }

        logger.info(f"Claude Code completed: {len(output)} chars output")
        return {
            "success": True,
            "output": output[:5000],
            "error": None,
        }

    except subprocess.TimeoutExpired:
        logger.error(f"Claude Code timed out after {REQUEST_TIMEOUT}s")
        return {
            "success": False,
            "error": f"Timed out after {REQUEST_TIMEOUT} seconds",
            "output": "",
        }
    except FileNotFoundError:
        logger.error(f"Claude Code CLI not found: {CLAUDE_CMD}")
        return {
            "success": False,
            "error": f"Claude CLI not found at '{CLAUDE_CMD}'. Is it installed?",
            "output": "",
        }
    except Exception as e:
        logger.error(f"Claude Code execution error: {e}")
        return {
            "success": False,
            "error": str(e)[:2000],
            "output": "",
        }


def process_request(r, request_data: dict) -> None:
    """Process a single GOD AI code change request."""
    request_id = request_data.get("request_id", "unknown")
    prompt = request_data.get("prompt", "")

    if not prompt:
        result = {"success": False, "error": "Empty prompt", "output": ""}
    else:
        # Prefix the prompt with project context
        full_prompt = (
            f"You are operating on the GENESIS project — an AI autonomous world simulation.\n"
            f"Working directory: {GENESIS_ROOT}\n"
            f"The GOD AI (the world's architect) has requested the following change:\n\n"
            f"{prompt}\n\n"
            f"Make the requested changes. Be precise and minimal. "
            f"Do not add unnecessary features or refactoring beyond what's requested."
        )
        result = run_claude_code(full_prompt)

    # Write result back to Redis with 10-minute expiry
    result_key = f"{RESULT_PREFIX}{request_id}"
    result["request_id"] = request_id
    result["timestamp"] = time.time()

    r.setex(result_key, 600, json.dumps(result, ensure_ascii=False))
    logger.info(f"Result for {request_id}: success={result['success']}")


def main():
    logger.info(f"GOD AI ↔ Claude Code Bridge starting")
    logger.info(f"  GENESIS_ROOT: {GENESIS_ROOT}")
    logger.info(f"  REDIS_URL: {REDIS_URL}")
    logger.info(f"  CLAUDE_CMD: {CLAUDE_CMD}")
    logger.info(f"  POLL_INTERVAL: {POLL_INTERVAL}s")

    # Verify Claude CLI exists
    try:
        ver = subprocess.run(
            [CLAUDE_CMD, "--version"],
            capture_output=True, text=True, timeout=10,
        )
        logger.info(f"  Claude CLI version: {ver.stdout.strip()}")
    except Exception as e:
        logger.error(f"Cannot find Claude CLI: {e}")
        sys.exit(1)

    r = get_redis()
    r.ping()
    logger.info("Connected to Redis. Listening for GOD AI requests...")

    while True:
        try:
            # Blocking pop from the request queue (timeout = POLL_INTERVAL)
            item = r.blpop(REQUEST_QUEUE, timeout=POLL_INTERVAL)

            if item is None:
                continue

            _, raw_data = item
            request_data = json.loads(raw_data)

            logger.info(f"Received request: {request_data.get('request_id', '?')}")
            process_request(r, request_data)

        except KeyboardInterrupt:
            logger.info("Shutting down...")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
