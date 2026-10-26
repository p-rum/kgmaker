"""User-requested deferred live connection: deterministic, read-only configuration."""
import json
from dataclasses import asdict
from unittest.mock import patch

import pytest

from kgmaker.analysis_model import AnalysisError
from kgmaker.confluence_sync_config import connection_status, load_connection_configuration


def settings(**changes):
    value = {"enabled": True, "host": "https://confluence.invalid/wiki", "api": "cloud-v1",
             "sandbox_space": "KGTEST", "auth": {"kind": "bearer", "token_env": "TEST_CF_TOKEN"}}
    value.update(changes)
    return {"documentation": {"confluence": {"directory": "offline-export", "connection": value}}}


def write_config(root, value):
    target = root / "kgmaker.json"
    target.write_text(json.dumps(value))
    return target


def test_absent_configuration_never_connects_or_creates_files(tmp_path):
    with patch("socket.create_connection", side_effect=AssertionError("network")), \
         patch("subprocess.Popen", side_effect=AssertionError("process")):
        config = load_connection_configuration(tmp_path)
        status = connection_status(config, environment={})
    assert status["configured"] is False
    assert status["enabled"] is False
    assert status["live_status"] == "NOT_RUN"
    assert list(tmp_path.iterdir()) == []


def test_configuration_and_auth_references_are_read_only_and_never_expose_values(tmp_path):
    path = write_config(tmp_path, settings())
    before = path.read_bytes()
    config = load_connection_configuration(tmp_path)
    status = connection_status(config, environment={"TEST_CF_TOKEN": "secret-never-output"})
    assert status["configured"] is True
    assert status["auth_ready"] is True
    assert status["live_status"] == "NOT_RUN"
    assert status["api"] == "cloud-v1"
    assert status["sandbox_space"] == "KGTEST"
    assert "secret-never-output" not in json.dumps(status)
    assert "secret-never-output" not in repr(config)
    assert asdict(config)["token_env"] == "TEST_CF_TOKEN"
    assert path.read_bytes() == before
    assert not (tmp_path / ".kgmaker").exists()


@pytest.mark.parametrize("changes", [
    {"enabled": "true"}, {"host": "https://user:secret@confluence.invalid"},
    {"host": "https://confluence.invalid/?token=secret"}, {"api": "guessed"},
    {"host": "https://confluence.invalid/\x00"}, {"host": "https://confluence.invalid/\x7f"},
    {"sandbox_space": ""}, {"auth": {"kind": "bearer", "token": "secret-never-output"}},
    {"auth": {"kind": "bearer", "token_env": "bad variable"}},
    {"auth": {"kind": "basic", "token_env": "TEST_CF_TOKEN"}},
    {"auth": {"kind": "bearer", "token_env": "TEST_CF_TOKEN", "username_env": "TEST_CF_USER"}},
])
def test_invalid_configuration_fails_before_mutation_without_echoing_secrets(tmp_path, changes):
    path = write_config(tmp_path, settings(**changes))
    before = path.read_bytes()
    with pytest.raises(AnalysisError) as error:
        load_connection_configuration(tmp_path)
    assert "secret-never-output" not in str(error.value)
    assert path.read_bytes() == before
    assert len(list(tmp_path.iterdir())) == 1


def test_precedence_and_explicit_missing_file_do_not_fall_back(tmp_path):
    write_config(tmp_path, settings(api="server-v1"))
    directory = tmp_path / ".kgmaker"
    directory.mkdir()
    (directory / "config.json").write_text(json.dumps(settings(api="cloud-v2")))
    assert load_connection_configuration(tmp_path).api == "cloud-v2"
    assert load_connection_configuration(tmp_path, tmp_path / "kgmaker.json").api == "server-v1"
    with pytest.raises(AnalysisError, match="unavailable"):
        load_connection_configuration(tmp_path, tmp_path / "missing.json")


def test_basic_auth_readiness_requires_both_references_and_preserves_not_run(tmp_path):
    write_config(tmp_path, settings(auth={"kind": "basic", "token_env": "TEST_CF_TOKEN",
                                         "username_env": "TEST_CF_USER"}))
    config = load_connection_configuration(tmp_path)
    assert connection_status(config, environment={"TEST_CF_TOKEN": "x"})["auth_ready"] is False
    status = connection_status(config, environment={"TEST_CF_TOKEN": "x", "TEST_CF_USER": "y"})
    assert status["auth_ready"] is True
    assert status["live_status"] == "NOT_RUN"


def test_unrelated_configuration_does_not_mask_connection_and_disabled_entry_is_authoritative(tmp_path):
    write_config(tmp_path, settings())
    directory = tmp_path / ".kgmaker"
    directory.mkdir()
    path = directory / "config.json"
    path.write_text('{"documentation":{"confluence":{"directory":"other-export"}}}')
    assert load_connection_configuration(tmp_path).enabled is True
    path.write_text(json.dumps(settings(enabled=False)))
    assert load_connection_configuration(tmp_path).enabled is False


def test_duplicate_keys_and_oversized_configuration_are_rejected(tmp_path):
    path = tmp_path / "kgmaker.json"
    path.write_text('{"documentation":{},"documentation":{}}')
    with pytest.raises(AnalysisError, match="duplicate"):
        load_connection_configuration(tmp_path)
    path.write_bytes(b" " * 65_537)
    with pytest.raises(AnalysisError, match="size"):
        load_connection_configuration(tmp_path)


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_non_json_constants_are_rejected_even_in_unrelated_settings(tmp_path, constant):
    path = tmp_path / "kgmaker.json"
    path.write_text('{"documentation":{},"unused":' + constant + '}')
    with pytest.raises(AnalysisError, match="strict JSON"):
        load_connection_configuration(tmp_path)


def test_excessive_json_nesting_has_a_structured_error(tmp_path):
    path = tmp_path / "kgmaker.json"
    path.write_text('{"unused":' + '[' * 12000 + '0' + ']' * 12000 + '}')
    with pytest.raises(AnalysisError, match="valid UTF-8 JSON"):
        load_connection_configuration(tmp_path)


def test_oversized_integer_has_a_structured_error(tmp_path):
    path = tmp_path / "kgmaker.json"
    path.write_text('{"unused":' + '9' * 5000 + '}')
    with pytest.raises(AnalysisError, match="supported parser limits"):
        load_connection_configuration(tmp_path)


def test_cli_status_is_offline_and_does_not_touch_last_graph(tmp_path, capsys, monkeypatch):
    from kgmaker.cli import main
    directory = tmp_path / ".kgmaker"
    directory.mkdir()
    store = directory / "graph.json"
    store.write_bytes(b"last valid graph")
    write_config(tmp_path, settings(enabled=False))
    monkeypatch.setenv("TEST_CF_TOKEN", "secret-never-output")
    monkeypatch.setattr("sys.argv", ["kgmaker", "confluence", "config", "--root", str(tmp_path)])
    with patch("socket.create_connection", side_effect=AssertionError("network")), \
         patch("subprocess.Popen", side_effect=AssertionError("process")):
        with pytest.raises(SystemExit) as error:
            main()
    assert error.value.code == 0
    output = capsys.readouterr().out
    assert json.loads(output)["live_status"] == "NOT_RUN"
    assert "secret-never-output" not in output
    assert store.read_bytes() == b"last valid graph"
