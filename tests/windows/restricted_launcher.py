"""Launch the actual smoke with an own-user restricted primary Windows token.

Uses documented token/process APIs, avoiding runas interactive-console requirements.
This is CI setup only; the smoke independently rejects administrator membership.
"""
import argparse
import ctypes
import json
from ctypes import wintypes as w
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace


class PrivateDesktop:
    """Own an isolated noninteractive Win32 station/desktop for the same user.

    Disabling the Administrators SID can remove access to a service runner's
    inherited desktop. Granting this user explicitly on private objects avoids
    changing any ACL on the runner's existing window station or desktop.
    """
    def __init__(self, token):
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.security = ctypes.WinDLL('advapi32', use_last_error=True)
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.station = self.desktop = self.descriptor = None
        signatures = [
            (self.kernel, 'LocalFree', [w.HANDLE], w.HANDLE),
            (self.security, 'GetTokenInformation', [w.HANDLE, ctypes.c_int, w.LPVOID,
                w.DWORD, ctypes.POINTER(w.DWORD)], w.BOOL),
            (self.security, 'ConvertSidToStringSidW', [w.LPVOID, ctypes.POINTER(w.LPWSTR)], w.BOOL),
            (self.security, 'ConvertStringSecurityDescriptorToSecurityDescriptorW',
                [w.LPCWSTR, w.DWORD, ctypes.POINTER(w.LPVOID), w.LPVOID], w.BOOL),
            (self.user, 'GetProcessWindowStation', [], w.HANDLE),
            (self.user, 'SetProcessWindowStation', [w.HANDLE], w.BOOL),
            (self.user, 'CreateWindowStationW', [w.LPCWSTR, w.DWORD, w.DWORD, w.LPVOID], w.HANDLE),
            (self.user, 'CloseWindowStation', [w.HANDLE], w.BOOL),
            (self.user, 'CreateDesktopW', [w.LPCWSTR, w.LPCWSTR, w.LPVOID, w.DWORD,
                w.DWORD, w.LPVOID], w.HANDLE),
            (self.user, 'CloseDesktop', [w.HANDLE], w.BOOL),
        ]
        for library, name, args, result in signatures:
            function = getattr(library, name)
            function.argtypes, function.restype = args, result

        def checked(value, operation):
            if not value:
                error = ctypes.get_last_error()
                raise OSError(error, f'{operation}: {ctypes.FormatError(error)}')
            return value

        class Attributes(ctypes.Structure):
            _fields_ = [('length', w.DWORD), ('descriptor', w.LPVOID), ('inherit', w.BOOL)]

        size = w.DWORD()
        self.security.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
        buffer = ctypes.create_string_buffer(size.value)
        checked(self.security.GetTokenInformation(token, 1, buffer, size, ctypes.byref(size)), 'GetTokenInformation(User)')
        sid = ctypes.cast(buffer, ctypes.POINTER(w.LPVOID))[0]
        sid_string = w.LPWSTR()
        checked(self.security.ConvertSidToStringSidW(sid, ctypes.byref(sid_string)), 'ConvertSidToStringSidW')
        try:
            # Private DACL, not Everyone/Users/Administrators. SYSTEM retains access.
            sddl = f'D:P(A;;GA;;;SY)(A;;GA;;;{sid_string.value})'
        finally:
            self.kernel.LocalFree(ctypes.cast(sid_string, w.HANDLE))
        descriptor = w.LPVOID()
        checked(self.security.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1,
            ctypes.byref(descriptor), None), 'ConvertStringSecurityDescriptorToSecurityDescriptorW')
        self.descriptor = descriptor
        try:
            attributes = Attributes(ctypes.sizeof(Attributes), descriptor, False)
            name = f'kgmaker_smoke_{os.getpid()}'
            self.station = checked(self.user.CreateWindowStationW(name, 0, 0x000f037f,
                ctypes.byref(attributes)), 'CreateWindowStationW(private)')
            previous = checked(self.user.GetProcessWindowStation(), 'GetProcessWindowStation')
            checked(self.user.SetProcessWindowStation(self.station), 'SetProcessWindowStation(private)')
            try:
                self.desktop = checked(self.user.CreateDesktopW('smoke', None, None, 0,
                    0x000f01ff, ctypes.byref(attributes)), 'CreateDesktopW(private)')
            finally:
                checked(self.user.SetProcessWindowStation(previous), 'SetProcessWindowStation(restore)')
            self.path = name + r'\smoke'
            print(f'Private noninteractive desktop: {self.path}; ACL grants own user and SYSTEM; {sddl}', flush=True)
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.desktop:
            self.user.CloseDesktop(self.desktop)
            self.desktop = None
        if self.station:
            self.user.CloseWindowStation(self.station)
            self.station = None
        if self.descriptor:
            self.kernel.LocalFree(self.descriptor)
            self.descriptor = None


def default_dacl(token):
    """Return the token's default object ACL as SDDL for native diagnosis."""
    api = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    api.GetTokenInformation.argtypes = [w.HANDLE, ctypes.c_int, w.LPVOID, w.DWORD, ctypes.POINTER(w.DWORD)]
    api.InitializeSecurityDescriptor.argtypes = [w.LPVOID, w.DWORD]
    api.SetSecurityDescriptorDacl.argtypes = [w.LPVOID, w.BOOL, w.LPVOID, w.BOOL]
    api.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = [w.LPVOID, w.DWORD,
        w.DWORD, ctypes.POINTER(w.LPWSTR), w.LPVOID]
    kernel.LocalFree.argtypes, kernel.LocalFree.restype = [w.HANDLE], w.HANDLE
    size = w.DWORD()
    api.GetTokenInformation(token, 6, None, 0, ctypes.byref(size))
    buffer = ctypes.create_string_buffer(size.value)
    if not api.GetTokenInformation(token, 6, buffer, size, ctypes.byref(size)):
        raise ctypes.WinError(ctypes.get_last_error())
    acl = ctypes.cast(buffer, ctypes.POINTER(w.LPVOID))[0]
    if not acl:
        return 'NULL default DACL'
    descriptor = ctypes.create_string_buffer(64)  # accommodates absolute SECURITY_DESCRIPTOR on x64
    if not api.InitializeSecurityDescriptor(descriptor, 1) or not api.SetSecurityDescriptorDacl(descriptor, True, acl, False):
        raise ctypes.WinError(ctypes.get_last_error())
    text = w.LPWSTR()
    if not api.ConvertSecurityDescriptorToStringSecurityDescriptorW(descriptor, 1, 4, ctypes.byref(text), None):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return text.value
    finally:
        kernel.LocalFree(ctypes.cast(text, w.HANDLE))


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
    desktop = None
    diagnostic_token = w.HANDLE()
    try:
        checked(security.OpenProcessToken(kernel.GetCurrentProcess(), 0x008b, ctypes.byref(source)), 'OpenProcessToken')
        sid = ctypes.create_string_buffer(68)  # SECURITY_MAX_SID_SIZE
        size = w.DWORD(len(sid))
        checked(security.CreateWellKnownSid(26, None, sid, ctypes.byref(size)), 'CreateWellKnownSid(Administrators)')
        deny = Sid(ctypes.cast(sid, w.LPVOID), 0)
        # DISABLE_MAX_PRIVILEGE; Administrators becomes deny-only, never enabled.
        checked(security.CreateRestrictedToken(source, 1, 1, ctypes.byref(deny), 0, None, 0, None,
            ctypes.byref(restricted)), 'CreateRestrictedToken')
        print('Created own-user restricted token: privileges disabled; Administrators deny-only', flush=True)
        desktop = PrivateDesktop(source)
        for name, token in (('Source', source), ('Restricted', restricted)):
            try:
                print(name + ' token default DACL: ' + default_dacl(token), flush=True)
            except Exception as error:
                print(f'{name} default-DACL query failed: {error}', flush=True)
        kernel.IsProcessInJob.argtypes = [w.HANDLE, w.HANDLE, ctypes.POINTER(w.BOOL)]
        kernel.QueryInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, w.LPVOID, w.DWORD, w.LPVOID]
        in_job, ui_limits = w.BOOL(), w.DWORD()
        checked(kernel.IsProcessInJob(kernel.GetCurrentProcess(), None, ctypes.byref(in_job)), 'IsProcessInJob')
        if in_job and kernel.QueryInformationJobObject(None, 4, ctypes.byref(ui_limits), ctypes.sizeof(ui_limits), None):
            print(f'Parent job UI restriction flags: {ui_limits.value:#x}', flush=True)
        else:
            print(f'Parent in job: {bool(in_job.value)}; UI query last-error: {ctypes.get_last_error()}', flush=True)
        # A separate experimental token changes object ACL defaults only. It is
        # never used for the acceptance smoke in this diagnostic candidate.
        diagnostic_ready = False
        try:
            checked(security.CreateRestrictedToken(source, 1, 1, ctypes.byref(deny), 0, None, 0, None,
                ctypes.byref(diagnostic_token)), 'CreateRestrictedToken(diagnostic)')
            security.GetSecurityDescriptorDacl.argtypes = [w.LPVOID, ctypes.POINTER(w.BOOL),
                ctypes.POINTER(w.LPVOID), ctypes.POINTER(w.BOOL)]
            security.SetTokenInformation.argtypes = [w.HANDLE, ctypes.c_int, w.LPVOID, w.DWORD]
            present, defaulted, acl = w.BOOL(), w.BOOL(), w.LPVOID()
            checked(security.GetSecurityDescriptorDacl(desktop.descriptor, ctypes.byref(present),
                ctypes.byref(acl), ctypes.byref(defaulted)), 'GetSecurityDescriptorDacl(private)')
            checked(security.SetTokenInformation(diagnostic_token, 6, ctypes.byref(acl), ctypes.sizeof(acl)),
                'SetTokenInformation(diagnostic default DACL)')
            print('Experimental token default DACL: ' + default_dacl(diagnostic_token), flush=True)
            diagnostic_ready = True
        except Exception as error:
            print(f'Experimental default-DACL setup failed: {type(error).__name__}: {error}', flush=True)

        class Attributes(ctypes.Structure):
            _fields_ = [('length', w.DWORD), ('descriptor', w.LPVOID), ('inherit', w.BOOL)]
        explicit_attributes = Attributes(ctypes.sizeof(Attributes), desktop.descriptor, False)

        def probe(label, argv, token, private, job_owned, marker, explicit_process_acl):
            child, owner = Process(), None
            report = {'label': label, 'exe': argv[0], 'private_desktop': private, 'job': job_owned, 'explicit_process_acl': explicit_process_acl}
            try:
                if marker is not None:
                    marker.unlink(missing_ok=True)
                    Path(str(marker) + '.started').unlink(missing_ok=True)
                start = Startup()
                start.cb = ctypes.sizeof(start)
                start.desktop = desktop.path if private else None
                command_line = ctypes.create_unicode_buffer(subprocess.list2cmdline(argv))
                attributes = ctypes.byref(explicit_attributes) if explicit_process_acl else None
                checked(security.CreateProcessAsUserW(token, argv[0], command_line, attributes, attributes, False,
                    0x08000000 | (4 if job_owned else 0), None, str(root), ctypes.byref(start),
                    ctypes.byref(child)), 'CreateProcessAsUserW(probe)')
                if job_owned:
                    owner = Job()
                    owner.attach_and_resume(SimpleNamespace(pid=child.pid))
                report['pid'] = child.pid
                outcome = kernel.WaitForSingleObject(child.process, 5000)
                report['wait'] = outcome
                if outcome == 0:
                    result = w.DWORD()
                    checked(kernel.GetExitCodeProcess(child.process, ctypes.byref(result)), 'GetExitCodeProcess(probe)')
                    report['exit_code'] = result.value
                    report['exit_hex'] = f'{result.value:#010x}'
                if marker is not None:
                    report['python_started'] = Path(str(marker) + '.started').exists()
                if marker is not None and marker.exists():
                    report['marker'] = json.loads(marker.read_text(encoding='utf-8-sig'))
            except Exception as error:
                report['error'] = f'{type(error).__name__}: {error}'
            finally:
                if owner is not None:
                    owner.close()
                if child.process:
                    kernel.TerminateProcess(child.process, 1)
                    report['cleanup_wait'] = kernel.WaitForSingleObject(child.process, 1000)
                for handle in (child.thread, child.process):
                    if handle:
                        kernel.CloseHandle(handle)
            print('NATIVE_STARTUP_PROBE ' + json.dumps(report, sort_keys=True), flush=True)
            return report

        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
        from kgmaker._windows_job import Job
        kernel.TerminateProcess.argtypes, kernel.TerminateProcess.restype = [w.HANDLE, w.UINT], w.BOOL
        reports = []
        full_matrix = ((False, False), (False, True), (True, False), (True, True))
        contrasting_cases = ((False, False), (True, True))
        variants = [('original', restricted, False, full_matrix),
                    ('explicit-process-thread-acl', restricted, True, contrasting_cases)]
        if diagnostic_ready:
            variants += [('explicit-default-dacl', diagnostic_token, False, contrasting_cases),
                         ('both-explicit-acls', diagnostic_token, True, contrasting_cases)]
        for token_name, token, explicit_process_acl, cases in variants:
            for private, job_owned in cases:
                for executable in ('cmd', 'python', 'powershell'):
                    label = f'{token_name}-desktop{int(private)}-job{int(job_owned)}-{executable}'
                    marker = root / (label + '.json') if executable != 'cmd' else None
                    if executable == 'cmd':
                        argv = [str(Path(os.environ['SystemRoot']) / 'System32/cmd.exe'), '/d', '/c', 'exit 0']
                    elif executable == 'python':
                        code = (f"open({str(marker) + '.started'!r},'w').write('Python initialized'); "
                            "import ctypes,json; "
                            f"open({str(marker)!r},'w').write(json.dumps({{'is_admin':bool(ctypes.windll.shell32.IsUserAnAdmin())}}))")
                        argv = [sys.executable, '-I', '-c', code]
                    else:
                        target = str(marker).replace("'", "''")
                        code = ("$p=New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent()); "
                            "$a=$p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator); "
                            f"[IO.File]::WriteAllText('{target}',(@{{is_admin=$a}}|ConvertTo-Json))")
                        argv = [command[0], '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', code]
                    reports.append(probe(label, argv, token, private, job_owned, marker, explicit_process_acl))
        (root / 'native-startup-diagnostics.json').write_text(json.dumps(reports, indent=2), encoding='utf-8')
        # Acceptance still exercises the original restricted token; the probe
        # variant must first supply native evidence before any repair is adopted.
        startup = Startup()
        startup.cb = ctypes.sizeof(startup)
        startup.desktop = desktop.path
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
        print(f'Restricted smoke exit code: {code.value} ({code.value:#010x})', flush=True)
        return code.value
    finally:
        if job is not None:
            job.close()
        if process.process:
            # A setup failure must not strand the suspended child.
            kernel.TerminateProcess.argtypes = [w.HANDLE, w.UINT]
            kernel.TerminateProcess(process.process, 1)
            kernel.WaitForSingleObject(process.process, 5000)
        if desktop is not None:
            desktop.close()
        for handle in (process.thread, process.process, diagnostic_token, restricted, source):
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
    raise SystemExit(0 if exit_code == 0 else 1)
