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
p.add_argument('--backend', choices=('k1', 'k2'), default='k1')
p.add_argument('--analysis-api-home', type=Path)
args = p.parse_args()
root = Path(__file__).resolve().parent
target = root / ('target-k2' if args.backend == 'k2' else 'target')
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
if args.backend == 'k2':
    if args.analysis_api_home is None:
        raise SystemExit('K2 build requires explicit --analysis-api-home; nothing is downloaded')
    api_names = ['analysis-api-for-ide', 'analysis-api-impl-base-for-ide',
                 'analysis-api-k2-for-ide', 'analysis-api-platform-interface-for-ide',
                 'analysis-api-standalone-for-ide', 'low-level-api-fir-for-ide',
                 'symbol-light-classes-for-ide']
    dependencies += [args.analysis_api_home / (n + '-2.1.10.jar') for n in api_names]
    dependencies.append(args.analysis_api_home / 'caffeine-2.9.3.jar')
if any(not d.is_file() for d in dependencies):
    raise SystemExit('Dependency unavailable: ' + ', '.join(str(d) for d in dependencies if not d.is_file()))
lock = {'kotlin_compiler': '2.1.10', 'jackson': '2.18.2', 'bytecode_engine': 'ASM bundled in Kotlin 2.1.10',
        'dependencies': [{'name': d.name, 'sha256': hashlib.sha256(d.read_bytes()).hexdigest()} for d in dependencies]}
lock_path = root / ('dependencies-k2.lock.json' if args.backend == 'k2' else 'dependencies.lock.json')
if args.backend == 'k2' and not lock_path.is_file():
    raise SystemExit('Pinned K2 dependency lock is required before building')
if lock_path.exists() and json.loads(lock_path.read_text()) != lock:
    raise SystemExit('Worker dependency checksum/version mismatch')
def executable(name):
    for path in (args.java_home / 'bin' / name, args.java_home / 'bin' / (name + '.exe')):
        if path.is_file():
            return str(path)
    raise SystemExit('JDK executable unavailable: ' + name)

classpath = os.pathsep.join(str(d) for d in dependencies)
kotlin = sorted((root / 'src/main/kotlin').rglob('*.kt'))
if args.backend == 'k2':
    kotlin = [f for f in kotlin if f.name != 'KotlinFrontend.kt'] + [root / 'k2/KotlinFrontend.kt']
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
classpath_header = 'Class-Path: ' + ' '.join('lib/' + d.name for d in dependencies)
# JAR manifests require continuation lines; the explicit K2 distribution is
# larger than the historical K1 classpath and exceeds the parser line limit.
folded = [classpath_header[:70]]
remaining = classpath_header[70:]
while remaining:
    folded.append(' ' + remaining[:69])
    remaining = remaining[69:]
manifest.write_text('Manifest-Version: 1.0\nMain-Class: org.kgmaker.worker.JvmWorkerKt\n'
                    + '\n'.join(folded) + '\n\n')
jar = target / 'kgmaker-jvm-worker.jar'
subprocess.run([executable('jar'), '--create', '--date', '2025-01-01T00:00:00Z', '--file', str(jar), '--manifest', str(manifest),
                '-C', str(classes), '.'], check=True)
lock_path.write_text(json.dumps(lock, indent=2) + '\n')
license_source = args.kotlin_home / 'license'
if license_source.is_dir():
    shutil.copytree(license_source, target / 'licenses/kotlin', dirs_exist_ok=True)
print(json.dumps({'status': 'SUCCESS', 'worker_jar': str(jar),
                  'sha256': hashlib.sha256(jar.read_bytes()).hexdigest(), 'dependencies': lock}))
