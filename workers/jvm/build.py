"""Build only this trusted worker, offline, from pinned installed dependencies.

This script is never called implicitly by scan/build/hooks/feature preparation.
It does not build the inspected application or retrieve any dependencies.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--kotlin-home', type=Path, required=True)
p.add_argument('--maven-repository', type=Path, required=True)
p.add_argument('--java-home', type=Path, required=True)
args = p.parse_args()
root = Path(__file__).resolve().parent
target = root / 'target'
classes = target / 'classes'
libs = target / 'lib'
classes.mkdir(parents=True, exist_ok=True)
libs.mkdir(parents=True, exist_ok=True)
names = ['kotlin-compiler.jar', 'kotlin-stdlib.jar', 'kotlin-reflect.jar',
         'kotlin-script-runtime.jar', 'kotlinx-coroutines-core-jvm.jar', 'trove4j.jar',
         'annotations-13.0.jar']
dependencies = [args.kotlin_home / 'lib' / n for n in names]
for artifact in ['jackson-databind', 'jackson-core', 'jackson-annotations']:
    dependencies.append(args.maven_repository / 'com/fasterxml/jackson/core' / artifact / '2.18.2' / f'{artifact}-2.18.2.jar')
if any(not d.is_file() for d in dependencies):
    raise SystemExit('Dependency unavailable: ' + ', '.join(str(d) for d in dependencies if not d.is_file()))
lock = {'kotlin_compiler': '2.1.10', 'jackson': '2.18.2', 'bytecode_engine': 'ASM bundled in Kotlin 2.1.10',
        'dependencies': [{'name': d.name, 'sha256': hashlib.sha256(d.read_bytes()).hexdigest()} for d in dependencies]}
lock_path = root / 'dependencies.lock.json'
if lock_path.exists() and json.loads(lock_path.read_text()) != lock:
    raise SystemExit('Worker dependency checksum/version mismatch')
def executable(name):
    for path in (args.java_home / 'bin' / name, args.java_home / 'bin' / (name + '.exe')):
        if path.is_file():
            return str(path)
    raise SystemExit('JDK executable unavailable: ' + name)

classpath = os.pathsep.join(str(d) for d in dependencies)
kotlin = sorted((root / 'src/main/kotlin').rglob('*.kt'))
java = sorted((root / 'src/main/java').rglob('*.java'))
subprocess.run([executable('java'), '-Dkotlin.home=' + str(args.kotlin_home), '-cp', classpath,
                'org.jetbrains.kotlin.cli.jvm.K2JVMCompiler', '-jvm-target', '21', '-classpath', classpath,
                '-d', str(classes), *(str(f) for f in kotlin + java)], check=True,
               env={**os.environ, 'JAVA_HOME': str(args.java_home)})
subprocess.run([executable('javac'), '--release', '21', '-classpath', str(classes) + os.pathsep + classpath,
                '-d', str(classes), *(str(f) for f in java)], check=True)
for dependency in dependencies:
    shutil.copy2(dependency, libs / dependency.name)
manifest = target / 'MANIFEST.MF'
manifest.write_text('Manifest-Version: 1.0\nMain-Class: org.kgmaker.worker.JvmWorkerKt\nClass-Path: '
                    + ' '.join('lib/' + d.name for d in dependencies) + '\n\n')
jar = target / 'kgmaker-jvm-worker.jar'
subprocess.run([executable('jar'), '--create', '--date', '2025-01-01T00:00:00Z', '--file', str(jar), '--manifest', str(manifest),
                '-C', str(classes), '.'], check=True)
lock_path.write_text(json.dumps(lock, indent=2) + '\n')
license_source = args.kotlin_home / 'license'
if license_source.is_dir():
    shutil.copytree(license_source, target / 'licenses/kotlin', dirs_exist_ok=True)
print(json.dumps({'status': 'SUCCESS', 'worker_jar': str(jar),
                  'sha256': hashlib.sha256(jar.read_bytes()).hexdigest(), 'dependencies': lock}))
