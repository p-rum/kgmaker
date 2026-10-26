"""T003-S11-W01: install real wheels into a clean venv outside the checkout."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import venv
from unittest.mock import patch

from kgmaker.inspection import command, worker_home
from kgmaker.worker_protocol import WorkerError

ROOT = Path(__file__).resolve().parents[1]


class WorkerSelectionTests(unittest.TestCase):
    def test_explicit_home_wins_and_never_falls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            selected = Path(directory) / "missing"
            with patch.dict(os.environ, {"KGMAKER_WORKERS_HOME": str(ROOT / "workers")}):
                self.assertEqual(selected, worker_home(selected))
                with self.assertRaises(WorkerError) as error:
                    command("typescript", selected)
                self.assertEqual("TOOLCHAIN_UNAVAILABLE", error.exception.status)

    def test_environment_home_wins_over_packaged_resources(self):
        with patch.dict(os.environ, {"KGMAKER_WORKERS_HOME": "~/chosen-workers"}):
            self.assertEqual(Path("~/chosen-workers").expanduser().resolve(), worker_home())

    def test_ambiguous_jvm_distribution_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            target = home / "jvm/target"
            target.mkdir(parents=True)
            for version in ("1", "2"):
                (target / f"kgmaker-jvm-worker-{version}.jar").write_bytes(b"not executed")
            jdk = home / 'jdk/bin'
            jdk.mkdir(parents=True)
            for name in ('java', 'javac'):
                (jdk / name).write_bytes(b'not executed')
            with patch("kgmaker.inspection.shutil.which", return_value=str(jdk / 'java')):
                with self.assertRaises(WorkerError) as error:
                    command("jvm", home)
            self.assertEqual("TOOLCHAIN_UNAVAILABLE", error.exception.status)
            self.assertIn('ambiguous', str(error.exception))


class InstalledWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='kgmaker user space ')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.directory = Path(cls.temporary.name)
        cls.environment = {k: v for k, v in os.environ.items()
                           if k not in {"PYTHONPATH", "KGMAKER_WORKERS_HOME", "NODE_PATH"}}
        cls.source_python = cls.install_wheel("core", source_only=True)
        cls.python = cls.install_wheel("optional", source_only=False)

    @classmethod
    def install_wheel(cls, name, *, source_only):
        directory = cls.directory / name
        source = directory / "source"
        source.mkdir(parents=True)
        for name in ("pyproject.toml", "README.md", "LICENSE"):
            shutil.copy2(ROOT / name, source / name)
        shutil.copytree(ROOT / "src", source / "src", ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
        ignored = ["__pycache__", "classes", ".bin"]
        if source_only:
            ignored += ["target", "target-k2", "node_modules"]
        shutil.copytree(ROOT / "workers", source / "workers", ignore=shutil.ignore_patterns(*ignored))
        # Exercise the sdist -> wheel route used by an offline pip install.
        result = subprocess.run([sys.executable, "-c",
                                 "from setuptools.build_meta import build_sdist; build_sdist('../sdist')"],
                                cwd=source, capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        archive, = (directory / "sdist").glob("*.tar.gz")
        with tarfile.open(archive) as bundle:
            bundle.extractall(directory / "unpacked", filter="data")
        source, = (directory / "unpacked").iterdir()
        # Packaging is explicit and offline. No build isolation downloads.
        result = subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps",
                                 "--no-build-isolation", "--no-index", "-w", str(directory / "dist"), "."],
                                cwd=source, capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        wheel, = (directory / "dist").glob("*.whl")
        installed = directory / "venv"
        venv.EnvBuilder(with_pip=True).create(installed)
        python = installed / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        result = subprocess.run([str(python), "-m", "pip", "install", "--no-index", "--no-deps", str(wheel)],
                                cwd=cls.directory, env=cls.environment, capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        # Remove all build inputs: success must come from the installed wheel.
        shutil.rmtree(source)
        return python

    def run_installed(self, script, *, no_tools=False, source_only=False):
        environment = dict(self.environment)
        if no_tools:
            environment["PATH"] = str(self.directory / "no-tools")
        python = self.source_python if source_only else self.python
        result = subprocess.run([str(python), "-c", script], cwd=self.directory,
                                env=environment, capture_output=True, text=True, timeout=60)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        return result.stdout

    def test_source_only_without_node_or_jdk_or_child_processes(self):
        self.run_installed('''
from pathlib import Path
from unittest.mock import patch
from kgmaker.inspection import command, worker_home
from kgmaker.scanner import scan_repository
from kgmaker.store import save_graph, load_graph
from kgmaker.worker_protocol import WorkerError
home = worker_home()
assert "site-packages" in str(home), home
assert (home / "typescript/worker.cjs").is_file()
assert (home / "jvm/build.py").is_file()
assert (home / "build/gradle/export.gradle").is_file()
assert not (home / "jvm/target").exists()
assert not (home / "jvm/target-k2").exists()
assert not (home / "typescript/node_modules").exists()
root = Path("source-only"); root.mkdir()
(root / "app.py").write_text("def hello(): return 42\\n")
with patch("subprocess.Popen", side_effect=AssertionError("implicit process")):
    graph = scan_repository(root.resolve())
    assert any(n.name == "hello" for n in graph.nodes)
    save_graph(graph, root.resolve())
    assert load_graph(root.resolve()).files == graph.files
    before = (root / ".kgmaker/graph.json").read_bytes()
    for language in ("jvm", "typescript"):
        try: command(language)
        except WorkerError as error: assert error.status == "TOOLCHAIN_UNAVAILABLE"
        else: raise AssertionError("runtime should be unavailable")
    assert (root / ".kgmaker/graph.json").read_bytes() == before
''', no_tools=True, source_only=True)

    def test_missing_installed_artifacts_do_not_mutate_last_graph(self):
        self.run_installed('''
from pathlib import Path
from unittest.mock import patch
from kgmaker.inspection import inspect_frontend, inspect_jvm
from kgmaker.worker_protocol import WorkerError
root = Path("unavailable"); root.mkdir()
(root / ".kgmaker").mkdir()
store = root / ".kgmaker/graph.json"; store.write_bytes(b"last valid generation")
with patch("subprocess.Popen", side_effect=AssertionError("implicit process")):
    for inspect in (inspect_frontend, inspect_jvm):
        try: inspect(root.resolve())
        except WorkerError as error: assert error.status == "TOOLCHAIN_UNAVAILABLE"
        else: raise AssertionError("incomplete distribution was accepted")
assert store.read_bytes() == b"last valid generation"
''', source_only=True)

    def test_packaged_typescript_analyzes_outside_checkout(self):
        if not shutil.which("node") or not (ROOT / "workers/typescript/node_modules/typescript/lib/typescript.js").is_file():
            if os.environ.get("KGMAKER_REQUIRE_WORKERS") == "1":
                self.fail("blocked: actual TypeScript worker and Node required")
            self.skipTest("blocked: actual TypeScript worker and Node required")
        self.run_installed('''
from pathlib import Path
from kgmaker.inspection import inspect_frontend, worker_home
root = Path("frontend"); root.mkdir()
(root / "tsconfig.json").write_text('{"compilerOptions":{"strict":true},"include":["*.ts"]}')
(root / "app.ts").write_text("export function target(x: number) { return x + 1; }\\nexport function caller() { return target(2); }\\n")
result = inspect_frontend(root.resolve(), publish=True)
graph = result["graph"]
assert len([c for c in graph["call_sites"] if c.get("declared_target")]) == 1, graph["call_sites"]
assert (worker_home() / "typescript/node_modules/typescript/lib/lib.d.ts").is_file()
assert (root / ".kgmaker/graph.json").is_file()
''')

    def test_packaged_jvm_analyzes_outside_checkout(self):
        if not shutil.which("java") or not (ROOT / "workers/jvm/target/kgmaker-jvm-worker.jar").is_file():
            if os.environ.get("KGMAKER_REQUIRE_WORKERS") == "1":
                self.fail("blocked: actual JVM worker and JDK required")
            self.skipTest("blocked: actual JVM worker and JDK required")
        self.run_installed('''
from pathlib import Path
from kgmaker.inspection import inspect_jvm
root = Path("jvm"); (root / "src/main/java").mkdir(parents=True)
(root / "src/main/java/App.java").write_text("class App { int target() { return 1; } int caller() { return target(); } }")
result = inspect_jvm(root.resolve(), publish=True)
assert any(c.get("declared_target") for c in result["graph"]["call_sites"]), result
assert (root / ".kgmaker/graph.json").is_file()
from kgmaker.inspection import worker_home
assert (worker_home() / "jvm/target/licenses/kotlin/LICENSE.txt").is_file()
''')

    def test_packaged_kotlin_analyzes_in_user_space_with_spaces(self):
        if not shutil.which('java') or not (ROOT / 'workers/jvm/target/kgmaker-jvm-worker.jar').is_file():
            if os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1':
                self.fail('blocked: actual JVM worker and JDK required')
            self.skipTest('blocked: actual JVM worker and JDK required')
        self.run_installed('''
from pathlib import Path
from kgmaker.inspection import inspect_jvm, worker_home
home = worker_home()
assert ' ' in str(home), home
root = Path('kotlin user project'); (root / 'src/main/kotlin').mkdir(parents=True)
(root / 'src/main/kotlin/App.kt').write_text('class App { fun target(): Int = 1; fun caller(): Int = target() }')
result = inspect_jvm(root.resolve(), classpath=[str(home / 'jvm/target/lib/kotlin-stdlib.jar')])
targets = {s['id']: s for s in result['graph']['symbols']}
assert any(c.get('declared_target') and targets[c['declared_target']]['path'] == 'src/main/kotlin/App.kt'
           for c in result['graph']['call_sites']), result
assert (root / '.kgmaker/graph.json').is_file()
''')

    def test_packaged_k2_analyzes_outside_checkout(self):
        if not shutil.which("java") or not (ROOT / "workers/jvm/target-k2/kgmaker-jvm-worker.jar").is_file():
            if os.environ.get("KGMAKER_REQUIRE_K2") == "1":
                self.fail("blocked: actual K2 Analysis API worker and JDK required")
            self.skipTest("blocked: actual K2 Analysis API worker and JDK required")
        self.run_installed('''
from pathlib import Path
from kgmaker.inspection import inspect_jvm, worker_home
root = Path("k2"); (root / "src/main/kotlin").mkdir(parents=True)
(root / "src/main/kotlin/App.kt").write_text("fun target(): Int = 1\\nfun caller(): Int = target()\\n")
stdlib = worker_home() / "jvm/target-k2/lib/kotlin-stdlib.jar"
result = inspect_jvm(root.resolve(), kotlin_backend="k2", classpath=[str(stdlib)])
assert result["context"]["worker"]["kotlin_backend"] == "k2-analysis-api-2.1.10-v1"
assert any(c.get("declared_target") for c in result["graph"]["call_sites"]), result
assert (root / ".kgmaker/graph.json").is_file()
''')
