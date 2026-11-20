"""T047-S01 source-only workspace and deterministic mutations."""
import shutil
from pathlib import Path

from kgmaker.analysis_model import digest, file_hash, read_json, write_json

FIXTURES = Path(__file__).resolve().parents[1]
TARGET = "api/src/main/kotlin/Scoring.kt"
CALLER = "api/src/main/kotlin/Caller.kt"
INDEPENDENT = "independent/src/main/kotlin/Other.kt"
KAFKA_CONFIG = "independent/src/main/resources/application-blue.properties"
CONTRACT = "contracts/exposure.json"
CLIENT = "generated/exposure.ts"
PAGE = "src/page.tsx"
GENERATION = "generation.json"


def make_workspace(root):
    for repo in ("backend", "frontend"):
        shutil.copytree(FIXTURES / "multirepo-analysis" / repo, root / repo)
    backend = root / "backend"
    write_json(root / "frontend/tsconfig.json", {"compilerOptions": {"strict": False}})
    for path, source in {
        TARGET: "package fixture\nfun score(value: Int): Int { return value }\n"
                "fun score(value: String): Int { return value.length }\n",
        CALLER: "package fixture\nfun callScore(): Int {\n    return score(2) + missingScore()\n}\n",
        INDEPENDENT: "package other\nfun independent(): Int { return 3 }\n",
    }.items():
        path = backend / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    kafka = FIXTURES / "kafka-bindings"
    config = read_json(kafka / "workspace.json")
    shutil.copyfile(kafka / "schemas/Order.json", backend / "contracts/Order.json")
    for direction, module, service, owner, binding in zip(
            ("producer", "consumer"), ("api", "independent"), config["services"],
            config["service_ownership"]["services"], config["kafka_bindings"]["bindings"],
            strict=True):
        shutil.copytree(kafka / direction / "src/main/resources",
                        backend / module / "src/main/resources")
        service.update(backend_repo="backend",
                       contract={"repo_id": "backend", "path": "contracts/Order.json"})
        owner["roots"] = [{"repo_id": "backend", "path": module + "/src/main"}]
        binding.update(repo_id="backend", module=module,
                       contract={**service["contract"], "release": "r1"})
        for item in binding["config_files"]:
            item["path"] = module + "/" + item["path"]
    config.update(workspace_id="incremental-integrity", repositories=[
        {"id": "backend", "role": "backend", "path": "backend",
         "flyway": {"database_id": "fixture-db", "stream_id": "main"}},
        {"id": "frontend", "role": "frontend", "path": "frontend"},
    ])
    config["services"].append({
        "id": "exposure-api", "backend_repo": "backend", "frontend_repos": ["frontend"],
        "test_repos": [], "contract": {"repo_id": "backend", "path": "contracts/exposure.json"},
        "consumer_path_prefix": "/api",
    })
    config["release_mapping"] = {"schema_version": 1, "mappings": [{
        "id": "exposure-release",
        "producer": {"repo_id": "backend", "manifest_path": "release/exposure-build.json",
                     "context_id": "build:fixture"},
        "consumer": {"repo_id": "frontend", "context_id": "compiler:fixture"},
        "output_sha256": "0" * 64,
    }]}
    manifest = root / "workspace.json"
    write_json(manifest, config)
    return manifest


def snapshot(root):
    return {path.relative_to(root).as_posix(): file_hash(path)
            for path in sorted(root.rglob("*")) if path.is_file()}


def declare_typed_client(root, origin):
    contract = root / "backend" / CONTRACT
    document = read_json(contract)
    response = document["paths"]["/exposure"]["get"]["responses"]["200"]
    field = response["content"]["application/json"]["schema"]["properties"]["decline"]
    field.update({"x-kgmaker-source": origin["id"], "x-kgmaker-source-sha256": origin["sha256"]})
    write_json(contract, document)

    frontend = root / "frontend"
    client = frontend / CLIENT
    client.parent.mkdir()
    client.write_text(
        "export interface Exposure { decline: number; }\n"
        "declare global { namespace JSX { interface IntrinsicElements {\n"
        "    span: { 'data-testid': string; children?: number };\n"
        "} } }\n", encoding="utf-8")
    page = frontend / PAGE
    page.write_text(
        "import type { Exposure } from '../generated/exposure';\n\n"
        + page.read_text(encoding="utf-8").replace("const data =", "const data: Exposure ="),
        encoding="utf-8")
    write_json(frontend / "tsconfig.json", {"compilerOptions": {"strict": True, "jsx": "preserve"}})
    write_json(frontend / GENERATION, {
        "source_contract": {"repo_id": "backend", "path": CONTRACT, "sha256": file_hash(contract)},
        "generated_files": [CLIENT], "generated_sha256": {CLIENT: file_hash(client)},
        "release": document["info"]["version"],
    })
    manifest = root / "workspace.json"
    workspace = read_json(manifest)
    service = next(item for item in workspace["services"] if item["id"] == "exposure-api")
    service["generated_clients"] = [{"repo_id": "frontend", "path": CLIENT,
                                     "metadata_path": GENERATION, "consumers": [PAGE]}]
    write_json(manifest, workspace)


def change_contract_version(root):
    path = root / "backend" / CONTRACT
    document = read_json(path)
    document["info"]["version"] = "2"
    write_json(path, document)


def change_kafka_topic(root):
    (root / "backend" / KAFKA_CONFIG).write_text("orders.topic=isolated\n", encoding="utf-8")


def mutations(root):
    backend = root / "backend"
    target = backend / TARGET
    added = target.with_name("Added.kt")
    moved = target.with_name("Renamed.kt")
    flyway = backend / "src/main/resources/db/migration/V11__optional.sql"
    tsconfig = root / "frontend/tsconfig.json"

    def write(path, content):
        path.write_text(content, encoding="utf-8")

    steps = [
        ("comment", lambda: write(target, "// comment\n" + target.read_text(encoding="utf-8")),
         (target,)),
        ("body", lambda: write(target, target.read_text(encoding="utf-8").replace(
            "return value }", "return value + 1 }")), (target,)),
        ("add", lambda: write(added, "package fixture\nfun missingScore(): Int = 0\n"), (added,)),
        ("move", lambda: target.rename(moved), (target, moved)),
        ("delete", moved.unlink, (moved,)),
        ("contract", lambda: change_contract_version(root), (backend / CONTRACT,)),
        ("kafka", lambda: change_kafka_topic(root), (backend / KAFKA_CONFIG,)),
        ("flyway", lambda: write(flyway, "CREATE TABLE extra (id integer);\n"), (flyway,)),
        ("tsconfig", lambda: write_json(tsconfig, {"compilerOptions": {"strict": True}}),
         (tsconfig,)),
    ]
    for label, operation, expected in steps:
        before = snapshot(root)
        operation()
        after = snapshot(root)
        changed = sorted(key for key in before.keys() | after.keys() if before.get(key) != after.get(key))
        expected_paths = sorted(path.relative_to(root).as_posix() for path in expected)
        yield label, digest(after), changed, expected_paths
