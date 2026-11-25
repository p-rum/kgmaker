"""Exercise project lifecycle from an offline-installed wheel outside the checkout."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv


def test_installed_wheel_lifecycle(tmp_path):
    repository = Path(__file__).resolve().parents[1]
    source = tmp_path / 'source'
    source.mkdir()
    for name in ('pyproject.toml', 'README.md', 'LICENSE'):
        shutil.copy2(repository / name, source / name)
    shutil.copytree(repository / 'src', source / 'src',
                    ignore=shutil.ignore_patterns('__pycache__', '*.egg-info'))
    shutil.copytree(repository / 'workers', source / 'workers',
                    ignore=shutil.ignore_patterns('__pycache__', 'target', 'target-k2', 'node_modules'))
    def checked(argv, cwd, env=None):
        result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, result.stdout + result.stderr
        return result
    checked([sys.executable, '-m', 'pip', 'wheel', '--no-deps', '--no-build-isolation',
             '--no-index', '-w', str(tmp_path / 'dist'), '.'], source)
    wheel, = (tmp_path / 'dist').glob('*.whl')
    environment = tmp_path / 'venv'
    venv.EnvBuilder(with_pip=True).create(environment)
    python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    checked([str(python), '-m', 'pip', 'install', '--no-index', '--no-deps', str(wheel)], tmp_path)
    shutil.rmtree(source)
    target = tmp_path / 'project with spaces'
    target.mkdir()
    (target / 'app.py').write_bytes(b'print(1)')
    env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'KGMAKER_WORKERS_HOME')}
    for operation in ('init', 'upgrade'):
        checked([str(python), '-I', '-m', 'kgmaker', operation, '--root', str(target)], tmp_path, env)
    manifest = json.loads((target / '.kgmaker/install-manifest.json').read_text())
    assert '.agents/skills/kgmaker-context/SKILL.md' in manifest['files']
    assert '.kgmaker/templates/analysis.json' in manifest['files']
    checked([str(python), '-I', '-m', 'kgmaker', 'uninstall', '--root', str(target), '--dry-run'], tmp_path, env)
    assert (target / '.kgmaker').exists()
    checked([str(python), '-I', '-m', 'kgmaker', 'uninstall', '--root', str(target)], tmp_path, env)
    assert list(target.iterdir()) == [target / 'app.py']
