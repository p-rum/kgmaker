"""Check that the built worker has exactly its reviewed runtime dependencies."""

import hashlib
import json
from pathlib import Path


def main():
    worker = Path(__file__).resolve().parent
    target = worker / "target"
    if not (target / "kgmaker-excel-worker.jar").is_file():
        raise SystemExit("Missing Excel worker jar. Build workers/excel/pom.xml first.")
    expected = json.loads((worker / "dependencies.lock.json").read_text(encoding="utf-8"))
    actual = {}
    for path in (target / "lib").glob("*.jar"):
        with path.open("rb") as stream:
            actual[path.name] = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != expected:
        different = sorted(name for name in actual.keys() | expected.keys()
                           if actual.get(name) != expected.get(name))
        raise SystemExit("Excel dependency lock mismatch: " + ", ".join(different))
    print(f"Verified Excel worker and {len(actual)} runtime dependencies.")


if __name__ == "__main__":
    main()
