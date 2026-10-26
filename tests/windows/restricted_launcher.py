"""Launch the actual smoke with an own-user restricted primary Windows token.

Uses documented token/process APIs, avoiding runas interactive-console requirements.
This is CI setup only; the smoke independently rejects administrator membership.
"""
import argparse
import ctypes
from ctypes import wintypes as w
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace


def launch(command, root, timeout=900):
    if os.name != 'nt':
        raise OSError('Restricted-token smoke requires actual Windows')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    security = ctypes.WinDLL('advapi32', use_last_error=True)

    class Sid(ctypes.Structure):
        _fields_ = [('sid', w.LPVOID), ('attributes', w.DWORD)]

    class Startup(ctypes.Structure):
        _fields_ = [('cb', w.DWORD), ('reserved', w.LPWSTR), ('desktop', w.LPWSTR),
                    ('title', w.LPWSTR), ('x', w.DWORD), ('y', w.DWORD),
                    ('width', w.DWORD), ('height', w.DWORD), ('chars_x', w.DWORD),
                    ('chars_y', w.DWORD), ('fill', w.DWORD), ('flags', w.DWORD),
                    ('show', w.WORD), ('reserved_size', w.WORD), ('reserved_ptr', w.LPVOID),
                    ('stdin', w.HANDLE), ('stdout', w.HANDLE), ('stderr', w.HANDLE)]

    class Process(ctypes.Structure):
        _fields_ = [('process', w.HANDLE), ('thread', w.HANDLE), ('pid', w.DWORD), ('tid', w.DWORD)]

    signatures = [
        (kernel, 'GetCurrentProcess', [], w.HANDLE),
        (kernel, 'CloseHandle', [w.HANDLE], w.BOOL),
        (kernel, 'WaitForSingleObject', [w.HANDLE, w.DWORD], w.DWORD),
        (kernel, 'GetExitCodeProcess', [w.HANDLE, ctypes.POINTER(w.DWORD)], w.BOOL),
        (security, 'OpenProcessToken', [w.HANDLE, w.DWORD, ctypes.POINTER(w.HANDLE)], w.BOOL),
        (security, 'CreateWellKnownSid', [ctypes.c_int, w.LPVOID, w.LPVOID, ctypes.POINTER(w.DWORD)], w.BOOL),
        (security, 'CreateRestrictedToken', [w.HANDLE, w.DWORD, w.DWORD, ctypes.POINTER(Sid),
            w.DWORD, w.LPVOID, w.DWORD, w.LPVOID, ctypes.POINTER(w.HANDLE)], w.BOOL),
        (security, 'CreateProcessAsUserW', [w.HANDLE, w.LPCWSTR, w.LPWSTR, w.LPVOID, w.LPVOID,
            w.BOOL, w.DWORD, w.LPVOID, w.LPCWSTR, ctypes.POINTER(Startup), ctypes.POINTER(Process)], w.BOOL),
    ]
    for library, name, args, result in signatures:
        function = getattr(library, name)
        function.argtypes, function.restype = args, result

    def checked(ok, operation):
        if not ok:
            error = ctypes.get_last_error()
            raise OSError(error, f'{operation}: {ctypes.FormatError(error)}')

    source, restricted = w.HANDLE(), w.HANDLE()
    process = Process()
    job = None
    try:
        checked(security.OpenProcessToken(kernel.GetCurrentProcess(), 0x000b, ctypes.byref(source)), 'OpenProcessToken')
        sid = ctypes.create_string_buffer(68)  # SECURITY_MAX_SID_SIZE
        size = w.DWORD(len(sid))
        checked(security.CreateWellKnownSid(26, None, sid, ctypes.byref(size)), 'CreateWellKnownSid(Administrators)')
        deny = Sid(ctypes.cast(sid, w.LPVOID), 0)
        # DISABLE_MAX_PRIVILEGE; Administrators becomes deny-only, never enabled.
        checked(security.CreateRestrictedToken(source, 1, 1, ctypes.byref(deny), 0, None, 0, None,
            ctypes.byref(restricted)), 'CreateRestrictedToken')
        print('Created own-user restricted token: privileges disabled; Administrators deny-only', flush=True)
        startup = Startup()
        startup.cb = ctypes.sizeof(startup)
        argv = ctypes.create_unicode_buffer(subprocess.list2cmdline(command))
        checked(security.CreateProcessAsUserW(restricted, command[0], argv, None, None, False,
            0x08000004, None, str(root), ctypes.byref(startup), ctypes.byref(process)), 'CreateProcessAsUserW')
        # Keep the complete smoke tree owned, including timeout cleanup.
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
        from kgmaker._windows_job import Job
        job = Job()
        job.attach_and_resume(SimpleNamespace(pid=process.pid))
        print(f'Restricted smoke PID: {process.pid}', flush=True)
        outcome = kernel.WaitForSingleObject(process.process, int(timeout * 1000))
        if outcome != 0:
            raise TimeoutError(f'Restricted smoke wait failed/timed out: {outcome:#x}')
        code = w.DWORD()
        checked(kernel.GetExitCodeProcess(process.process, ctypes.byref(code)), 'GetExitCodeProcess')
        print(f'Restricted smoke exit code: {code.value}', flush=True)
        return code.value
    finally:
        if job is not None:
            job.close()
        if process.process:
            # A setup failure must not strand the suspended child.
            kernel.TerminateProcess.argtypes = [w.HANDLE, w.UINT]
            kernel.TerminateProcess(process.process, 1)
            kernel.WaitForSingleObject(process.process, 5000)
        for handle in (process.thread, process.process, restricted, source):
            if handle:
                kernel.CloseHandle(handle)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    options = parser.parse_args()
    command = options.command[1:] if options.command[:1] == ['--'] else options.command
    if not command:
        parser.error('An explicit smoke command is required')
    try:
        exit_code = launch(command, options.root)
    except Exception as error:
        print(f'Restricted launcher failed: {type(error).__name__}: {error}', flush=True)
        exit_code = 1
    raise SystemExit(exit_code)
