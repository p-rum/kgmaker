"""Bounded offline worker transport. No shell, package install or project build."""
from __future__ import annotations

import json
import os
import selectors
import signal
import subprocess
import time
from pathlib import Path

from .analysis_model import AnalysisError, canonical

PROTOCOL_VERSION = 1
MAX_REQUEST = 16 * 1024 * 1024
MAX_RESPONSE = 64 * 1024 * 1024
MAX_STDERR = 256 * 1024


class WorkerError(AnalysisError):
    def __init__(self, message: str, status: str, stderr: str = ""):
        super().__init__(message, 3)
        self.status, self.stderr = status, stderr


def _terminate(process):
    if process.poll() is None:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
    process.wait()


def request_worker(argv: list[str], request: dict, *, cwd: Path, timeout: float = 120,
                   cancel_file: Path | None = None, max_response: int = MAX_RESPONSE) -> dict:
    if not argv or not all(isinstance(a, str) and a and "\0" not in a for a in argv):
        raise AnalysisError("worker command must be a nonempty argv array")
    if timeout <= 0 or max_response < 1:
        raise AnalysisError("worker timeout/output limit must be positive")
    request = {**request, "protocol_version": PROTOCOL_VERSION}
    payload = canonical(request).encode() + b"\n"
    if len(payload) > MAX_REQUEST:
        raise AnalysisError("Worker request exceeds protocol limit")
    if cancel_file is not None and cancel_file.exists():
        raise WorkerError("Worker cancelled before launch", "CANCELLED")
    try:
        process = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=os.name == "posix")
    except OSError as error:
        raise WorkerError(str(error), "TOOLCHAIN_UNAVAILABLE") from error
    assert process.stdin is not None and process.stdout is not None and process.stderr is not None
    output, errors = bytearray(), bytearray()
    deadline = time.monotonic() + timeout
    try:
        with selectors.DefaultSelector() as selector:
            for stream, name in ((process.stdin, "stdin"), (process.stdout, "stdout"), (process.stderr, "stderr")):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_WRITE if name == "stdin" else selectors.EVENT_READ, name)
            sent = 0
            while selector.get_map():
                if cancel_file is not None and cancel_file.exists():
                    raise WorkerError("Worker cancelled", "CANCELLED")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise WorkerError("Worker timed out", "TIMED_OUT")
                for key, _ in selector.select(min(remaining, .1)):
                    stream, name = key.fileobj, key.data
                    if name == "stdin":
                        try:
                            sent += os.write(stream.fileno(), payload[sent:sent + 65536])
                        except BrokenPipeError:
                            sent = len(payload)
                        if sent == len(payload):
                            selector.unregister(stream)
                            stream.close()
                        continue
                    block = os.read(stream.fileno(), 65536)
                    if not block:
                        selector.unregister(stream)
                        stream.close()
                    elif name == "stdout":
                        output.extend(block)
                        if len(output) > max_response:
                            raise WorkerError("Worker response exceeds protocol output limit", "OUTPUT_LIMIT_EXCEEDED")
                    elif len(errors) < MAX_STDERR:
                        errors.extend(block[:MAX_STDERR - len(errors)])
            remaining = deadline - time.monotonic()
            try:
                code = process.wait(timeout=max(remaining, .01))
            except subprocess.TimeoutExpired as error:
                raise WorkerError("Worker timed out after closing streams", "TIMED_OUT") from error
    except BaseException:
        _terminate(process)
        raise
    finally:
        for stream in (process.stdin, process.stdout, process.stderr):
            if not stream.closed:
                stream.close()
    stderr = errors.decode("utf-8", errors="replace")
    try:
        def unique(pairs):
            value = {}
            for key, item in pairs:
                if key in value:
                    raise ValueError("Duplicate protocol key: " + key)
                value[key] = item
            return value
        def reject_constant(value):
            raise ValueError("Non-finite protocol value: " + value)
        response = json.loads(output, object_pairs_hook=unique, parse_constant=reject_constant)
    except (UnicodeError, ValueError) as error:
        raise WorkerError("Worker stdout is not a single JSON response", "INVALID_PROTOCOL", stderr) from error
    if not isinstance(response, dict) or response.get("protocol_version") != PROTOCOL_VERSION:
        raise WorkerError("Worker protocol version mismatch", "INVALID_PROTOCOL", stderr)
    if code or response.get("status") == "FAILED":
        reason = "; ".join(str(d.get("reason", d.get("code", "unknown"))) for d in response.get("diagnostics", []) if isinstance(d, dict))
        raise WorkerError(reason or f"Worker failed with exit code {code}", "FAILED", stderr)
    if not isinstance(response.get("worker"), str) or not isinstance(response.get("capabilities"), list):
        raise WorkerError("Missing worker handshake/capability metadata", "INVALID_PROTOCOL", stderr)
    return response


def handshake(argv: list[str], *, cwd: Path, timeout: float = 30) -> dict:
    response = request_worker(argv, {"operation": "handshake"}, cwd=cwd, timeout=timeout)
    if not response.get("compiler_version"):
        raise WorkerError("Handshake lacks compiler version", "INVALID_PROTOCOL")
    return response
