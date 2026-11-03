"""Fixture prerequisite failures stay distinct from product/protocol errors."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from kgmaker.worker_protocol import WorkerError
import test_coroutine_mapping as coroutine
import test_orm_xml_overrides as orm
import test_worker_install as installed
import unittest


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


@pytest.mark.parametrize('method', ['test_packaged_jvm_analyzes_outside_checkout',
    'test_packaged_kotlin_analyzes_in_user_space_with_spaces', 'test_packaged_k2_analyzes_outside_checkout'])
@pytest.mark.parametrize('required', [False, True])
def test_packaged_worker_checks_full_jdk_before_installed_analysis(monkeypatch, method, required):
    case = installed.InstalledWorkerTests(method)
    def unavailable(*args, **kwargs):
        raise WorkerError('Full JDK21 prerequisite unavailable', 'TOOLCHAIN_UNAVAILABLE')
    monkeypatch.setattr(installed, 'command', unavailable)
    monkeypatch.setenv('KGMAKER_REQUIRE_WORKERS', '1' if required else '0')
    monkeypatch.setenv('KGMAKER_REQUIRE_K2', '0')
    def forbidden(*args, **kwargs):
        raise AssertionError('Installed analysis must not start without prerequisites')
    monkeypatch.setattr(case, 'run_installed', forbidden)
    with pytest.raises(AssertionError if required else unittest.SkipTest, match='blocked:'):
        getattr(case, method)()


def test_packaged_k2_required_flag_rejects_missing_prerequisite(monkeypatch):
    case = installed.InstalledWorkerTests('test_packaged_k2_analyzes_outside_checkout')
    def unavailable(*args, **kwargs):
        raise WorkerError('Missing K2 toolchain', 'TOOLCHAIN_UNAVAILABLE')
    monkeypatch.setattr(installed, 'command', unavailable)
    monkeypatch.setenv('KGMAKER_REQUIRE_WORKERS', '0')
    monkeypatch.setenv('KGMAKER_REQUIRE_K2', '1')
    monkeypatch.setattr(case, 'run_installed', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('Do not start')))
    with pytest.raises(AssertionError, match='blocked:'):
        case.test_packaged_k2_analyzes_outside_checkout()


@pytest.mark.parametrize('error', [WorkerError('broken protocol', 'INVALID_PROTOCOL'), RuntimeError('product failure')])
def test_packaged_worker_does_not_hide_other_errors(monkeypatch, error):
    case = installed.InstalledWorkerTests('test_packaged_jvm_analyzes_outside_checkout')
    def broken(*args, **kwargs):
        raise error
    monkeypatch.setattr(installed, 'command', broken)
    with pytest.raises(type(error)) as caught:
        case.test_packaged_jvm_analyzes_outside_checkout()
    assert caught.value is error
