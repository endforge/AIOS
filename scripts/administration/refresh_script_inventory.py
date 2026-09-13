"""
AlphaOmega Script Inventory Refresh

Purpose:
    Maintains the development implementation inventory stored in the
    public.scripts table.

Responsibilities:
    - Discover Python and SQL artifacts in the AIOS repository.
    - Extract human-authored documentation metadata.
    - Extract deterministic implementation metadata.
    - Resolve internal Python dependencies to repository artifacts.
    - Detect database table and RPC relationships.
    - Measure documentation compliance.
    - Maintain active and inactive artifact state.

Does NOT:
    - Execute discovered Python or SQL artifacts.
    - Modify discovered source files.
    - Create Knowledge Objects.
    - Synchronize AlphaOmega content.
    - Infer architectural intent that is not documented in source.
    - Determine inbound dependencies manually.
"""

import ast
import hashlib
import re
from datetime import datetime, timezone
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

DOCUMENTATION_HEADINGS = {
    "purpose:": "purpose",
    "responsibilities:": "responsibilities",
    "verifies:": "verifies",
    "does not:": "exclusions",
    "this module does not:": "exclusions",
    "this repository does not:": "exclusions",
    "this utility does not:": "exclusions",
    "this script does not:": "exclusions",
    "this test does not:": "exclusions",
}

UPSERT_BATCH_SIZE = 100


# ============================================================================
# Repository Location
# ============================================================================

def get_repository_root():
    """
    Determine the AIOS repository root from this script's location.
    """

    return Path(__file__).resolve().parents[2]


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
    Return a stable repository-relative path.
    """

    return (
        artifact_path
        .relative_to(repository_root)
        .as_posix()
    )


def get_line_count(content_text):
    """
    Return the number of physical lines in an artifact.
    """

    if not content_text:
        return 0

    return len(
        content_text.splitlines()
    )


def is_test_artifact(
    artifact_relative_path,
):
    """
    Determine whether an artifact represents test code.
    """

    normalized = (
        artifact_relative_path
        .replace("\\", "/")
        .lower()
    )

    artifact_name = (
        Path(normalized)
        .name
    )

    return (
        "/code_testing/" in f"/{normalized}"
        or artifact_name.startswith("test_")
    )


# ============================================================================
# File Discovery
# ============================================================================

def discover_artifacts(
    repository_root,
):
    """
    Discover all supported Python and SQL files.
    """

    artifacts = []

    for path in repository_root.rglob("*"):

        if not path.is_file():
            continue

        suffix = (
            path.suffix.lower()
        )

        if suffix not in SUPPORTED_SUFFIXES:
            continue

        relative_parts = (
            path
            .relative_to(repository_root)
            .parts
        )

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
# Documentation Parsing
# ============================================================================

def normalize_documentation_line(
    line,
):
    """
    Normalize one documentation line.
    """

    stripped = line.strip()

    if stripped.startswith("-"):
        stripped = stripped[1:].strip()

    return stripped


def parse_documentation(
    documentation,
):
    """
    Parse the AlphaOmega documentation header.

    Recognizes both the new Gold Standard headings and older exclusion
    heading variations for backward compatibility.
    """

    result = {
        "title": None,
        "purpose": None,
        "responsibilities": [],
        "verifies": [],
        "exclusions": [],
    }

    if not documentation:
        return result

    title_lines = []

    sections = {
        "purpose": [],
        "responsibilities": [],
        "verifies": [],
        "exclusions": [],
    }

    current_section = None

    for raw_line in documentation.splitlines():

        stripped = raw_line.strip()

        if not stripped:
            continue

        heading_key = (
            stripped
            .lower()
        )

        mapped_section = (
            DOCUMENTATION_HEADINGS.get(
                heading_key
            )
        )

        if mapped_section:

            current_section = mapped_section
            continue

        normalized = (
            normalize_documentation_line(
                stripped
            )
        )

        if not normalized:
            continue

        if current_section is None:

            title_lines.append(
                normalized
            )

            continue

        sections[
            current_section
        ].append(
            normalized
        )

    if title_lines:

        result["title"] = (
            title_lines[0]
        )

    if sections["purpose"]:

        result["purpose"] = " ".join(
            sections["purpose"]
        )

    result["responsibilities"] = (
        sections["responsibilities"]
    )

    result["verifies"] = (
        sections["verifies"]
    )

    result["exclusions"] = (
        sections["exclusions"]
    )

    return result


def determine_documentation_status(
    documentation,
    parsed_documentation,
    artifact_relative_path,
):
    """
    Measure compliance with the AlphaOmega source documentation standard.

    COMPLETE:
        Title, Purpose, correct ownership/test section, and Does NOT exist.

    INCOMPLETE:
        Documentation exists but one or more required sections are missing.

    MISSING:
        No documentation header exists.
    """

    if not documentation:
        return "MISSING"

    has_title = bool(
        parsed_documentation[
            "title"
        ]
    )

    has_purpose = bool(
        parsed_documentation[
            "purpose"
        ]
    )

    has_exclusions = bool(
        parsed_documentation[
            "exclusions"
        ]
    )

    if is_test_artifact(
        artifact_relative_path
    ):

        has_primary_section = bool(
            parsed_documentation[
                "verifies"
            ]
        )

    else:

        has_primary_section = bool(
            parsed_documentation[
                "responsibilities"
            ]
        )

    if (
        has_title
        and has_purpose
        and has_primary_section
        and has_exclusions
    ):
        return "COMPLETE"

    return "INCOMPLETE"


# ============================================================================
# SQL Documentation
# ============================================================================

def extract_sql_documentation(
    content_text,
):
    """
    Extract the leading SQL comment documentation block.

    Only leading '--' comments are considered documentation.
    """

    documentation_lines = []
    documentation_started = False

    for raw_line in content_text.splitlines():

        stripped = raw_line.strip()

        if stripped.startswith("--"):

            documentation_started = True

            documentation_lines.append(
                stripped[2:].strip()
            )

            continue

        if not stripped:

            if documentation_started:

                documentation_lines.append(
                    ""
                )

            continue

        break

    documentation = "\n".join(
        documentation_lines
    ).strip()

    if not documentation:
        return None

    return documentation


# ============================================================================
# Python Constants
# ============================================================================

def collect_python_string_constants(
    tree,
):
    """
    Collect simple statically declared string constants.

    This allows relationships such as:

        TABLE_NAME = "scripts"
        client.table(TABLE_NAME)

    to be resolved without executing source code.
    """

    constants = {}

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Assign,
        ):

            value = node.value
            targets = node.targets

        elif isinstance(
            node,
            ast.AnnAssign,
        ):

            value = node.value
            targets = [
                node.target
            ]

        else:
            continue

        if not (
            isinstance(
                value,
                ast.Constant,
            )
            and isinstance(
                value.value,
                str,
            )
        ):
            continue

        for target in targets:

            if isinstance(
                target,
                ast.Name,
            ):

                constants[
                    target.id
                ] = value.value

            elif isinstance(
                target,
                ast.Attribute,
            ):

                constants[
                    target.attr
                ] = value.value

    return constants


def resolve_static_string(
    node,
    constants,
):
    """
    Resolve a simple AST expression to a static string.

    Supported forms:
        "sources"
        TABLE_NAME
        self.TABLE_NAME
        ClassName.TABLE_NAME
    """

    if (
        isinstance(
            node,
            ast.Constant,
        )
        and isinstance(
            node.value,
            str,
        )
    ):

        return node.value

    if isinstance(
        node,
        ast.Name,
    ):

        return constants.get(
            node.id
        )

    if isinstance(
        node,
        ast.Attribute,
    ):

        return constants.get(
            node.attr
        )

    return None


# ============================================================================
# Python Import Analysis
# ============================================================================

def path_to_module_name(
    repository_root,
    artifact_path,
):
    """
    Convert a Python artifact path into its importable module name.
    """

    relative_path = (
        artifact_path
        .relative_to(repository_root)
    )

    without_suffix = (
        relative_path
        .with_suffix("")
    )

    parts = list(
        without_suffix.parts
    )

    if (
        parts
        and parts[-1] == "__init__"
    ):

        parts = parts[:-1]

    return ".".join(
        parts
    )


def build_python_module_map(
    repository_root,
    discovered_paths,
):
    """
    Map importable Python module names to repository-relative files.
    """

    module_map = {}

    for artifact_path in discovered_paths:

        if (
            artifact_path
            .suffix
            .lower()
            != ".py"
        ):
            continue

        module_name = (
            path_to_module_name(
                repository_root,
                artifact_path,
            )
        )

        if not module_name:
            continue

        module_map[
            module_name
        ] = get_relative_path(
            repository_root,
            artifact_path,
        )

    return module_map


def resolve_relative_import_module(
    current_module,
    imported_module,
    level,
):
    """
    Resolve a Python relative import into an absolute module name.
    """

    if level == 0:
        return imported_module or ""

    current_parts = (
        current_module
        .split(".")
    )

    if current_parts:

        current_parts = (
            current_parts[:-1]
        )

    remove_count = (
        level - 1
    )

    if remove_count > 0:

        if remove_count <= len(
            current_parts
        ):

            current_parts = (
                current_parts[
                    :-remove_count
                ]
            )

        else:

            current_parts = []

    if imported_module:

        current_parts.extend(
            imported_module.split(".")
        )

    return ".".join(
        current_parts
    )


def find_best_module_match(
    candidate_module,
    module_map,
):
    """
    Resolve an imported module or sub-object to the closest repository module.
    """

    candidate = (
        candidate_module
        .strip(".")
    )

    while candidate:

        if candidate in module_map:

            return module_map[
                candidate
            ]

        if "." not in candidate:
            break

        candidate = (
            candidate
            .rsplit(
                ".",
                1,
            )[0]
        )

    return None


# ============================================================================
# Python Analysis
# ============================================================================

def analyze_python(
    repository_root,
    artifact_path,
    artifact_relative_path,
    content_text,
    module_map,
):
    """
    Extract deterministic metadata from a Python artifact.
    """

    tree = ast.parse(
        content_text,
        filename=str(
            artifact_path
        ),
    )

    module_docstring = (
        ast.get_docstring(
            tree,
            clean=True,
        )
    )

    parsed_documentation = (
        parse_documentation(
            module_docstring
        )
    )

    constants = (
        collect_python_string_constants(
            tree
        )
    )

    classes = set()
    functions = set()
    imports = set()
    import_modules = set()
    referenced_tables = set()
    referenced_rpcs = set()

    current_module = (
        path_to_module_name(
            repository_root,
            artifact_path,
        )
    )

    for node in ast.walk(tree):

        # ====================================================================
        # Classes
        # ====================================================================

        if isinstance(
            node,
            ast.ClassDef,
        ):

            classes.add(
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

            functions.add(
                node.name
            )

        # ====================================================================
        # import package.module
        # ====================================================================

        elif isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:

                imports.add(
                    alias.name
                )

                import_modules.add(
                    alias.name
                )

        # ====================================================================
        # from package.module import Object
        # ====================================================================

        elif isinstance(
            node,
            ast.ImportFrom,
        ):

            base_module = (
                resolve_relative_import_module(
                    current_module=current_module,
                    imported_module=node.module,
                    level=node.level,
                )
            )

            for alias in node.names:

                if base_module:

                    imports.add(
                        f"{base_module}.{alias.name}"
                    )

                    import_modules.add(
                        base_module
                    )

                    possible_submodule = (
                        f"{base_module}.{alias.name}"
                    )

                    if (
                        possible_submodule
                        in module_map
                    ):

                        import_modules.add(
                            possible_submodule
                        )

                else:

                    imports.add(
                        alias.name
                    )

        # ====================================================================
        # Database Table Calls
        # ====================================================================

        elif isinstance(
            node,
            ast.Call,
        ):

            function = node.func

            if not isinstance(
                function,
                ast.Attribute,
            ):
                continue

            # ----------------------------------------------------------------
            # Supabase/PostgREST table access
            # ----------------------------------------------------------------

            if (
                function.attr
                in {
                    "table",
                    "from_",
                }
                and node.args
            ):

                table_name = (
                    resolve_static_string(
                        node.args[0],
                        constants,
                    )
                )

                if table_name:

                    referenced_tables.add(
                        table_name
                    )

            # ----------------------------------------------------------------
            # Supabase RPC access
            # ----------------------------------------------------------------

            if (
                function.attr == "rpc"
                and node.args
            ):

                rpc_name = (
                    resolve_static_string(
                        node.args[0],
                        constants,
                    )
                )

                if rpc_name:

                    referenced_rpcs.add(
                        rpc_name
                    )

    referenced_scripts = set()

    for imported_module in (
        import_modules
    ):

        referenced_script = (
            find_best_module_match(
                imported_module,
                module_map,
            )
        )

        if not referenced_script:
            continue

        if (
            referenced_script
            == artifact_relative_path
        ):
            continue

        referenced_scripts.add(
            referenced_script
        )

    documentation_status = (
        determine_documentation_status(
            documentation=module_docstring,
            parsed_documentation=parsed_documentation,
            artifact_relative_path=artifact_relative_path,
        )
    )

    return {
        "module_docstring":
            module_docstring,

        "purpose":
            parsed_documentation[
                "purpose"
            ],

        "responsibilities":
            sorted(
                set(
                    parsed_documentation[
                        "responsibilities"
                    ]
                )
            ),

        "verifies":
            sorted(
                set(
                    parsed_documentation[
                        "verifies"
                    ]
                )
            ),

        "exclusions":
            sorted(
                set(
                    parsed_documentation[
                        "exclusions"
                    ]
                )
            ),

        "classes":
            sorted(
                classes
            ),

        "functions":
            sorted(
                functions
            ),

        "imports":
            sorted(
                imports
            ),

        "referenced_scripts":
            sorted(
                referenced_scripts
            ),

    
        "referenced_tables":
            sorted(
                referenced_tables
            ),

        "referenced_rpcs":
            sorted(
                referenced_rpcs
            ),

        "defined_rpcs":
            [],

        "documentation_status":
            documentation_status,
    }


# ============================================================================
# SQL Analysis
# ============================================================================

def strip_sql_comments(
    content_text,
):
    """
    Remove SQL comments for relationship detection.
    """

    without_block_comments = re.sub(
        r"/\*.*?\*/",
        " ",
        content_text,
        flags=re.DOTALL,
    )

    without_line_comments = re.sub(
        r"--.*?$",
        " ",
        without_block_comments,
        flags=re.MULTILINE,
    )

    return without_line_comments


def find_sql_defined_rpcs(
    content_text,
):
    """
    Detect SQL function definitions.
    """

    pattern = re.compile(
        r"""
        \bCREATE
        \s+
        (?:OR\s+REPLACE\s+)?
        FUNCTION
        \s+
        (?:(?:public)\.)?
        ([A-Za-z_][A-Za-z0-9_]*)
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    return sorted(
        {
            match.group(1)
            for match in pattern.finditer(
                content_text
            )
        }
    )


def find_sql_referenced_tables(
    content_text,
):
    """
    Detect tables directly touched or defined by SQL.
    """

    cleaned_sql = (
        strip_sql_comments(
            content_text
        )
    )

    pattern = re.compile(
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
            |
            ALTER\s+TABLE
            |
            CREATE\s+TABLE
            |
            DROP\s+TABLE
            |
            TRUNCATE(?:\s+TABLE)?
        )
        \s+
        (?:IF\s+(?:NOT\s+)?EXISTS\s+)?
        (?:(?:public)\.)?
        ([A-Za-z_][A-Za-z0-9_]*)
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    return sorted(
        {
            match.group(1)
            for match in pattern.finditer(
                cleaned_sql
            )
        }
    )


def analyze_sql(
    artifact_relative_path,
    content_text,
):
    """
    Extract deterministic metadata from a SQL artifact.
    """

    documentation = (
        extract_sql_documentation(
            content_text
        )
    )

    parsed_documentation = (
        parse_documentation(
            documentation
        )
    )

    defined_rpcs = (
        find_sql_defined_rpcs(
            content_text
        )
    )

    referenced_tables = (
        find_sql_referenced_tables(
            content_text
        )
    )

    documentation_status = (
        determine_documentation_status(
            documentation=documentation,
            parsed_documentation=parsed_documentation,
            artifact_relative_path=artifact_relative_path,
        )
    )

    return {
        # The column is named module_docstring because Python is the primary
        # implementation language. For SQL it stores the equivalent leading
        # documentation header so the full human-authored contract is still
        # available from one inventory field.
        "module_docstring":
            documentation,

        "purpose":
            parsed_documentation[
                "purpose"
            ],

        "responsibilities":
            sorted(
                set(
                    parsed_documentation[
                        "responsibilities"
                    ]
                )
            ),

        "verifies":
            sorted(
                set(
                    parsed_documentation[
                        "verifies"
                    ]
                )
            ),

        "exclusions":
            sorted(
                set(
                    parsed_documentation[
                        "exclusions"
                    ]
                )
            ),

        "classes":
            [],

        "functions":
            [],

        "imports":
            [],

        "referenced_scripts":
            [],

        "referenced_tables":
            referenced_tables,

        "referenced_rpcs":
            [],

        "defined_rpcs":
            defined_rpcs,

        "documentation_status":
            documentation_status,
    }


def find_sql_referenced_rpcs(
    content_text,
    known_rpcs,
    defined_rpcs,
):
    """
    Detect calls from SQL to RPC/functions defined elsewhere in the repository.

    Only known AlphaOmega SQL functions are considered. This avoids treating
    normal PostgreSQL built-in functions as repository dependencies.
    """

    cleaned_sql = (
        strip_sql_comments(
            content_text
        )
    )

    own_definitions = set(
        defined_rpcs
    )

    referenced = set()

    for rpc_name in known_rpcs:

        if rpc_name in own_definitions:
            continue

        pattern = re.compile(
            rf"""
            \b
            (?:public\.)?
            {re.escape(rpc_name)}
            \s*
            \(
            """,
            re.IGNORECASE | re.VERBOSE,
        )

        if pattern.search(
            cleaned_sql
        ):

            referenced.add(
                rpc_name
            )

    return sorted(
        referenced
    )


# ============================================================================
# Artifact Analysis
# ============================================================================

def build_base_record(
    repository_root,
    artifact_path,
    content_bytes,
    content_text,
    scanned_at,
):
    """
    Build metadata available regardless of parser success.
    """

    suffix = (
        artifact_path
        .suffix
        .lower()
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
            None,

        "responsibilities":
            [],

        "verifies":
            [],

        "exclusions":
            [],

        "classes":
            [],

        "functions":
            [],

        "imports":
            [],

        "referenced_scripts":
            [],

        "referenced_tables":
            [],

        "referenced_rpcs":
            [],

        "defined_rpcs":
            [],

        "module_docstring":
            None,

        "content_hash":
            calculate_hash(
                content_bytes
            ),

        "line_count":
            get_line_count(
                content_text
            ),

        "scan_error":
            None,

        "documentation_status":
            "MISSING",

        "last_scanned_at":
            scanned_at,

        "is_active":
            True,
    }


def analyze_artifact(
    repository_root,
    artifact_path,
    module_map,
    scanned_at,
):
    """
    Analyze one artifact without allowing parser failures to stop the scan.
    """

    content_bytes = (
        artifact_path
        .read_bytes()
    )

    decoding_error = None

    try:

        content_text = (
            content_bytes
            .decode(
                "utf-8-sig"
            )
        )

    except UnicodeDecodeError as error:

        decoding_error = (
            f"{type(error).__name__}: {error}"
        )

        content_text = (
            content_bytes
            .decode(
                "utf-8",
                errors="replace",
            )
        )

    record = (
        build_base_record(
            repository_root=repository_root,
            artifact_path=artifact_path,
            content_bytes=content_bytes,
            content_text=content_text,
            scanned_at=scanned_at,
        )
    )

    artifact_relative_path = (
        record[
            "artifact_path"
        ]
    )

    suffix = (
        artifact_path
        .suffix
        .lower()
    )

    try:

        if suffix == ".py":

            analysis = (
                analyze_python(
                    repository_root=repository_root,
                    artifact_path=artifact_path,
                    artifact_relative_path=artifact_relative_path,
                    content_text=content_text,
                    module_map=module_map,
                )
            )

        elif suffix == ".sql":

            analysis = (
                analyze_sql(
                    artifact_relative_path=artifact_relative_path,
                    content_text=content_text,
                )
            )

        else:

            raise ValueError(
                "Unsupported artifact type: "
                f"{artifact_path}"
            )

        record.update(
            analysis
        )

    except Exception as error:

        record[
            "scan_error"
        ] = (
            f"{type(error).__name__}: {error}"
        )

    if decoding_error:

        if record[
            "scan_error"
        ]:

            record[
                "scan_error"
            ] = (
                f"{decoding_error}; "
                f"{record['scan_error']}"
            )

        else:

            record[
                "scan_error"
            ] = decoding_error

    # Transient content used during second-pass SQL dependency resolution.
    # It is removed before persistence.
    record[
        "_content_text"
    ] = content_text

    return record


# ============================================================================
# Second-Pass Relationship Analysis
# ============================================================================

def enrich_sql_rpc_relationships(
    records,
):
    """
    Resolve SQL-to-SQL RPC relationships after all function definitions
    have been discovered.
    """

    known_rpcs = set()

    for record in records:

        known_rpcs.update(
            record[
                "defined_rpcs"
            ]
        )

    for record in records:

        if (
            record[
                "artifact_type"
            ]
            != "SQL"
        ):
            continue

        if record[
            "scan_error"
        ]:
            continue

        content_text = (
            record[
                "_content_text"
            ]
        )

        record[
            "referenced_rpcs"
        ] = (
            find_sql_referenced_rpcs(
                content_text=content_text,
                known_rpcs=known_rpcs,
                defined_rpcs=record[
                    "defined_rpcs"
                ],
            )
        )


def remove_transient_fields(
    records,
):
    """
    Remove analysis-only fields before database persistence.
    """

    for record in records:

        record.pop(
            "_content_text",
            None,
        )


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


def upsert_records(
    client,
    records,
):
    """
    Upsert inventory records in controlled batches.

    All observed artifacts are refreshed, even if their source hash has not
    changed, because scanner-derived metadata can improve independently of
    source-code changes.
    """

    for start_index in range(
        0,
        len(records),
        UPSERT_BATCH_SIZE,
    ):

        batch = records[
            start_index:
            start_index + UPSERT_BATCH_SIZE
        ]

        (
            client
            .table(
                TABLE_NAME
            )
            .upsert(
                batch,
                on_conflict="artifact_path",
            )
            .execute()
        )


def deactivate_missing_artifact(
    client,
    artifact_path,
    scanned_at,
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

                "last_scanned_at":
                    scanned_at,
            }
        )
        .eq(
            "artifact_path",
            artifact_path,
        )
        .execute()
    )


# ============================================================================
# Inventory Classification
# ============================================================================

def classify_record(
    record,
    existing,
):
    """
    Classify one observed artifact relative to the previous inventory.
    """

    if existing is None:
        return "new"

    if not existing.get(
        "is_active",
        True,
    ):
        return "reactivated"

    if (
        existing.get(
            "content_hash"
        )
        != record[
            "content_hash"
        ]
    ):
        return "changed"

    return "unchanged"


# ============================================================================
# Inventory Refresh
# ============================================================================

def refresh_inventory(
    client,
    repository_root,
):
    """
    Refresh the complete AlphaOmega development implementation inventory.
    """

    scanned_at = (
        datetime.now(
            timezone.utc
        )
        .isoformat()
    )

    discovered_paths = (
        discover_artifacts(
            repository_root
        )
    )

    # Discovery completed successfully before any deactivation decisions.
    # This prevents a partial traversal from falsely marking artifacts absent.

    module_map = (
        build_python_module_map(
            repository_root,
            discovered_paths,
        )
    )

    existing_records = (
        load_existing_records(
            client
        )
    )

    records = []

    counts = {
        "observed": 0,
        "new": 0,
        "changed": 0,
        "unchanged": 0,
        "reactivated": 0,
        "deactivated": 0,
        "scan_errors": 0,
        "documentation_complete": 0,
        "documentation_incomplete": 0,
        "documentation_missing": 0,
    }

    observed_artifact_paths = set()

    for artifact_path in (
        discovered_paths
    ):

        record = (
            analyze_artifact(
                repository_root=repository_root,
                artifact_path=artifact_path,
                module_map=module_map,
                scanned_at=scanned_at,
            )
        )

        records.append(
            record
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

        classification = (
            classify_record(
                record,
                existing,
            )
        )

        counts[
            classification
        ] += 1

    # Second pass requires a complete view of discovered SQL definitions.

    enrich_sql_rpc_relationships(
        records
    )

    remove_transient_fields(
        records
    )

    # Documentation and parser statistics are calculated after enrichment.

    for record in records:

        counts[
            "observed"
        ] += 1

        if record[
            "scan_error"
        ]:

            counts[
                "scan_errors"
            ] += 1

        documentation_status = (
            record[
                "documentation_status"
            ]
        )

        if documentation_status == "COMPLETE":

            counts[
                "documentation_complete"
            ] += 1

        elif documentation_status == "INCOMPLETE":

            counts[
                "documentation_incomplete"
            ] += 1

        else:

            counts[
                "documentation_missing"
            ] += 1

    # Persist all current observations.

    upsert_records(
        client,
        records,
    )

    # Deactivate only after complete filesystem discovery and successful
    # current-record persistence.

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
            client=client,
            artifact_path=artifact_path,
            scanned_at=scanned_at,
        )

        counts[
            "deactivated"
        ] += 1

    return counts


# ============================================================================
# Console Output
# ============================================================================

def print_results(
    result,
):
    """
    Print the inventory refresh result.
    """

    print()
    print(
        "Refresh complete"
    )

    print()
    print(
        "Repository Inventory"
    )
    print(
        "--------------------"
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

    print()
    print(
        "Documentation"
    )
    print(
        "-------------"
    )

    print(
        "Complete:",
        result[
            "documentation_complete"
        ],
    )

    print(
        "Incomplete:",
        result[
            "documentation_incomplete"
        ],
    )

    print(
        "Missing:",
        result[
            "documentation_missing"
        ],
    )

    print()
    print(
        "Analysis"
    )
    print(
        "--------"
    )

    print(
        "Scan errors:",
        result[
            "scan_errors"
        ],
    )


# ============================================================================
# Main
# ============================================================================

def main():
    """
    Execute the AlphaOmega development implementation inventory refresh.
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

    result = (
        refresh_inventory(
            client=client,
            repository_root=repository_root,
        )
    )

    print_results(
        result
    )


if __name__ == "__main__":
    main()