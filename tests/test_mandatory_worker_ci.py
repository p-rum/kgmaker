"""T003-S11-W04: missing real prerequisites must fail required CI gates."""
import unittest

import pytest

import test_compiler_workers as compiler
import test_k2_backend as k2
import test_kafka_retry_dlt as retry
from kgmaker.inspection import command


@pytest.mark.parametrize("required", [None, "0", "1"])
@pytest.mark.parametrize("missing", ["jvm", "jdk", "typescript", "mixed-fixture", "k2", "retry-api"])
def test_missing_prerequisite_fails_required_but_skips_optional(tmp_path, monkeypatch, required, missing):
    """Call the actual integration setup, using an empty distribution/fixture.

    Earlier prerequisites are acknowledged only to reach each independent gate;
    no worker, compiler, package manager or application may execute here.
    """
    flag = "KGMAKER_REQUIRE_K2" if missing == "k2" else "KGMAKER_REQUIRE_WORKERS"
    monkeypatch.delenv(flag, raising=False)
    if required is not None:
        monkeypatch.setenv(flag, required)
    store = tmp_path / ".kgmaker/graph.json"
    store.parent.mkdir()
    store.write_bytes(b"last valid generation")
    empty_home = tmp_path / "missing-workers"
    # Discovery-only tool paths make the missing-distribution cases independent
    # of the host's JDK/Node installation. These files must never be executed.
    tools = tmp_path / "tools/bin"
    tools.mkdir(parents=True)
    for name in ("java", "javac", "node"):
        (tools / name).write_text("must not execute")
    monkeypatch.setattr("kgmaker.inspection.shutil.which", lambda name:
                        None if missing == "jdk" and name == "java" else str(tools / name))

    def forbidden_process(*args, **kwargs):
        raise AssertionError("prerequisite discovery must not start a process")

    monkeypatch.setattr("subprocess.Popen", forbidden_process)
    if missing == "retry-api":
        # The real API discovery helper must fail required runs before a compiler
        # sees unpinned inputs; a different required backend flag is independent.
        lock = retry.ROOT / "fixtures/kafka-retry-dlt/dependencies.lock.json"
        fixture = tmp_path / "fixtures/kafka-retry-dlt"
        fixture.mkdir(parents=True)
        (fixture / "dependencies.lock.json").write_bytes(lock.read_bytes())
        monkeypatch.setattr(retry, "ROOT", tmp_path)
        monkeypatch.setenv("KGMAKER_TEST_MAVEN_REPOSITORY", str(tmp_path / "missing-api"))
        monkeypatch.delenv("KGMAKER_REQUIRE_K2", raising=False)
        expected = pytest.fail.Exception if required == "1" else pytest.skip.Exception
        with pytest.raises(expected, match="Pinned retry API input unavailable"):
            retry.api_inputs()
    elif missing == "k2":
        monkeypatch.setattr(k2, "command", lambda *args, **kwargs:
                            command("jvm", empty_home, kotlin_backend="k2"))
        expected = pytest.fail.Exception if required == "1" else pytest.skip.Exception
        with pytest.raises(expected, match="backend k2" if required == "1" else "K2 worker"):
            next(k2.actual_k2.__wrapped__())
    else:
        monkeypatch.setattr(compiler.CompilerWorkerTests, "jvm", None, raising=False)
        monkeypatch.setattr(compiler.CompilerWorkerTests, "ts", None, raising=False)
        def discover(kind):
            if kind == missing or missing == "jdk" and kind == "jvm":
                return command(kind, empty_home)
            return ["earlier-prerequisite-not-executed"]

        monkeypatch.setattr(compiler, "command", discover)
        monkeypatch.setattr(compiler, "FIXTURE", tmp_path / "missing-mixed-fixture")
        expected = AssertionError if required == "1" else unittest.SkipTest
        reason = "Actual Maven fixture build" if missing == "mixed-fixture" else "worker"
        with pytest.raises(expected, match=reason):
            compiler.CompilerWorkerTests.setUpClass()
    assert store.read_bytes() == b"last valid generation"
    assert not empty_home.exists()
