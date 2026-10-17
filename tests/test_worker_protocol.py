import json
import sys
import tempfile
import unittest
from pathlib import Path

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


if __name__=='__main__':unittest.main()
