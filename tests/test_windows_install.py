"""W03: unsupported build execution is explicit; real Windows smoke is a CI gate."""
import os
from pathlib import Path
import shutil
import sys
from unittest.mock import patch

import pytest

from kgmaker.analysis_model import AnalysisError
from kgmaker import build_runner
from kgmaker.inspection import command
from kgmaker.worker_protocol import WorkerError


def test_unsupported_build_platform_fails_without_process_or_store_mutation(tmp_path, monkeypatch):
    monkeypatch.setattr(build_runner, '_BUILD_EXECUTE_SUPPORTED', False)
    store = tmp_path / '.kgmaker/graph.json'
    store.parent.mkdir()
    store.write_bytes(b'last valid graph')
    with patch('subprocess.Popen', side_effect=AssertionError('implicit process')):
        for call in (lambda: build_runner.create_plan(tmp_path), lambda: build_runner.run_plan({})):
            with pytest.raises(AnalysisError, match='UNSUPPORTED_PLATFORM.*BUILD_IMPORT'):
                call()
    assert store.read_bytes() == b'last valid graph'
    assert not (tmp_path / '.kgmaker/build-runs').exists()


@pytest.mark.parametrize('kind', ['jre', 'old-jdk'])
def test_unsupported_jdk_prerequisite_is_explicit_without_process(tmp_path, kind):
    binary = tmp_path / 'Java runtime with spaces/bin'
    binary.mkdir(parents=True)
    java = binary / 'java.exe'
    java.write_bytes(b'not executed')
    if kind == 'old-jdk':
        (binary / 'javac.exe').write_bytes(b'not executed')
        (binary.parent / 'release').write_text('JAVA_VERSION="17.0.1"\n')
    with patch('kgmaker.inspection.shutil.which', return_value=str(java)), \
            patch('subprocess.Popen', side_effect=AssertionError('implicit process')):
        with pytest.raises(WorkerError, match='(full JDK 21|requires JDK 21)') as error:
            command('jvm', tmp_path / 'workers')
    assert error.value.status == 'TOOLCHAIN_UNAVAILABLE'


def test_actual_windows_smoke_uses_restricted_token_and_paths_with_spaces():
    if os.environ.get('KGMAKER_REQUIRE_WINDOWS_SMOKE') != '1':
        pytest.skip('real non-admin Windows CI smoke is an explicit gate')
    if os.name != 'nt':
        pytest.fail('blocked: this mandatory smoke requires an actual Windows executor')
    import ctypes
    assert not ctypes.windll.shell32.IsUserAnAdmin(), 'Windows smoke process must not have administrator membership'
    assert ' ' in str(Path(sys.prefix)), sys.prefix
    assert ' ' in str(Path(__file__).resolve()), __file__
    assert ' ' in os.environ.get('JAVA_HOME', ''), 'JDK must be in a user-space path with spaces'
    for name in ('java', 'node'):
        executable = shutil.which(name)
        assert executable and executable.lower().endswith('.exe'), (name, executable)
        assert ' ' in executable, (name, executable)
