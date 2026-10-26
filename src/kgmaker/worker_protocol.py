"""Bounded offline worker transport. No shell, package install or project build."""
from __future__ import annotations

import errno
import json
import os
import queue
import signal
import subprocess
import threading
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


def _terminate(process, job=None):
    # The session leader may already have exited while descendants retain pipes.
    try:
        if job is not None:
            job.terminate()
        elif os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        elif process.poll() is None:
            process.kill()
    except ProcessLookupError:
        pass
    process.wait()


def _exchange(process, payload, *, deadline, cancel_file, max_response, job=None):
    """Drain bounded byte streams using pipe operations available on Windows.

    Anonymous Windows pipes cannot be registered with a socket selector. Three
    I/O threads keep request writes and both output streams moving concurrently;
    the bounded queue limits unread buffers, and the caller owns termination.
    """
    messages = queue.Queue(maxsize=8)
    stopped = threading.Event()

    def send(name, value):
        while not stopped.is_set():
            try:
                messages.put((name, value), timeout=.1)
                return
            except queue.Full:
                pass

    def read(stream, name):
        try:
            while not stopped.is_set():
                if os.name == 'posix':
                    try:
                        block = os.read(stream.fileno(), 65536)
                    except BlockingIOError:
                        stopped.wait(.01)
                        continue
                else:
                    block = stream.read(65536)
                if not block:
                    break
                send(name, block)
        except (OSError, ValueError) as error:
            send('error', error)
        finally:
            send(name, None)

    def write():
        try:
            if os.name == 'posix':
                remaining = memoryview(payload)
                while remaining and not stopped.is_set():
                    try:
                        count = os.write(process.stdin.fileno(), remaining[:65536])
                        remaining = remaining[count:]
                    except BlockingIOError:
                        stopped.wait(.01)
            else:
                process.stdin.write(payload)
                process.stdin.flush()
        except BrokenPipeError:
            pass
        except OSError as error:
            # Windows may report EINVAL when the child closes stdin early,
            # as handled by subprocess.communicate as well. Validate stdout
            # and the exit code rather than replacing a protocol diagnostic.
            if error.errno != errno.EINVAL:
                send('error', error)
        except ValueError as error:
            send('error', error)
        finally:
            try:
                process.stdin.close()
            except (OSError, ValueError):
                pass

    threads = [threading.Thread(target=read, args=(process.stdout, 'stdout'), name='kgmaker-worker-stdout', daemon=True),
               threading.Thread(target=read, args=(process.stderr, 'stderr'), name='kgmaker-worker-stderr', daemon=True),
               threading.Thread(target=write, name='kgmaker-worker-stdin', daemon=True)]
    output, errors = bytearray(), bytearray()
    if os.name == 'posix':
        for stream in (process.stdin, process.stdout, process.stderr):
            os.set_blocking(stream.fileno(), False)
    started = []
    try:
        for thread in threads:
            thread.start()
            started.append(thread)
        pending = {'stdout', 'stderr'}
        while pending:
            if cancel_file is not None and cancel_file.exists():
                raise WorkerError('Worker cancelled', 'CANCELLED')
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise WorkerError('Worker timed out', 'TIMED_OUT')
            try:
                name, block = messages.get(timeout=min(remaining, .1))
            except queue.Empty:
                continue
            if name == 'error':
                raise WorkerError('Worker pipe I/O failed: ' + str(block), 'FAILED')
            if block is None:
                pending.discard(name)
            elif name == 'stdout':
                output.extend(block)
                if len(output) > max_response:
                    raise WorkerError('Worker response exceeds protocol output limit', 'OUTPUT_LIMIT_EXCEEDED')
            elif len(errors) < MAX_STDERR:
                errors.extend(block[:MAX_STDERR - len(errors)])
        try:
            code = process.wait(timeout=max(deadline - time.monotonic(), .01))
        except subprocess.TimeoutExpired as error:
            raise WorkerError('Worker timed out after closing streams', 'TIMED_OUT') from error
        return output, errors, code
    except BaseException:
        _terminate(process, job)
        raise
    finally:
        stopped.set()
        for thread in started:
            thread.join(timeout=1)


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
    job = None
    process = None
    try:
        if os.name == 'nt':
            from ._windows_job import Job
            job = Job()
        process = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=os.name == "posix",
                                   creationflags=0x00000004 if os.name == 'nt' else 0)
        if job is not None:
            job.attach_and_resume(process)
    except OSError as error:
        if process is not None:
            process.kill()
            process.wait()
            for stream in (process.stdin, process.stdout, process.stderr):
                stream.close()
        if job is not None:
            job.close()
        raise WorkerError(str(error), "TOOLCHAIN_UNAVAILABLE") from error
    assert process.stdin is not None and process.stdout is not None and process.stderr is not None
    deadline = time.monotonic() + timeout
    try:
        output, errors, code = _exchange(process, payload, deadline=deadline,
            cancel_file=cancel_file, max_response=max_response, job=job)
    finally:
        if job is not None:
            job.close()
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
