"""Explicit developer/CI download of checksum-pinned Analysis API additions.

Never imported or called by kgmaker, inspection, installation, or build.py.
The compiler distribution and Jackson remain separately supplied build inputs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
lock = json.loads((Path(__file__).parent / "dependencies-k2.lock.json").read_text())
selected = [entry for entry in lock["dependencies"]
            if entry["name"].endswith("-for-ide-2.1.10.jar") or entry["name"] == "caffeine-2.9.3.jar"]
if len(selected) != 8:
    raise SystemExit("Expected exactly eight pinned K2 additions")
args.output.mkdir(parents=True, exist_ok=True)
for entry in selected:
    name = entry["name"]
    target = args.output / name
    if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == entry["sha256"]:
        continue
    if name == "caffeine-2.9.3.jar":
        url = "https://repo.maven.apache.org/maven2/com/github/ben-manes/caffeine/caffeine/2.9.3/" + name
    else:
        artifact = name.removesuffix("-2.1.10.jar")
        url = ("https://maven.pkg.jetbrains.space/kotlin/p/kotlin/kotlin-ide-plugin-dependencies/"
               "org/jetbrains/kotlin/" + artifact + "/2.1.10/" + name)
    with urllib.request.urlopen(url, timeout=60) as response:
        content = response.read(32 * 1024 * 1024 + 1)
    if len(content) > 32 * 1024 * 1024 or hashlib.sha256(content).hexdigest() != entry["sha256"]:
        raise SystemExit("Dependency checksum/size mismatch: " + name)
    with tempfile.NamedTemporaryFile(dir=args.output, delete=False) as temporary:
        temporary.write(content)
        staged = Path(temporary.name)
    try:
        staged.replace(target)
    finally:
        staged.unlink(missing_ok=True)
print("Prepared 8 checksum-pinned K2 Analysis API additions")
