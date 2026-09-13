"""
AlphaOmega Script Documentation Audit Export

Purpose:
    Exports the current development implementation inventory into one
    documentation audit package for controlled Gold Standard review.

Responsibilities:
    - Read active artifact metadata from public.scripts.
    - Preserve human-authored and machine-discovered inventory metadata.
    - Read the current source text for each inventoried repository artifact.
    - Derive direct inbound script dependencies without storing them.
    - Produce summary statistics for the current inventory.
    - Write one deterministic JSON audit package to artifacts/reports.

Does NOT:
    - Modify repository source files.
    - Modify database records.
    - Execute inventoried Python or SQL artifacts.
    - Infer undocumented architectural intent.
    - Store reverse dependencies in the database.
    - Create Knowledge Objects.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from common.security.local_credential_provider import LocalCredentialProvider
from scripts.database.database_connection import DatabaseConnection


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIRECTORY = REPOSITORY_ROOT / "artifacts" / "reports"
REPORT_PATH = REPORT_DIRECTORY / "script_documentation_audit.json"


def create_database_client():
    credential_provider = LocalCredentialProvider()
    database_connection = DatabaseConnection(credential_provider)
    return database_connection.connect()


def normalize_json_array(value):
    if isinstance(value, list):
        return value

    return []


def load_active_scripts(client):
    response = (
        client.table("scripts")
        .select(
            "artifact_path,"
            "artifact_name,"
            "artifact_type,"
            "module_docstring,"
            "purpose,"
            "responsibilities,"
            "verifies,"
            "exclusions,"
            "classes,"
            "functions,"
            "imports,"
            "referenced_scripts,"
            "referenced_tables,"
            "referenced_rpcs,"
            "defined_rpcs,"
            "content_hash,"
            "line_count,"
            "documentation_status,"
            "scan_error,"
            "last_scanned_at,"
            "is_active"
        )
        .eq("is_active", True)
        .order("artifact_path")
        .execute()
    )

    return response.data or []


def read_source_text(artifact_path):
    if not artifact_path:
        return None, "Artifact path is missing."

    source_path = REPOSITORY_ROOT / Path(artifact_path)

    try:
        resolved_source_path = source_path.resolve()
        resolved_repository_root = REPOSITORY_ROOT.resolve()

        if (
            resolved_source_path != resolved_repository_root
            and resolved_repository_root not in resolved_source_path.parents
        ):
            return None, "Artifact path resolves outside the repository root."

        if not resolved_source_path.exists():
            return None, "Artifact file does not exist."

        if not resolved_source_path.is_file():
            return None, "Artifact path is not a file."

        return resolved_source_path.read_text(encoding="utf-8"), None

    except UnicodeDecodeError as exc:
        return None, f"UTF-8 decode failed: {exc}"

    except OSError as exc:
        return None, f"Source read failed: {exc}"


def build_reverse_dependency_map(records):
    reverse_dependencies = {}

    for record in records:
        artifact_path = record.get("artifact_path")

        if artifact_path:
            reverse_dependencies.setdefault(artifact_path, set())

    for record in records:
        referring_artifact = record.get("artifact_path")

        if not referring_artifact:
            continue

        for referenced_script in normalize_json_array(
            record.get("referenced_scripts")
        ):
            reverse_dependencies.setdefault(referenced_script, set()).add(
                referring_artifact
            )

    return {
        artifact_path: sorted(referrers)
        for artifact_path, referrers in reverse_dependencies.items()
    }


def build_summary(records, source_read_error_count):
    python_count = 0
    sql_count = 0
    complete_count = 0
    incomplete_count = 0
    missing_count = 0
    scan_error_count = 0

    for record in records:
        artifact_type = (record.get("artifact_type") or "").upper()
        documentation_status = (
            record.get("documentation_status") or ""
        ).upper()

        if artifact_type == "PYTHON":
            python_count += 1
        elif artifact_type == "SQL":
            sql_count += 1

        if documentation_status == "COMPLETE":
            complete_count += 1
        elif documentation_status == "INCOMPLETE":
            incomplete_count += 1
        elif documentation_status == "MISSING":
            missing_count += 1

        if record.get("scan_error"):
            scan_error_count += 1

    return {
        "artifacts": len(records),
        "python": python_count,
        "sql": sql_count,
        "documentation": {
            "complete": complete_count,
            "incomplete": incomplete_count,
            "missing": missing_count,
        },
        "scan_errors": scan_error_count,
        "source_read_errors": source_read_error_count,
    }


def build_audit(records):
    reverse_dependencies = build_reverse_dependency_map(records)
    artifacts = []
    source_read_error_count = 0

    for record in records:
        artifact_path = record.get("artifact_path")
        source_text, source_read_error = read_source_text(artifact_path)

        if source_read_error:
            source_read_error_count += 1

        artifacts.append(
            {
                "artifact_path": artifact_path,
                "artifact_name": record.get("artifact_name"),
                "artifact_type": record.get("artifact_type"),
                "module_docstring": record.get("module_docstring"),
                "purpose": record.get("purpose"),
                "responsibilities": normalize_json_array(
                    record.get("responsibilities")
                ),
                "verifies": normalize_json_array(record.get("verifies")),
                "exclusions": normalize_json_array(
                    record.get("exclusions")
                ),
                "classes": normalize_json_array(record.get("classes")),
                "functions": normalize_json_array(record.get("functions")),
                "imports": normalize_json_array(record.get("imports")),
                "referenced_scripts": normalize_json_array(
                    record.get("referenced_scripts")
                ),
                "referenced_by": reverse_dependencies.get(
                    artifact_path,
                    [],
                ),
                "referenced_by_count": len(
                    reverse_dependencies.get(artifact_path, [])
                ),
                "referenced_tables": normalize_json_array(
                    record.get("referenced_tables")
                ),
                "referenced_rpcs": normalize_json_array(
                    record.get("referenced_rpcs")
                ),
                "defined_rpcs": normalize_json_array(
                    record.get("defined_rpcs")
                ),
                "content_hash": record.get("content_hash"),
                "line_count": record.get("line_count"),
                "documentation_status": record.get(
                    "documentation_status"
                ),
                "scan_error": record.get("scan_error"),
                "last_scanned_at": record.get("last_scanned_at"),
                "is_active": record.get("is_active"),
                "source_read_error": source_read_error,
                "source_text": source_text,
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository_root": str(REPOSITORY_ROOT),
        "summary": build_summary(
            records,
            source_read_error_count,
        ),
        "artifacts": artifacts,
    }


def write_audit_report(audit):
    REPORT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    with REPORT_PATH.open("w", encoding="utf-8") as report_file:
        json.dump(
            audit,
            report_file,
            indent=2,
            ensure_ascii=False,
        )


def print_summary(audit):
    summary = audit["summary"]
    documentation = summary["documentation"]

    print("Export complete")
    print()
    print("Documentation Audit")
    print("-------------------")
    print(f"Artifacts: {summary['artifacts']}")
    print(f"Python: {summary['python']}")
    print(f"SQL: {summary['sql']}")
    print()
    print("Documentation")
    print("-------------")
    print(f"Complete: {documentation['complete']}")
    print(f"Incomplete: {documentation['incomplete']}")
    print(f"Missing: {documentation['missing']}")
    print(f"Scan errors: {summary['scan_errors']}")
    print(f"Source read errors: {summary['source_read_errors']}")
    print()
    print(f"Output: {REPORT_PATH}")


def main():
    print("AlphaOmega Script Documentation Audit Export")
    print(f"Repository: {REPOSITORY_ROOT}")
    print()

    client = create_database_client()
    records = load_active_scripts(client)

    audit = build_audit(records)
    write_audit_report(audit)
    print_summary(audit)


if __name__ == "__main__":
    main()