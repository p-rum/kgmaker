"""Fixture prerequisite failures stay distinct from product/protocol errors."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from kgmaker.worker_protocol import WorkerError
import test_coroutine_mapping as coroutine
import test_orm_xml_overrides as orm


@pytest.mark.parametrize('required', [False, True])
@pytest.mark.parametrize('available', ['missing', 'mismatched'])
def test_coroutine_unavailable_pin_never_compiles_or_passes(tmp_path, monkeypatch, required, available):
    compiler = tmp_path / 'kotlin/bin/kotlinc'
    compiler.parent.mkdir(parents=True)
    compiler.write_text('unused compiler')
    if available == 'mismatched':
        jar = tmp_path / 'kotlin/lib/kotlinx-coroutines-core-jvm.jar'
        jar.parent.mkdir()
        jar.write_bytes(b'not the pinned compiler-distribution coroutine library')
    monkeypatch.setattr(coroutine.shutil, 'which', lambda name: str(compiler))
    monkeypatch.setenv('KGMAKER_REQUIRE_WORKERS', '1' if required else '0')
    def forbidden(*args, **kwargs):
        raise AssertionError('Unverified compiler inputs must never be executed')
    monkeypatch.setattr(coroutine.subprocess, 'run', forbidden)
    factory = SimpleNamespace(mktemp=lambda name: tmp_path)
    expected = pytest.fail.Exception if required else pytest.skip.Exception
    with pytest.raises(expected):
        coroutine.compiled.__wrapped__(factory, SimpleNamespace(param=True))


@pytest.mark.parametrize('required', [False, True])
@pytest.mark.parametrize('strict', [False, True])
@pytest.mark.parametrize('entry', ['graph', 'worker'])
def test_orm_unavailable_worker_respects_required_policy(tmp_path, monkeypatch, required, strict, entry):
    def unavailable(*args, **kwargs):
        raise WorkerError('JDK21 or trusted worker unavailable', 'TOOLCHAIN_UNAVAILABLE')
    monkeypatch.setattr(orm, 'inspect_jvm', unavailable)
    monkeypatch.setenv('KGMAKER_REQUIRE_WORKERS', '1' if required else '0')
    with pytest.raises(pytest.fail.Exception if required else pytest.skip.Exception):
        (orm.inspect if entry == 'graph' else orm._inspect_worker)(tmp_path, strict=strict)


@pytest.mark.parametrize('required', [False, True])
@pytest.mark.parametrize('error', [WorkerError('invalid response', 'INVALID_PROTOCOL'), RuntimeError('actual implementation failure')])
def test_orm_never_skips_product_or_protocol_errors(tmp_path, monkeypatch, required, error):
    def broken(*args, **kwargs):
        raise error
    monkeypatch.setattr(orm, 'inspect_jvm', broken)
    monkeypatch.setenv('KGMAKER_REQUIRE_WORKERS', '1' if required else '0')
    with pytest.raises(type(error)) as caught:
        orm.inspect(tmp_path)
    assert caught.value is error
