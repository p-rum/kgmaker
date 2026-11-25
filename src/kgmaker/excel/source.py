"""Content-bound source selection and isolated transport for the Excel worker."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from ..analysis_model import ID_PATTERN, AnalysisError, decode_json, read_json, safe_path
from ..worker_protocol import WorkerError, request_worker
from ..workbooks import MAX_ENTRIES, MAX_EXPANDED_BYTES, MAX_XML_BYTES, binary_format

VERSION = "excel-migration-1"
WORKER = "excel-poi-6.0.0-1"
MAX_BOOK_BYTES = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
FORMATS = {"xlsm", "xlsx", "xls"}
XML_DECLARATION = re.compile(rb"<!\s*(?:DOCTYPE|ENTITY)\b", re.I)


@dataclass(frozen=True)
class Book:
    id: str
    relative: str
    path: Path


@dataclass(frozen=True)
class Manifest:
    path: Path
    sha256: str
    main: str
    books: tuple[Book, ...]
    links: dict[tuple[str, str], str]


def _regular(path: Path) -> None:
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise AnalysisError(f"Expected a regular input file: {path}")


def bounded_json(path: Path, maximum: int = MAX_ARTIFACT_BYTES):
    _regular(path)
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    if len(raw) > maximum:
        raise AnalysisError(f"JSON input is too large: {path.name}")
    return decode_json(raw.decode("utf-8"), path.name)


def manifest(path: Path) -> Manifest:
    _regular(path)
    with path.open("rb") as stream:
        raw = stream.read(262_145)
    if len(raw) > 262_144:
        raise AnalysisError("Excel manifest exceeds 256 KiB")
    config = decode_json(raw.decode("utf-8"), path.name)
    if (not isinstance(config, dict) or config.get("schema_version") != 1
            or not {"main", "workbooks"} <= config.keys()
            or config.keys() - {"schema_version", "main", "workbooks", "links"}):
        raise AnalysisError("Expected Excel manifest v1 with main, workbooks and optional links")
    rows = config["workbooks"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= 16:
        raise AnalysisError("The manifest must declare 1–16 workbooks")
    base = path.absolute().parent
    books = {}
    paths = set()
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {"id", "path"}
                or not isinstance(row["id"], str) or not ID_PATTERN.fullmatch(row["id"])
                or not isinstance(row["path"], str) or "\0" in row["path"]):
            raise AnalysisError("Each workbook needs a valid id and relative path")
        target = safe_path(base, row["path"])
        if row["id"] in books or target in paths:
            raise AnalysisError("Workbook IDs and paths must be unique")
        paths.add(target)
        books[row["id"]] = Book(row["id"], target.relative_to(base.resolve()).as_posix(), target)
    main = config["main"]
    if not isinstance(main, str) or main not in books:
        raise AnalysisError("Manifest main must select a declared workbook")
    links = {}
    declarations = config.get("links", [])
    if not isinstance(declarations, list):
        raise AnalysisError("Manifest links must be an array")
    for row in declarations:
        if (not isinstance(row, dict) or set(row) != {"from", "reference", "to"}
                or any(not isinstance(value, str) or not value for value in row.values())
                or row["from"] not in books or row["to"] not in books or row["from"] == row["to"]
                or len(row["reference"]) > 2_048):
            raise AnalysisError("Each link needs from/to workbook IDs and an exact reference identity")
        key = (row["from"], row["reference"])
        if key in links:
            raise AnalysisError(f"Duplicate link identity for workbook {row['from']}")
        links[key] = row["to"]
    ordered = [books[main], *(books[key] for key in sorted(books) if key != main)]
    return Manifest(path, hashlib.sha256(raw).hexdigest(), main, tuple(ordered), links)


def capture(book: Book, destination: Path | None = None) -> tuple[str, int]:
    """Hash the same stream the worker will parse. Keep no oversized snapshot."""
    _regular(book.path)
    sha = hashlib.sha256()
    size = 0
    with book.path.open("rb") as source:
        if destination is None:
            return hashlib.file_digest(source, "sha256").hexdigest(), os.fstat(source.fileno()).st_size
        with destination.open("wb") as output:
            for block in iter(lambda: source.read(256 * 1024), b""):
                sha.update(block)
                size += len(block)
                if size <= MAX_BOOK_BYTES:
                    output.write(block)
    if size > MAX_BOOK_BYTES:
        destination.unlink()
    return sha.hexdigest(), size


def preflight(path: Path, format: str) -> str | None:
    with path.open("rb") as stream:
        header = stream.read(8)
    container = binary_format(header)
    if format == "xls":
        return {"OLE_COMPOUND": None, "BIFF": "EXCEL_BIFF_UNSUPPORTED"}.get(
            container, "EXCEL_FORMAT_MISMATCH")
    if container == "OLE_COMPOUND":
        # Compound encrypted OOXML stores an explicit EncryptedPackage stream.
        # The worker distinguishes this from a BIFF workbook renamed to OOXML.
        return None
    if not header.startswith(b"PK\x03\x04"):
        return "EXCEL_FORMAT_MISMATCH"
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if (len(entries) > MAX_ENTRIES
                    or sum(entry.file_size for entry in entries) > MAX_EXPANDED_BYTES):
                return "EXCEL_ARCHIVE_LIMIT"
            seen = set()
            for entry in entries:
                name = PurePosixPath(entry.filename)
                entry_key = name.as_posix().casefold()
                if (entry_key in seen or name.is_absolute() or ".." in name.parts
                        or "\\" in entry.filename or ":" in entry.filename or entry.flag_bits & 1):
                    return "EXCEL_UNSAFE_ARCHIVE"
                seen.add(entry_key)
                if name.suffix.lower() not in {".xml", ".rels", ".vml"}:
                    continue
                if entry.file_size > MAX_XML_BYTES:
                    return "EXCEL_ARCHIVE_LIMIT"
                with archive.open(entry) as xml:
                    previous = b""
                    for block in iter(lambda: xml.read(32 * 1024), b""):
                        # UTF-16/32 declarations contain the same ASCII bytes with padding.
                        window = previous + block.replace(b"\0", b"")
                        if XML_DECLARATION.search(window):
                            return "EXCEL_UNSAFE_XML"
                        previous = window[-32:]
    except (zipfile.BadZipFile, OSError, NotImplementedError, RuntimeError):
        return "EXCEL_PARSE_FAILED"
    return None


def worker_command() -> list[str]:
    from ..inspection import worker_home

    home = worker_home() / "excel"
    target = home / "target"
    jar = target / "kgmaker-excel-worker.jar"
    java = shutil.which("java")
    if not java or not jar.is_file():
        raise WorkerError(
            "Excel analysis requires Java 17+ and the Excel worker. "
            "Install the distribution with the worker or build workers/excel explicitly.",
            "TOOLCHAIN_UNAVAILABLE",
        )
    expected = read_json(home / "dependencies.lock.json")
    actual = {path.name: path for path in (target / "lib").glob("*.jar")}
    if set(expected) != set(actual):
        raise WorkerError("Excel worker dependency inventory differs from its lock", "TOOLCHAIN_UNAVAILABLE")
    for name, path in actual.items():
        _regular(path)
        with path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != expected[name]:
                raise WorkerError(f"Excel worker dependency checksum mismatch: {name}", "TOOLCHAIN_UNAVAILABLE")
    return [str(Path(java).absolute()), "-Xmx512m", "-XX:+ExitOnOutOfMemoryError",
            "-XX:-UsePerfData", "-Djava.awt.headless=true", "-Djava.io.tmpdir=.",
            "-jar", str(jar)]


def extract(command: list[str], book: Book) -> tuple[str, int, dict | None, list[dict]]:
    format = book.path.suffix.lower().removeprefix(".")
    if format not in FORMATS:
        sha, size = capture(book)
        return sha, size, None, [{"code": "EXCEL_FORMAT_UNSUPPORTED"}]
    with tempfile.TemporaryDirectory(prefix="kgmaker-excel-") as temporary:
        root = Path(temporary)
        source = root / f"input.{format}"
        sha, size = capture(book, source)
        if size > MAX_BOOK_BYTES:
            return sha, size, None, [{"code": "EXCEL_INPUT_LIMIT"}]
        problem = preflight(source, format)
        if problem:
            return sha, size, None, [{"code": problem}]
        # Preserve mandatory Windows process variables, but drop inherited JVM
        # injection flags, credentials and proxy settings.
        keep = {"SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "TEMP", "TMP", "LANG", "LC_ALL"}
        environment = {key: value for key, value in os.environ.items() if key.upper() in keep}
        try:
            response = request_worker(command, {"operation": "analyze", "format": format},
                                      cwd=root, timeout=30, max_response=16 * 1024 * 1024,
                                      env=environment)
        except WorkerError as error:
            if error.status == "TOOLCHAIN_UNAVAILABLE" or "UnsupportedClassVersionError" in error.stderr:
                raise WorkerError("Excel worker requires a working Java 17+ runtime",
                                  "TOOLCHAIN_UNAVAILABLE") from error
            return sha, size, None, [{"code": f"EXCEL_WORKER_{error.status}"}]
        if response["worker"] != WORKER or response.get("status") not in {"OK", "REJECTED"}:
            raise WorkerError("Unexpected Excel worker version or response", "INVALID_PROTOCOL")
        facts = response.get("facts")
        problems = response.get("diagnostics")
        if (not isinstance(problems, list)
                or (response["status"] == "OK" and not isinstance(facts, dict))
                or (response["status"] == "REJECTED" and (facts is not None or not problems))):
            raise WorkerError("Invalid Excel worker facts", "INVALID_PROTOCOL")
        return sha, size, facts, problems
