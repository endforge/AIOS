"""
Live OneDrive End-to-End Synchronization Test

Purpose:
    Validates a controlled live OneDrive synchronization path through the
    production AlphaOmega synchronization components.

Verifies:
    - The controlled OneDrive scope can be retrieved.
    - Connector and Translator output preserve expected source facts.
    - Discovery produces the expected synchronization decisions.
    - Eligible CONTENT proceeds through Extraction and Load.
    - CONTAINER objects respect the orchestration boundary.
    - Persistence results match synchronization decisions.
    - Processing Job state reflects the completed synchronization run.

Does NOT:
    - Synchronize the complete OneDrive Source of Truth.
    - Modify OneDrive source content.
    - Bypass production synchronization stage boundaries.
    - Treat CONTAINER objects as Knowledge Objects.
"""

from datetime import datetime

from common.security.local_credential_provider import LocalCredentialProvider
from common.object_types import CONTENT, CONTAINER
from scripts.database.database_connection import DatabaseConnection
from scripts.database.source_repository import SourceRepository
from scripts.database.processing_job_repository import ProcessingJobRepository
from scripts.connectors.ms_graph.graph_connector import GraphConnector
from scripts.connectors.connector_section import ConnectorSection
from scripts.translator.graph_translator import GraphTranslator
from scripts.discovery.discovery_service import DiscoveryService
from scripts.database.knowledge_object_repository import KnowledgeObjectRepository
from scripts.extraction.extraction_service import ExtractionService
from scripts.load.load_repository import LoadRepository
from scripts.load.load_service import LoadService
from scripts.orchestration.sync_orchestrator import SynchronizationOrchestrator
from scripts.sync.sync_state import SyncState


TARGET_PATH = ("David", "Book Ideas")
PIPELINE_VERSION = "lab7-live-orchestrator-onedrive-book-ideas-v2"


def parse_timestamp(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value

    text = str(value).strip()

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    return datetime.fromisoformat(text)


class BookIdeasOneDriveConnector(GraphConnector):
    """
    Bounded live OneDrive connector for the selected test scope.

    It uses GraphConnector request/wrapping behavior, but intentionally
    enumerates this folder tree with /children rather than full-drive /delta.
    """

    @staticmethod
    def _find_folder(items, name):
        matches = [
            item
            for item in items
            if "folder" in item
            and (item.get("name") or "").strip().casefold() == name.casefold()
        ]

        if len(matches) != 1:
            raise RuntimeError(
                f"Could not uniquely locate OneDrive folder '{name}'. "
                f"Matches found: {len(matches)}"
            )

        return matches[0]

    @staticmethod
    def _join(parent, child):
        return f"{parent}/{child}" if parent else child

    @staticmethod
    def _parent(path):
        return path.rsplit("/", 1)[0] if "/" in path else None

    def _locate(self):
        items = self._get_collection("/me/drive/root/children")
        current = None

        for index, name in enumerate(TARGET_PATH):
            current = self._find_folder(items, name)

            folder_id = current.get("id")

            if not folder_id:
                raise RuntimeError(
                    f"OneDrive folder '{name}' is missing its Graph ID."
                )

            print(f"  FOUND: {name}")

            if index < len(TARGET_PATH) - 1:
                items = self._get_collection(
                    f"/me/drive/items/{folder_id}/children"
                )

        return current

    def _crawl(self, folder, raw_objects, path, parent_id):
        folder_id = folder.get("id")

        if not folder_id:
            raise RuntimeError("OneDrive folder is missing its Graph ID.")

        raw_objects.append(
            self._wrap_object(
                "driveItem",
                folder,
                connector_metadata={
                    "source_parent_object_id": parent_id,
                    "source_path": self._parent(path),
                    "object_path": path,
                    "hierarchy_verified": True,
                },
            )
        )

        children = self._get_collection(
            f"/me/drive/items/{folder_id}/children"
        )

        for item in children:
            item_id = item.get("id")
            item_name = item.get("name")

            if not item_id or not item_name:
                raise RuntimeError(
                    "OneDrive child object is missing its Graph ID or name."
                )

            child_path = self._join(path, item_name)

            if "folder" in item:
                self._crawl(
                    item,
                    raw_objects,
                    child_path,
                    folder_id,
                )
            else:
                raw_objects.append(
                    self._wrap_object(
                        "driveItem",
                        item,
                        connector_metadata={
                            "source_parent_object_id": folder_id,
                            "source_path": path,
                            "object_path": child_path,
                            "hierarchy_verified": True,
                        },
                    )
                )

    def run(self, source_name):
        if source_name is None or str(source_name).casefold() != "onedrive":
            raise ValueError(
                "BookIdeasOneDriveConnector supports OneDrive only."
            )

        print("Locating controlled OneDrive scope...")

        target = self._locate()
        parent_id = (
            target.get("parentReference")
            or {}
        ).get("id")

        raw_objects = []

        self._crawl(
            target,
            raw_objects,
            TARGET_PATH[-1],
            parent_id,
        )

        object_ids = [
            (item.get("raw_object") or {}).get("id")
            for item in raw_objects
        ]

        if any(object_id is None for object_id in object_ids):
            raise RuntimeError(
                "One or more enumerated OneDrive objects are missing Graph IDs."
            )

        if len(set(object_ids)) != len(object_ids):
            raise RuntimeError(
                "Duplicate Graph identities were returned in the controlled scope."
            )

        containers = [
            item
            for item in raw_objects
            if "folder" in (item.get("raw_object") or {})
        ]

        content = [
            item
            for item in raw_objects
            if "folder" not in (item.get("raw_object") or {})
        ]

        section = ConnectorSection("onedrive")
        section.raw_objects = raw_objects
        section.raw_metadata = {
            "enumeration_complete": True,
            "test_mode": True,
            "retrieval_strategy": "bounded_live_folder_recursive",
            "target_path": "/".join(TARGET_PATH),
            "target_folder_id": target["id"],
            "containers_retrieved": len(containers),
            "content_retrieved": len(content),
            "objects_retrieved": len(raw_objects),
        }
        section.connection_succeeded = True

        # This bounded test connector enumerates with /children and
        # therefore does not require a production full-drive deltaLink.
        section.lock()

        print("PASS: Controlled live Connector enumeration completed.")
        print(f"  CONTAINER objects: {len(containers)}")
        print(f"  CONTENT objects  : {len(content)}")
        print(f"  Connector objects: {len(raw_objects)}")

        return section


def build():
    credential_provider = LocalCredentialProvider()
    client = DatabaseConnection(credential_provider).connect()

    source_repository = SourceRepository(client)
    knowledge_object_repository = KnowledgeObjectRepository(client)
    processing_job_repository = ProcessingJobRepository(client)

    discovery_service = DiscoveryService(
        source_repository=source_repository,
        knowledge_object_repository=knowledge_object_repository,
    )

    load_service = LoadService(
        source_repository=source_repository,
        load_repository=LoadRepository(client),
    )

    orchestrator = SynchronizationOrchestrator(
        connector=BookIdeasOneDriveConnector(),
        translator=GraphTranslator(),
        discovery_service=discovery_service,
        extraction_service=ExtractionService(),
        load_service=load_service,
        processing_job_repository=processing_job_repository,
        pipeline_version=PIPELINE_VERSION,
    )

    return client, source_repository, orchestrator


def split_associations(associations):
    containers = []
    content = []

    for association in associations:
        translator = association.translator_record

        if translator is None:
            raise RuntimeError(
                "Synchronization association is missing its TranslatorRecord."
            )

        if translator.object_type == CONTAINER:
            containers.append(association)
        elif translator.object_type == CONTENT:
            content.append(association)
        else:
            raise RuntimeError(
                f"Unexpected translated object type: {translator.object_type}"
            )

    return containers, content


def get_load_eligible(content_associations):
    eligible = []

    for association in content_associations:
        discovery = association.discovery_record
        extraction = association.extraction_record

        if discovery is None or extraction is None:
            continue

        if discovery.sync_state == SyncState.NEW:
            eligible.append(association)

        elif discovery.sync_state == SyncState.MODIFIED:
            if (
                discovery.previous_content_hash is None
                or extraction.content_hash
                != discovery.previous_content_hash
            ):
                eligible.append(association)

    return tuple(eligible)


def verify_pipeline(result):
    associations = result["associations"]
    counts = result["counts"]

    containers, content = split_associations(associations)

    association_total = len(associations)
    translated_total = sum(
        1
        for association in associations
        if association.translator_record is not None
    )

    if translated_total != association_total:
        raise RuntimeError(
            "Not every synchronization association produced a TranslatorRecord."
        )

    for association in containers:
        if association.discovery_record is not None:
            raise RuntimeError(
                "CONTAINER unexpectedly entered Discovery."
            )
        if association.extraction_record is not None:
            raise RuntimeError(
                "CONTAINER unexpectedly reached Extraction."
            )

    states = {
        SyncState.NEW: 0,
        SyncState.MODIFIED: 0,
        SyncState.UNCHANGED: 0,
    }

    source_object_ids = set()

    for association in content:
        translator = association.translator_record
        discovery = association.discovery_record
        extraction = association.extraction_record

        if not translator.source_object_id:
            raise RuntimeError(
                "CONTENT TranslatorRecord is missing source_object_id."
            )

        if translator.source_object_id in source_object_ids:
            raise RuntimeError(
                "Duplicate CONTENT source identity entered synchronization."
            )

        source_object_ids.add(translator.source_object_id)

        if discovery is None:
            raise RuntimeError(
                f"CONTENT object '{translator.name}' did not enter Discovery."
            )

        if discovery.sync_state not in states:
            raise RuntimeError(
                f"Unexpected Discovery state: {discovery.sync_state}"
            )

        states[discovery.sync_state] += 1

        if discovery.sync_state == SyncState.UNCHANGED:
            if extraction is not None:
                raise RuntimeError(
                    f"UNCHANGED object '{translator.name}' "
                    "unexpectedly reached Extraction."
                )
            continue

        if discovery.requires_extraction is not True:
            raise RuntimeError(
                f"{discovery.sync_state} object '{translator.name}' "
                "was not marked for Extraction."
            )

        if extraction is None:
            raise RuntimeError(
                f"{discovery.sync_state} object '{translator.name}' "
                "did not produce an ExtractionRecord."
            )

        if extraction.correlation_id != association.correlation_id:
            raise RuntimeError(
                f"Extraction correlation mismatch for '{translator.name}'."
            )

        if not extraction.content_hash:
            raise RuntimeError(
                f"Extraction produced no content hash for '{translator.name}'."
            )

    discovered_total = sum(states.values())
    extracted_total = sum(
        1
        for association in content
        if association.extraction_record is not None
    )

    derived_counts = {
        "associations": association_total,
        "translated": translated_total,
        "discovered": discovered_total,
        "extracted": extracted_total,
        "new": states[SyncState.NEW],
        "modified": states[SyncState.MODIFIED],
        "unchanged": states[SyncState.UNCHANGED],
    }

    if counts != derived_counts:
        raise RuntimeError(
            "Orchestrator counts do not reconcile to actual records.\n"
            f"Derived:      {derived_counts}\n"
            f"Orchestrator: {counts}"
        )

    if discovered_total != len(content):
        raise RuntimeError(
            "Discovery records do not reconcile to translated CONTENT."
        )

    eligible = get_load_eligible(content)

    print("PASS: Pipeline records reconcile.")
    print(f"  Associations     : {association_total}")
    print(f"  Translated       : {translated_total}")
    print(f"  CONTAINER stop   : {len(containers)}")
    print(f"  CONTENT          : {len(content)}")
    print(f"  Discovered       : {discovered_total}")
    print(f"  NEW              : {states[SyncState.NEW]}")
    print(f"  MODIFIED         : {states[SyncState.MODIFIED]}")
    print(f"  UNCHANGED        : {states[SyncState.UNCHANGED]}")
    print(f"  Extracted        : {extracted_total}")
    print(f"  Canonical changes: {len(eligible)}")

    return containers, content, eligible


def verify_database(
    client,
    source_id,
    containers,
    content,
    eligible,
    processing_job_id,
):
    knowledge_object_ids = set()

    for association in content:
        translator = association.translator_record
        discovery = association.discovery_record
        extraction = association.extraction_record

        rows = (
            client.table("knowledge_objects")
            .select(
                "id,source_id,source_object_id,title,"
                "content_hash,source_modified_at"
            )
            .eq("source_id", source_id)
            .eq("source_object_id", translator.source_object_id)
            .execute()
            .data
            or []
        )

        if len(rows) != 1:
            raise RuntimeError(
                "Canonical identity did not resolve to exactly one "
                f"Knowledge Object for '{translator.name}'. "
                f"Rows found: {len(rows)}"
            )

        row = rows[0]

        if row["id"] in knowledge_object_ids:
            raise RuntimeError(
                "Duplicate Knowledge Object identity detected."
            )

        knowledge_object_ids.add(row["id"])

        if association in eligible:
            if extraction is None:
                raise RuntimeError(
                    f"Persistence-eligible object '{translator.name}' "
                    "has no ExtractionRecord."
                )

            if row["content_hash"] != extraction.content_hash:
                raise RuntimeError(
                    f"Persisted content hash mismatch for '{translator.name}'."
                )

            if (
                parse_timestamp(row["source_modified_at"])
                != parse_timestamp(translator.source_modified_at)
            ):
                raise RuntimeError(
                    "Persisted source_modified_at mismatch for "
                    f"'{translator.name}'.\n"
                    f"Translator: {translator.source_modified_at}\n"
                    f"Database:   {row['source_modified_at']}"
                )

        elif (
            discovery.sync_state == SyncState.MODIFIED
            and extraction is not None
            and discovery.previous_content_hash is not None
            and extraction.content_hash
            == discovery.previous_content_hash
        ):
            if row["content_hash"] != discovery.previous_content_hash:
                raise RuntimeError(
                    "Same-hash MODIFIED candidate altered canonical "
                    f"content for '{translator.name}'."
                )

    for association in containers:
        translator = association.translator_record

        rows = (
            client.table("knowledge_objects")
            .select("id")
            .eq("source_id", source_id)
            .eq("source_object_id", translator.source_object_id)
            .execute()
            .data
            or []
        )

        if rows:
            raise RuntimeError(
                "CONTAINER was persisted as a Knowledge Object: "
                f"'{translator.name}'."
            )

    history_rows = (
        client.table("sync_history")
        .select(
            "id,source_id,knowledge_object_id,"
            "processing_job_id,sync_event"
        )
        .eq("processing_job_id", processing_job_id)
        .execute()
        .data
        or []
    )

    if len(history_rows) != len(eligible):
        raise RuntimeError(
            "Sync History does not reconcile to canonical persistence.\n"
            f"Canonical changes: {len(eligible)}\n"
            f"Sync History rows: {len(history_rows)}"
        )

    expected_events = {}

    for association in eligible:
        translator = association.translator_record

        rows = (
            client.table("knowledge_objects")
            .select("id")
            .eq("source_id", source_id)
            .eq("source_object_id", translator.source_object_id)
            .execute()
            .data
            or []
        )

        if len(rows) != 1:
            raise RuntimeError(
                "Could not resolve persistence-eligible Knowledge Object."
            )

        expected_events[rows[0]["id"]] = (
            "new"
            if association.discovery_record.sync_state == SyncState.NEW
            else "modified"
        )

    for history in history_rows:
        if history["source_id"] != source_id:
            raise RuntimeError(
                "Sync History source identity mismatch."
            )

        expected_event = expected_events.get(
            history["knowledge_object_id"]
        )

        if expected_event is None:
            raise RuntimeError(
                "Sync History references an object that did not "
                "produce a canonical persistence event in this run."
            )

        if str(history["sync_event"]).casefold() != expected_event:
            raise RuntimeError(
                "Sync History event does not match Discovery state."
            )

    print("PASS: Canonical Knowledge Objects reconcile.")
    print("PASS: CONTAINER objects remain non-canonical.")
    print(f"PASS: Sync History reconciles ({len(history_rows)} events).")


def verify_processing_job(client, processing_job_id):
    rows = (
        client.table("processing_jobs")
        .select(
            "id,process_type,status,pipeline_version,"
            "completed_at,error_message"
        )
        .eq("id", processing_job_id)
        .execute()
        .data
        or []
    )

    if len(rows) != 1:
        raise RuntimeError(
            "Processing Job did not resolve to exactly one database row."
        )

    job = rows[0]

    if job["status"] != "completed":
        raise RuntimeError(
            f"Processing Job status is '{job['status']}', not completed."
        )

    if job["process_type"] != "sync":
        raise RuntimeError(
            f"Processing Job process_type is '{job['process_type']}', not sync."
        )

    if job["pipeline_version"] != PIPELINE_VERSION:
        raise RuntimeError(
            "Processing Job pipeline_version does not match this run."
        )

    if job["completed_at"] is None:
        raise RuntimeError(
            "Completed Processing Job has no completed_at timestamp."
        )

    if job["error_message"] is not None:
        raise RuntimeError(
            f"Completed Processing Job contains error_message: "
            f"{job['error_message']}"
        )

    print("PASS: Processing Job completed correctly.")


def main():
    print()
    print("=" * 72)
    print("AlphaOmega Live OneDrive E2E Synchronization Test")
    print("=" * 72)
    print(f"Scope: OneDrive / {' / '.join(TARGET_PATH)} / recursive")
    print()
    print("WARNING: THIS TEST WRITES TO ALPHAOMEGA.")
    print()

    client, source_repository, orchestrator = build()

    print("PASS: Live Orchestrator infrastructure constructed.")

    source_id = source_repository.find_id_by_name("OneDrive")

    if source_id is None:
        raise RuntimeError(
            "OneDrive Source is not registered."
        )

    print("PASS: OneDrive Source registration verified.")
    print()

    print("-" * 72)
    print("EXECUTING SYNCHRONIZATION")
    print("-" * 72)

    result = orchestrator.run(
        source_name="OneDrive",
        job_metadata={
            "test_type": "controlled_live_multi_record_e2e",
            "target_path": "/".join(TARGET_PATH),
            "recursive": True,
        },
    )

    processing_job_id = result["processing_job_id"]

    print("PASS: SynchronizationOrchestrator returned.")
    print(f"  Processing Job ID: {processing_job_id}")
    print()

    print("-" * 72)
    print("VERIFYING PIPELINE RESULTS")
    print("-" * 72)

    containers, content, eligible = verify_pipeline(result)

    print()
    print("-" * 72)
    print("VERIFYING DATABASE RESULTS")
    print("-" * 72)

    verify_database(
        client=client,
        source_id=source_id,
        containers=containers,
        content=content,
        eligible=eligible,
        processing_job_id=processing_job_id,
    )

    verify_processing_job(
        client,
        processing_job_id,
    )

    counts = result["counts"]

    same_hash_modified = sum(
        1
        for association in content
        if (
            association.discovery_record.sync_state == SyncState.MODIFIED
            and association.extraction_record is not None
            and association.discovery_record.previous_content_hash is not None
            and association.extraction_record.content_hash
            == association.discovery_record.previous_content_hash
        )
    )

    print()
    print("=" * 72)
    print("SYNCHRONIZATION RESULTS")
    print("=" * 72)
    print(f"Connector objects             : {len(containers) + len(content)}")
    print(f"CONTAINER objects             : {len(containers)}")
    print(f"CONTENT objects               : {len(content)}")
    print(f"Associations                  : {counts['associations']}")
    print(f"Translator records            : {counts['translated']}")
    print(f"Discovery records             : {counts['discovered']}")
    print(f"NEW                           : {counts['new']}")
    print(f"MODIFIED                      : {counts['modified']}")
    print(f"UNCHANGED                     : {counts['unchanged']}")
    print(f"Extraction records            : {counts['extracted']}")
    print(f"Same-hash MODIFIED suppressed : {same_hash_modified}")
    print(f"Canonical persistence events  : {len(eligible)}")
    print()
    print("Pipeline reconciliation       : PASS")
    print("Knowledge Object integrity    : PASS")
    print("CONTAINER boundary            : PASS")
    print("Sync History reconciliation   : PASS")
    print("Processing Job completion     : PASS")
    print()
    print("LIVE ONEDRIVE E2E SYNCHRONIZATION PASSED.")
    print()


if __name__ == "__main__":
    main()
