"""
AlphaOmega Script Inventory Refresh

Purpose:
    Maintains the development metadata inventory stored in the
    public.scripts table.

Responsibilities:
    - Recursively discover Python and SQL files in the AIOS repository.
    - Extract useful structural metadata without executing source code.
    - Calculate a SHA-256 hash for each artifact.
    - Insert new artifacts.
    - Update changed or previously known artifacts.
    - Mark artifacts inactive when they no longer exist in the repository.

This utility does NOT:
    - Execute discovered Python or SQL code.
    - Create Knowledge Objects.
    - Synchronize AlphaOmega content.
    - Modify source files.
    - Make architectural decisions about discovered artifacts.
"""

import ast
import hashlib
import re
from pathlib import Path

from common.security.local_credential_provider import (
    LocalCredentialProvider,
)
from scripts.database.database_connection import (
    DatabaseConnection,
)


# ============================================================================
# Configuration
# ============================================================================

TABLE_NAME = "scripts"

SUPPORTED_SUFFIXES = {
    ".py": "Python",
    ".sql": "SQL",
}

EXCLUDED_DIRECTORIES = {
    ".git",
    ".idea",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "node_modules",
    "venv",
}


# ============================================================================
# Repository Location
# ============================================================================

def get_repository_root():
    """
    Determine the AIOS repository root from this script's location.

    Expected location:
        AIOS/scripts/administration/refresh_script_inventory.py
    """

    return Path(__file__).resolve().parents[2]


# ============================================================================
# File Discovery
# ============================================================================

def discover_artifacts(repository_root):
    """
    Discover all supported Python and SQL files in the repository.
    """

    artifacts = []

    for path in repository_root.rglob("*"):

        if not path.is_file():
            continue

        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue

        relative_parts = path.relative_to(
            repository_root
        ).parts

        if any(
            part in EXCLUDED_DIRECTORIES
            for part in relative_parts
        ):
            continue

        artifacts.append(
            path
        )

    return sorted(
        artifacts,
        key=lambda value: str(value).lower(),
    )


# ============================================================================
# Shared Helpers
# ============================================================================

def calculate_hash(content_bytes):
    """
    Calculate the SHA-256 hash of an artifact.
    """

    return hashlib.sha256(
        content_bytes
    ).hexdigest()


def get_relative_path(
    repository_root,
    artifact_path,
):
    """
    Return a stable repository-relative artifact path.
    """

    return (
        artifact_path
        .relative_to(repository_root)
        .as_posix()
    )


def clean_docstring(value):
    """
    Normalize an extracted docstring.
    """

    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    return value


def extract_docstring_section(
    docstring,
    heading,
):
    """
    Extract a simple named section from a module docstring.
    """

    if not docstring:
        return []

    lines = docstring.splitlines()

    heading_lower = heading.lower()

    collecting = False
    values = []

    for raw_line in lines:

        stripped = raw_line.strip()

        if not collecting:

            if stripped.lower() == heading_lower:
                collecting = True

            continue

        if (
            stripped.endswith(":")
            and not stripped.startswith("-")
        ):
            break

        if not stripped:
            continue

        if stripped.startswith("-"):
            stripped = stripped[1:].strip()

        values.append(
            stripped
        )

    return values


def extract_purpose(docstring):
    """
    Extract the Purpose section from a module docstring.

    Falls back to the first meaningful docstring line.
    """

    if not docstring:
        return None

    purpose_lines = (
        extract_docstring_section(
            docstring,
            "Purpose:",
        )
    )

    if purpose_lines:
        return " ".join(
            purpose_lines
        )

    lines = [
        line.strip()
        for line in docstring.splitlines()
        if line.strip()
    ]

    if not lines:
        return None

    return lines[0]


# ============================================================================
# Python Analysis
# ============================================================================

def analyze_python(
    artifact_path,
    content_text,
):
    """
    Extract structural metadata from a Python artifact using AST.

    Source code is parsed but never executed.
    """

    try:

        tree = ast.parse(
            content_text,
            filename=str(
                artifact_path
            ),
        )

    except SyntaxError as error:

        raise RuntimeError(
            "Python syntax could not be parsed for "
            f"'{artifact_path}'."
        ) from error

    module_docstring = clean_docstring(
        ast.get_docstring(
            tree,
            clean=True,
        )
    )

    classes = []
    functions = []
    imports = []
    referenced_rpcs = []

    for node in ast.walk(
        tree
    ):

        # ====================================================================
        # Classes
        # ====================================================================

        if isinstance(
            node,
            ast.ClassDef,
        ):

            classes.append(
                node.name
            )

        # ====================================================================
        # Functions and Methods
        # ====================================================================

        elif isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            functions.append(
                node.name
            )

        # ====================================================================
        # Imports
        # ====================================================================

        elif isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:

                imports.append(
                    alias.name
                )

        elif isinstance(
            node,
            ast.ImportFrom,
        ):

            module_name = (
                node.module
                or ""
            )

            for alias in node.names:

                if module_name:

                    imports.append(
                        f"{module_name}.{alias.name}"
                    )

                else:

                    imports.append(
                        alias.name
                    )

        # ====================================================================
        # Direct Supabase RPC Calls
        # ====================================================================

        elif isinstance(
            node,
            ast.Call,
        ):

            function = node.func

            if (
                isinstance(
                    function,
                    ast.Attribute,
                )
                and function.attr == "rpc"
                and node.args
            ):

                first_argument = (
                    node.args[0]
                )

                if (
                    isinstance(
                        first_argument,
                        ast.Constant,
                    )
                    and isinstance(
                        first_argument.value,
                        str,
                    )
                ):

                    referenced_rpcs.append(
                        first_argument.value
                    )

    # ========================================================================
    # RPC_NAME Constants
    # ========================================================================

    for node in ast.walk(
        tree
    ):

        if isinstance(
            node,
            ast.Assign,
        ):

            targets = (
                node.targets
            )

            value = (
                node.value
            )

        elif isinstance(
            node,
            ast.AnnAssign,
        ):

            targets = [
                node.target
            ]

            value = (
                node.value
            )

        else:

            continue

        for target in targets:

            if (
                isinstance(
                    target,
                    ast.Name,
                )
                and target.id == "RPC_NAME"
                and isinstance(
                    value,
                    ast.Constant,
                )
                and isinstance(
                    value.value,
                    str,
                )
            ):

                referenced_rpcs.append(
                    value.value
                )

    responsibilities = (
        extract_docstring_section(
            module_docstring,
            "Responsibilities:",
        )
    )

    exclusions = []

    for heading in (
        "This module does NOT:",
        "This repository does not:",
        "This utility does NOT:",
    ):

        exclusions.extend(
            extract_docstring_section(
                module_docstring,
                heading,
            )
        )

    return {
        "purpose":
            extract_purpose(
                module_docstring
            ),

        "responsibilities":
            sorted(
                set(
                    responsibilities
                )
            ),

        "exclusions":
            sorted(
                set(
                    exclusions
                )
            ),

        "classes":
            sorted(
                set(
                    classes
                )
            ),

        "functions":
            sorted(
                set(
                    functions
                )
            ),

        "imports":
            sorted(
                set(
                    imports
                )
            ),

        "sql_functions":
            [],

        "referenced_tables":
            [],

        "referenced_rpcs":
            sorted(
                set(
                    referenced_rpcs
                )
            ),
    }


# ============================================================================
# SQL Analysis
# ============================================================================

def analyze_sql(content_text):
    """
    Extract conservative structural metadata from a SQL artifact.

    This intentionally does not attempt to be a complete SQL parser.
    """

    sql_functions = set()
    referenced_tables = set()

    # ========================================================================
    # SQL Function Definitions
    # ========================================================================

    function_pattern = re.compile(
        r"""
        \bCREATE
        \s+(?:OR\s+REPLACE\s+)?
        FUNCTION
        \s+
        (?:(?:public)\.)?
        ([A-Za-z_][A-Za-z0-9_]*)
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    for match in function_pattern.finditer(
        content_text
    ):

        sql_functions.add(
            match.group(1)
        )

    # ========================================================================
    # Referenced Tables
    # ========================================================================

    table_pattern = re.compile(
        r"""
        \b
        (?:
            FROM
            |
            JOIN
            |
            INSERT\s+INTO
            |
            UPDATE
            |
            DELETE\s+FROM
        )
        \s+
        (?:(?:public)\.)?
        ([A-Za-z_][A-Za-z0-9_]*)
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    for match in table_pattern.finditer(
        content_text
    ):

        referenced_tables.add(
            match.group(1)
        )

    # ========================================================================
    # Leading SQL Comments
    # ========================================================================

    purpose = None
    comment_lines = []

    for line in content_text.splitlines():

        stripped = line.strip()

        if stripped.startswith(
            "--"
        ):

            comment_text = (
                stripped[2:]
                .strip()
            )

            if comment_text:

                comment_lines.append(
                    comment_text
                )

        elif stripped:

            break

    if comment_lines:

        purpose = " ".join(
            comment_lines
        )

    return {
        "purpose":
            purpose,

        "responsibilities":
            [],

        "exclusions":
            [],

        "classes":
            [],

        "functions":
            [],

        "imports":
            [],

        "sql_functions":
            sorted(
                sql_functions
            ),

        "referenced_tables":
            sorted(
                referenced_tables
            ),

        "referenced_rpcs":
            [],
    }


# ============================================================================
# Artifact Analysis
# ============================================================================

def analyze_artifact(
    repository_root,
    artifact_path,
):
    """
    Build one scripts-table record from one repository artifact.
    """

    content_bytes = (
        artifact_path
        .read_bytes()
    )

    try:

        content_text = (
            content_bytes
            .decode(
                "utf-8"
            )
        )

    except UnicodeDecodeError:

        content_text = (
            content_bytes
            .decode(
                "utf-8-sig"
            )
        )

    suffix = (
        artifact_path
        .suffix
        .lower()
    )

    if suffix == ".py":

        analysis = analyze_python(
            artifact_path,
            content_text,
        )

    elif suffix == ".sql":

        analysis = analyze_sql(
            content_text
        )

    else:

        raise ValueError(
            "Unsupported artifact type: "
            f"'{artifact_path}'."
        )

    return {
        "artifact_path":
            get_relative_path(
                repository_root,
                artifact_path,
            ),

        "artifact_name":
            artifact_path.name,

        "artifact_type":
            SUPPORTED_SUFFIXES[
                suffix
            ],

        "purpose":
            analysis[
                "purpose"
            ],

        "responsibilities":
            analysis[
                "responsibilities"
            ],

        "exclusions":
            analysis[
                "exclusions"
            ],

        "classes":
            analysis[
                "classes"
            ],

        "functions":
            analysis[
                "functions"
            ],

        "imports":
            analysis[
                "imports"
            ],

        "sql_functions":
            analysis[
                "sql_functions"
            ],

        "referenced_tables":
            analysis[
                "referenced_tables"
            ],

        "referenced_rpcs":
            analysis[
                "referenced_rpcs"
            ],

        "content_hash":
            calculate_hash(
                content_bytes
            ),

        "is_active":
            True,
    }


# ============================================================================
# Database Operations
# ============================================================================

def load_existing_records(
    client,
):
    """
    Load the current scripts inventory.
    """

    response = (
        client
        .table(
            TABLE_NAME
        )
        .select(
            "artifact_path,"
            "content_hash,"
            "is_active"
        )
        .execute()
    )

    return {
        row[
            "artifact_path"
        ]: row
        for row in (
            response.data
            or []
        )
    }


def upsert_artifact(
    client,
    record,
):
    """
    Insert or update one scripts inventory record.
    """

    (
        client
        .table(
            TABLE_NAME
        )
        .upsert(
            record,
            on_conflict="artifact_path",
        )
        .execute()
    )


def deactivate_missing_artifact(
    client,
    artifact_path,
):
    """
    Mark a previously known artifact inactive.
    """

    (
        client
        .table(
            TABLE_NAME
        )
        .update(
            {
                "is_active":
                    False,
            }
        )
        .eq(
            "artifact_path",
            artifact_path,
        )
        .execute()
    )


# ============================================================================
# Inventory Refresh
# ============================================================================

def refresh_inventory(
    client,
    repository_root,
):
    """
    Refresh the complete development script inventory.
    """

    discovered_paths = (
        discover_artifacts(
            repository_root
        )
    )

    existing_records = (
        load_existing_records(
            client
        )
    )

    observed_artifact_paths = set()

    new_count = 0
    changed_count = 0
    unchanged_count = 0
    reactivated_count = 0
    deactivated_count = 0

    for artifact_path in (
        discovered_paths
    ):

        record = analyze_artifact(
            repository_root,
            artifact_path,
        )

        artifact_relative_path = (
            record[
                "artifact_path"
            ]
        )

        observed_artifact_paths.add(
            artifact_relative_path
        )

        existing = (
            existing_records.get(
                artifact_relative_path
            )
        )

        # ====================================================================
        # New
        # ====================================================================

        if existing is None:

            upsert_artifact(
                client,
                record,
            )

            new_count += 1

            continue

        # ====================================================================
        # Reactivated
        # ====================================================================

        if not existing.get(
            "is_active",
            True,
        ):

            upsert_artifact(
                client,
                record,
            )

            reactivated_count += 1

            continue

        # ====================================================================
        # Changed
        # ====================================================================

        if (
            existing.get(
                "content_hash"
            )
            != record[
                "content_hash"
            ]
        ):

            upsert_artifact(
                client,
                record,
            )

            changed_count += 1

            continue

        # ====================================================================
        # Unchanged
        # ====================================================================

        unchanged_count += 1

    # ========================================================================
    # Missing / Inactive
    # ========================================================================

    for (
        artifact_path,
        existing,
    ) in existing_records.items():

        if (
            artifact_path
            in observed_artifact_paths
        ):
            continue

        if not existing.get(
            "is_active",
            True,
        ):
            continue

        deactivate_missing_artifact(
            client,
            artifact_path,
        )

        deactivated_count += 1

    return {
        "observed":
            len(
                discovered_paths
            ),

        "new":
            new_count,

        "changed":
            changed_count,

        "unchanged":
            unchanged_count,

        "reactivated":
            reactivated_count,

        "deactivated":
            deactivated_count,
    }


# ============================================================================
# Main
# ============================================================================

def main():
    """
    Execute the development script inventory refresh.
    """

    repository_root = (
        get_repository_root()
    )

    print(
        "AlphaOmega Script Inventory Refresh"
    )

    print(
        "Repository:",
        repository_root,
    )

    credential_provider = (
        LocalCredentialProvider()
    )

    database_connection = (
        DatabaseConnection(
            credential_provider
        )
    )

    client = (
        database_connection
        .connect()
    )

    result = refresh_inventory(
        client=client,
        repository_root=repository_root,
    )

    print()
    print(
        "Refresh complete"
    )

    print(
        "Observed:",
        result[
            "observed"
        ],
    )

    print(
        "New:",
        result[
            "new"
        ],
    )

    print(
        "Changed:",
        result[
            "changed"
        ],
    )

    print(
        "Unchanged:",
        result[
            "unchanged"
        ],
    )

    print(
        "Reactivated:",
        result[
            "reactivated"
        ],
    )

    print(
        "Deactivated:",
        result[
            "deactivated"
        ],
    )


if __name__ == "__main__":
    main()