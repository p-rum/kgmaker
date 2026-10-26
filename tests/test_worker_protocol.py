import io
from types import SimpleNamespace
import os
import subprocess
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from kgmaker.worker_protocol import WorkerError, request_worker


class WorkerProtocolTests(unittest.TestCase):
    def call(self, script, **options):
        return request_worker([sys.executable,'-c',script],{'operation':'handshake'},cwd=Path.cwd(),**options)
    def test_transport_accepts_one_json_and_stderr_logs(self):
        script='import json,sys; json.load(sys.stdin); print("log",file=sys.stderr); print(json.dumps({"protocol_version":1,"worker":"test","capabilities":[],"compiler_version":"test"}))'
        self.assertEqual('test',self.call(script)['worker'])
    def test_protocol_stdout_logs_are_rejected(self):
        with self.assertRaises(WorkerError) as r:self.call('print("not a JSON protocol")')
        self.assertEqual('INVALID_PROTOCOL',r.exception.status)
    def test_timeout_and_output_limit_are_distinct(self):
        with self.assertRaises(WorkerError) as r:self.call('import time; time.sleep(5)',timeout=.1)
        self.assertEqual('TIMED_OUT',r.exception.status)
        with self.assertRaises(WorkerError) as r:self.call('print("x"*10000)',max_response=100)
        self.assertEqual('OUTPUT_LIMIT_EXCEEDED',r.exception.status)
    def test_cancellation_before_launch(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'cancel';path.write_text('cancel')
            with self.assertRaises(WorkerError) as r:self.call('raise Exception("must not launch")',cancel_file=path)
            self.assertEqual('CANCELLED',r.exception.status)
    def test_pipe_transport_does_not_require_selectable_pipe_handles(self):
        # Windows selectors accept sockets, not anonymous subprocess pipes.
        with patch('selectors.DefaultSelector', side_effect=OSError('pipes are not sockets')):
            response = self.call('import json,sys; json.load(sys.stdin); print(json.dumps({"protocol_version":1,"worker":"portable","capabilities":[]}))')
        self.assertEqual('portable', response['worker'])
    def test_large_request_and_stderr_are_drained_without_deadlock(self):
        script = 'import json,sys; sys.stderr.write("x"*400000); sys.stderr.flush(); value=json.load(sys.stdin); print(json.dumps({"protocol_version":1,"worker":"portable","capabilities":[],"size":len(value["payload"])}))'
        response = request_worker([sys.executable,'-c',script],{'payload':'x'*300000},cwd=Path.cwd(),timeout=10)
        self.assertEqual(300000, response['size'])
    def test_early_stdin_close_still_validates_stdout_protocol(self):
        with self.assertRaises(WorkerError) as caught:
            request_worker([sys.executable, '-c', 'import sys; sys.stdin.close(); print("not JSON")'],
                {'payload': 'x' * 1000000}, cwd=Path.cwd(), timeout=5)
        self.assertEqual('INVALID_PROTOCOL', caught.exception.status)
    def test_cancellation_unblocks_a_writer_and_closes_transport_threads(self):
        with tempfile.TemporaryDirectory() as folder:
            cancel = Path(folder) / 'cancel'
            timer = threading.Timer(.15, lambda: cancel.write_text('cancel'))
            timer.start()
            try:
                started = time.monotonic()
                with self.assertRaises(WorkerError) as caught:
                    request_worker([sys.executable, '-c', 'import time; time.sleep(10)'],
                        {'payload': 'x' * 1000000}, cwd=Path.cwd(), cancel_file=cancel, timeout=5)
                self.assertEqual('CANCELLED', caught.exception.status)
                self.assertLess(time.monotonic() - started, 2)
            finally:
                timer.join()
        self.assertFalse([t.name for t in threading.enumerate() if t.name.startswith('kgmaker-worker-')])

    @unittest.skipUnless(os.name == 'posix', 'POSIX initialization failure regression')
    def test_nonblocking_setup_failure_reaps_child_and_closes_pipes(self):
        processes = []
        original = subprocess.Popen
        def capture(*args, **kwargs):
            process = original(*args, **kwargs)
            processes.append(process)
            return process
        with patch('kgmaker.worker_protocol.subprocess.Popen', side_effect=capture), \
                patch('kgmaker.worker_protocol.os.set_blocking', side_effect=OSError('injected setup failure')):
            with self.assertRaisesRegex(OSError, 'injected setup failure'):
                self.call('import time; time.sleep(10)', timeout=.5)
        self.assertIsNotNone(processes[0].returncode)
        self.assertTrue(all(s.closed for s in (processes[0].stdin, processes[0].stdout, processes[0].stderr)))
        self.assertFalse([t for t in threading.enumerate() if t.name.startswith('kgmaker-worker-')])

    def test_interrupted_windows_attach_cleans_suspended_child_and_job(self):
        # Fault injection verifies cleanup ownership; it is not a Windows PASS.
        for error in (KeyboardInterrupt('injected attach interruption'), OSError('injected assign failure')):
            with self.subTest(error=type(error).__name__):
                events = []
                class FakeProcess:
                    pid = 123
                    def __init__(self):
                        self.stdin, self.stdout, self.stderr = io.BytesIO(), io.BytesIO(), io.BytesIO()
                        self.alive = True
                    def poll(self):
                        return None if self.alive else -1
                    def kill(self):
                        self.alive = False
                        events.append('kill-direct-child')
                    def wait(self):
                        assert not self.alive, 'Waiting on an unassigned suspended child would hang'
                        events.append('wait')
                process = FakeProcess()
                class FakeJob:
                    def attach_and_resume(self, child):
                        raise error  # Failure BEFORE assignment: this job owns no process.
                    def terminate(self):
                        events.append('terminate-empty-job')
                    def close(self):
                        events.append('close-job')
                cwd = Path.cwd()
                with patch.dict(sys.modules, {'kgmaker._windows_job': SimpleNamespace(Job=FakeJob)}), \
                        patch('kgmaker.worker_protocol.os.name', 'nt'), \
                        patch('kgmaker.worker_protocol.subprocess.Popen', return_value=process):
                    with self.assertRaises(WorkerError if isinstance(error, OSError) else KeyboardInterrupt) as caught:
                        request_worker(['unused-worker'], {}, cwd=cwd)
                if isinstance(error, OSError):
                    self.assertEqual('TOOLCHAIN_UNAVAILABLE', caught.exception.status)
                self.assertEqual(['terminate-empty-job', 'kill-direct-child', 'wait', 'close-job'], events)
                self.assertTrue(all(s.closed for s in (process.stdin, process.stdout, process.stderr)))

    def test_exited_parent_inherited_pipes_timeout_and_cancel_are_bounded(self):
        for cancelled in (False, True):
            with self.subTest(cancelled=cancelled), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                marker, cancel = root / 'child', root / 'cancel'
                sentinel = root / 'graph.json'
                sentinel.write_bytes(b'unchanged')
                script = ("import subprocess,sys,pathlib; "
                          "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(5)']); "
                          "pathlib.Path(sys.argv[1]).write_text(str(p.pid))")
                processes = []
                original = subprocess.Popen
                def capture(*args, **kwargs):
                    process = original(*args, **kwargs)
                    processes.append(process)
                    return process
                def trigger():
                    while not marker.exists() or not processes or processes[0].poll() is None:
                        if stop.wait(.01):
                            return
                    cancel.write_text('cancel')
                stop = threading.Event()
                watcher = threading.Thread(target=trigger)
                if cancelled:
                    watcher.start()
                descriptors = Path('/proc/self/fd')
                before_fds = len(list(descriptors.iterdir())) if descriptors.exists() else None
                started = time.monotonic()
                try:
                    with patch('kgmaker.worker_protocol.subprocess.Popen', side_effect=capture):
                        with self.assertRaises(WorkerError) as caught:
                            request_worker([sys.executable, '-c', script, str(marker)], {}, cwd=root,
                                timeout=10 if cancelled else 1, cancel_file=cancel if cancelled else None)
                    self.assertEqual('CANCELLED' if cancelled else 'TIMED_OUT', caught.exception.status)
                    self.assertLess(time.monotonic() - started, 3)
                    self.assertTrue(marker.exists(), 'Worker must have created the inherited-pipe descendant')
                    self.assertIsNotNone(processes[0].returncode)
                    self.assertTrue(all(stream.closed for stream in (processes[0].stdin, processes[0].stdout, processes[0].stderr)))
                    self.assertFalse([t for t in threading.enumerate() if t.name.startswith('kgmaker-worker-')])
                    self.assertEqual(b'unchanged', sentinel.read_bytes())
                    if before_fds is not None:
                        self.assertEqual(before_fds, len(list(descriptors.iterdir())))
                        state = Path('/proc') / marker.read_text() / 'stat'
                        deadline = time.monotonic() + 1
                        while state.exists():
                            try:
                                status = state.read_text().split(') ', 1)[1].split()[0]
                            except (FileNotFoundError, ProcessLookupError):
                                break
                            if status == 'Z':
                                break
                            self.assertLess(time.monotonic(), deadline,
                                'Inherited-pipe descendant must stop within the cleanup bound')
                            time.sleep(.01)
                finally:
                    stop.set()
                    if cancelled:
                        watcher.join()
                    if os.name == 'posix' and marker.exists():
                        try:
                            os.kill(int(marker.read_text()), 9)
                        except ProcessLookupError:
                            pass


if __name__=='__main__':unittest.main()
