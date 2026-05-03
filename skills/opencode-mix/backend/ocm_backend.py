"""
OpenCode Mix skill backend — shared helpers and session store.
"""
import subprocess
import threading
import time
import uuid
import os

OCM_BINARY = "/home/mimin/.local/bin/opencode-mix"
DEFAULT_MODEL = "enowxlabs/claude-opus-4-6"
DEFAULT_WORKDIR = "/home/mimin/.openclaw/workspace"
DEFAULT_TIMEOUT = 300

# In-memory session store: {session_id: {process, output_lines, status, workdir}}
_sessions = {}
_sessions_lock = threading.Lock()


def get_config(sdk, key, default):
    """Get skill config variable with fallback."""
    try:
        val = sdk.config.get(key)
        return val if val else default
    except Exception:
        return default


def run_ocm_oneshot(task: str, workdir: str, model: str, variant: str = None, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Run opencode-mix in one-shot mode via `opencode run`."""
    cmd = [OCM_BINARY, "run", task, "--dir", workdir, "-m", model, "--format", "default",
           "--dangerously-skip-permissions"]
    if variant:
        cmd += ["--variant", variant]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=workdir,
            env={**os.environ, "TERM": "dumb"}
        )
        output = result.stdout.strip() or result.stderr.strip()
        return {
            "success": result.returncode == 0,
            "output": output[:8000] if output else "(no output)",
            "exit_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "output": f"Task timed out after {timeout}s", "exit_code": -1}
    except Exception as e:
        return {"success": False, "output": str(e), "exit_code": -1}


def start_session(workdir: str, model: str) -> str:
    """Start a background opencode-mix session, return session_id."""
    session_id = "ses_" + uuid.uuid4().hex[:12]
    output_lines = []
    lock = threading.Lock()

    cmd = [OCM_BINARY, "run", "--dir", workdir, "-m", model,
           "--dangerously-skip-permissions", "--format", "default"]

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=workdir,
        env={**os.environ, "TERM": "dumb"}
    )

    def reader():
        for line in proc.stdout:
            with lock:
                output_lines.append(line)

    t = threading.Thread(target=reader, daemon=True)
    t.start()

    with _sessions_lock:
        _sessions[session_id] = {
            "process": proc,
            "output_lines": output_lines,
            "lock": lock,
            "status": "running",
            "workdir": workdir,
            "model": model,
            "started_at": time.time(),
            "reader_thread": t
        }

    return session_id


def send_to_session(session_id: str, prompt: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Send prompt to active session and wait for response."""
    with _sessions_lock:
        session = _sessions.get(session_id)

    if not session:
        return {"success": False, "output": f"Session {session_id} not found"}

    proc = session["process"]
    if proc.poll() is not None:
        return {"success": False, "output": "Session has ended"}

    # Clear previous output
    with session["lock"]:
        session["output_lines"].clear()

    # Send prompt
    try:
        proc.stdin.write(prompt + "\n")
        proc.stdin.flush()
    except Exception as e:
        return {"success": False, "output": f"Failed to send: {e}"}

    # Wait for output
    deadline = time.time() + timeout
    last_output_time = time.time()
    while time.time() < deadline:
        time.sleep(1)
        with session["lock"]:
            lines = list(session["output_lines"])
        if lines:
            last_output_time = time.time()
        # Consider done if no new output for 5s and we have some output
        if lines and (time.time() - last_output_time) > 5:
            break

    with session["lock"]:
        output = "".join(session["output_lines"]).strip()

    return {
        "success": True,
        "output": output[:8000] if output else "(waiting for response...)",
        "session_id": session_id
    }


def list_sessions() -> list:
    """List all sessions with status."""
    result = []
    with _sessions_lock:
        for sid, s in _sessions.items():
            proc = s["process"]
            status = "running" if proc.poll() is None else "ended"
            result.append({
                "session_id": sid,
                "status": status,
                "workdir": s["workdir"],
                "model": s["model"],
                "uptime_seconds": int(time.time() - s["started_at"])
            })
    return result


def stop_session(session_id: str) -> dict:
    """Stop and remove a session."""
    with _sessions_lock:
        session = _sessions.pop(session_id, None)

    if not session:
        return {"success": False, "output": f"Session {session_id} not found"}

    proc = session["process"]
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        proc.kill()

    return {"success": True, "output": f"Session {session_id} stopped"}
