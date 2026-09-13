"""
Load Service Test

Purpose:
    Provides isolated regression validation of AlphaOmega LoadService using
    mocked repositories.

Verifies:
    - NEW associations are persisted correctly.
    - MODIFIED associations are persisted correctly.
    - Processing Job identity propagates correctly.
    - Source identity lookup is cached.
    - Correlation mismatches are isolated.
    - Missing Translator, Discovery, and Extraction records are handled.
    - UNCHANGED associations are rejected from Load.
    - Repository persistence failures remain isolated from other records.
    - LoadSection completes and locks correctly.

Does NOT:
    - Connect to Supabase.
    - Modify AlphaOmega database records.
    - Retrieve live source content.
    - Execute the complete synchronization pipeline.
"""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from scripts.load.load_service import (
    LoadService,
)
from scripts.sync.sync_association import (
    SynchronizationAssociation,
)
from scripts.sync.sync_state import (
    SyncState,
)


PROCESSING_JOB_ID = str(
    uuid4()
)

SOURCE_ID = str(
    uuid4()
)


# ============================================================================
# Helpers
# ============================================================================


def build_translator_record(
    correlation_id,
    source_object_id,
    name,
):
    """
    Build a controlled Translator-like record.
    """

    return SimpleNamespace(
        correlation_id=correlation_id,
        source_name="OneDrive",
        source_object_id=source_object_id,
        source_parent_object_id="parent-123",
        source_path=f"/Writings/{name}",
        source_url=(
            "https://alphaomega.invalid/"
            f"{source_object_id}"
        ),
        name=name,
        object_type="CONTENT",
        source_created_at="2026-08-20T12:00:00+00:00",
        source_modified_at="2026-08-20T13:00:00+00:00",
        metadata={
            "source_metadata": "translator-value",
        },
    )


def build_discovery_record(
    correlation_id,
    sync_state,
    knowledge_object_id=None,
    comparison_reason=None,
):
    """
    Build a controlled Discovery-like record.
    """

    return SimpleNamespace(
        correlation_id=correlation_id,
        sync_state=sync_state,
        knowledge_object_id=knowledge_object_id,
        comparison_reason=comparison_reason,
    )


def build_extraction_record(
    correlation_id,
    canonical_content,
):
    """
    Build a controlled Extraction-like record.
    """

    return SimpleNamespace(
        correlation_id=correlation_id,
        canonical_content=canonical_content,
        content_hash=(
            "a" * 64
        ),
        canonical_metadata={
            "content_length": len(
                canonical_content
            ),
        },
        extractor_name="text_extractor",
        extraction_timestamp=(
            "2026-08-20T14:00:00+00:00"
        ),
    )


def build_association(
    *,
    source_object_id,
    name,
    sync_state,
    knowledge_object_id=None,
    comparison_reason=None,
):
    """
    Build a complete loadable SynchronizationAssociation.
    """

    correlation_id = str(
        uuid4()
    )

    association = SynchronizationAssociation(
        correlation_id
    )

    translator_record = (
        build_translator_record(
            correlation_id=correlation_id,
            source_object_id=source_object_id,
            name=name,
        )
    )

    discovery_record = (
        build_discovery_record(
            correlation_id=correlation_id,
            sync_state=sync_state,
            knowledge_object_id=knowledge_object_id,
            comparison_reason=comparison_reason,
        )
    )

    extraction_record = (
        build_extraction_record(
            correlation_id=correlation_id,
            canonical_content=(
                f"Canonical content for {name}"
            ),
        )
    )

    association.attach_translator(
        translator_record
    )

    association.attach_discovery(
        discovery_record
    )

    association.attach_extraction(
        extraction_record
    )

    return association


def build_service(
    *,
    persist_side_effect=None,
):
    """
    Build LoadService with mocked repositories.
    """

    source_repository = Mock()

    source_repository.find_id_by_name.return_value = (
        SOURCE_ID
    )

    load_repository = Mock()

    if persist_side_effect is None:
        load_repository.persist.return_value = str(
            uuid4()
        )

    else:
        load_repository.persist.side_effect = (
            persist_side_effect
        )

    service = LoadService(
        source_repository=source_repository,
        load_repository=load_repository,
    )

    return (
        service,
        source_repository,
        load_repository,
    )


# ============================================================================
# Tests
# ============================================================================


def test_new_association():
    """
    Verify NEW association values are passed correctly
    to LoadRepository.
    """

    (
        service,
        source_repository,
        load_repository,
    ) = build_service()

    association = build_association(
        source_object_id="new-object-001",
        name="New Object.txt",
        sync_state=SyncState.NEW,
    )

    section = service.run(
        associations=[
            association,
        ],
        processing_job_id=PROCESSING_JOB_ID,
    )

    assert section.load_succeeded is True
    assert section.is_locked is True
    assert len(section.record_errors) == 0

    source_repository.find_id_by_name.assert_called_once_with(
        "OneDrive"
    )

    load_repository.persist.assert_called_once()

    kwargs = (
        load_repository
        .persist
        .call_args
        .kwargs
    )

    assert kwargs["sync_state"] == SyncState.NEW.value

    assert kwargs["knowledge_object_id"] is None

    assert kwargs["source_id"] == SOURCE_ID

    assert (
        kwargs["source_object_id"]
        == "new-object-001"
    )

    assert (
        kwargs["source_parent_object_id"]
        == "parent-123"
    )

    assert (
        kwargs["source_path"]
        == "/Writings/New Object.txt"
    )

    assert (
        kwargs["title"]
        == "New Object.txt"
    )

    assert kwargs["object_type"] == "CONTENT"

    assert (
        kwargs["canonical_content"]
        == "Canonical content for New Object.txt"
    )

    assert kwargs["content_hash"] == "a" * 64

    assert (
        kwargs["processing_job_id"]
        == PROCESSING_JOB_ID
    )

    assert kwargs["comparison_reason"] is None

    assert (
        kwargs["metadata"]["source_metadata"]
        == "translator-value"
    )

    assert (
        kwargs["metadata"]["extraction"][
            "content_length"
        ]
        == len(
            "Canonical content for New Object.txt"
        )
    )

    assert (
        kwargs["metadata"]["extraction"][
            "extractor_name"
        ]
        == "text_extractor"
    )

    print(
        "PASS: NEW association persisted correctly."
    )

    print(
        "PASS: Processing Job identity propagated."
    )


def test_modified_association():
    """
    Verify MODIFIED association preserves existing
    Knowledge Object identity and comparison reason.
    """

    (
        service,
        _,
        load_repository,
    ) = build_service()

    knowledge_object_id = str(
        uuid4()
    )

    association = build_association(
        source_object_id="modified-object-001",
        name="Modified Object.txt",
        sync_state=SyncState.MODIFIED,
        knowledge_object_id=knowledge_object_id,
        comparison_reason=(
            "source modified timestamp changed"
        ),
    )

    section = service.run(
        associations=[
            association,
        ],
        processing_job_id=PROCESSING_JOB_ID,
    )

    assert section.load_succeeded is True
    assert len(section.record_errors) == 0

    kwargs = (
        load_repository
        .persist
        .call_args
        .kwargs
    )

    assert (
        kwargs["sync_state"]
        == SyncState.MODIFIED.value
    )

    assert (
        kwargs["knowledge_object_id"]
        == knowledge_object_id
    )

    assert (
        kwargs["comparison_reason"]
        == "source modified timestamp changed"
    )

    print(
        "PASS: MODIFIED association persisted correctly."
    )


def test_source_lookup_cache():
    """
    Verify one Source lookup is used for multiple records
    from the same Source.
    """

    (
        service,
        source_repository,
        load_repository,
    ) = build_service()

    associations = [
        build_association(
            source_object_id="cache-001",
            name="Cache One.txt",
            sync_state=SyncState.NEW,
        ),
        build_association(
            source_object_id="cache-002",
            name="Cache Two.txt",
            sync_state=SyncState.NEW,
        ),
        build_association(
            source_object_id="cache-003",
            name="Cache Three.txt",
            sync_state=SyncState.NEW,
        ),
    ]

    section = service.run(
        associations=associations,
        processing_job_id=PROCESSING_JOB_ID,
    )

    assert section.load_succeeded is True
    assert len(section.record_errors) == 0

    assert (
        source_repository
        .find_id_by_name
        .call_count
        == 1
    )

    assert (
        load_repository
        .persist
        .call_count
        == 3
    )

    print(
        "PASS: Load Source lookup caching correct."
    )


def test_correlation_mismatch():
    """
    Verify a correlation mismatch becomes a record-level
    Load error and does not reach persistence.
    """

    (
        service,
        _,
        load_repository,
    ) = build_service()

    association = build_association(
        source_object_id="correlation-001",
        name="Correlation Test.txt",
        sync_state=SyncState.NEW,
    )

    #
    # Deliberately corrupt the ExtractionRecord correlation
    # after the association has been constructed.
    #
    association.extraction_record.correlation_id = str(
        uuid4()
    )

    section = service.run(
        associations=[
            association,
        ],
        processing_job_id=PROCESSING_JOB_ID,
    )

    assert section.load_succeeded is True
    assert len(section.record_errors) == 1

    error = section.record_errors[0]

    assert error["stage"] == "Load"

    assert (
        error["correlation_id"]
        == association.correlation_id
    )

    assert (
        error["object_id"]
        == "correlation-001"
    )

    assert (
        "ExtractionRecord correlation_id"
        in error["failure_reason"]
    )

    load_repository.persist.assert_not_called()

    print(
        "PASS: Correlation mismatch isolated correctly."
    )


def test_missing_stage_records():
    """
    Verify missing stage-owned records become record-level
    Load errors.
    """

    # ------------------------------------------------------------------
    # Missing TranslatorRecord
    # ------------------------------------------------------------------

    (
        service,
        _,
        load_repository,
    ) = build_service()

    correlation_id = str(
        uuid4()
    )

    missing_translator = (
        SynchronizationAssociation(
            correlation_id
        )
    )

    missing_translator.attach_discovery(
        build_discovery_record(
            correlation_id=correlation_id,
            sync_state=SyncState.NEW,
        )
    )

    missing_translator.attach_extraction(
        build_extraction_record(
            correlation_id=correlation_id,
            canonical_content="Missing translator",
        )
    )

    section = service.run(
        associations=[
            missing_translator,
        ],
        processing_job_id=PROCESSING_JOB_ID,
    )

    assert len(section.record_errors) == 1

    assert (
        "missing TranslatorRecord"
        in section.record_errors[0][
            "failure_reason"
        ]
    )

    load_repository.persist.assert_not_called()

    # ------------------------------------------------------------------
    # Missing DiscoveryRecord
    # ------------------------------------------------------------------

    (
        service,
        _,
        load_repository,
    ) = build_service()

    correlation_id = str(
        uuid4()
    )

    missing_discovery = (
        SynchronizationAssociation(
            correlation_id
        )
    )

    missing_discovery.attach_translator(
        build_translator_record(
            correlation_id=correlation_id,
            source_object_id="missing-discovery",
            name="Missing Discovery.txt",
        )
    )

    missing_discovery.attach_extraction(
        build_extraction_record(
            correlation_id=correlation_id,
            canonical_content="Missing discovery",
        )
    )

    section = service.run(
        associations=[
            missing_discovery,
        ],
        processing_job_id=PROCESSING_JOB_ID,
    )

    assert len(section.record_errors) == 1

    assert (
        "missing DiscoveryRecord"
        in section.record_errors[0][
            "failure_reason"
        ]
    )

    load_repository.persist.assert_not_called()

    # ------------------------------------------------------------------
    # Missing ExtractionRecord
    # ------------------------------------------------------------------

    (
        service,
        _,
        load_repository,
    ) = build_service()

    correlation_id = str(
        uuid4()
    )

    missing_extraction = (
        SynchronizationAssociation(
            correlation_id
        )
    )

    missing_extraction.attach_translator(
        build_translator_record(
            correlation_id=correlation_id,
            source_object_id="missing-extraction",
            name="Missing Extraction.txt",
        )
    )

    missing_extraction.attach_discovery(
        build_discovery_record(
            correlation_id=correlation_id,
            sync_state=SyncState.NEW,
        )
    )

    section = service.run(
        associations=[
            missing_extraction,
        ],
        processing_job_id=PROCESSING_JOB_ID,
    )

    assert len(section.record_errors) == 1

    assert (
        "missing ExtractionRecord"
        in section.record_errors[0][
            "failure_reason"
        ]
    )

    load_repository.persist.assert_not_called()

    print(
        "PASS: Missing stage records isolated correctly."
    )


def test_unchanged_rejected():
    """
    Verify UNCHANGED associations are not accepted by Load.
    """

    (
        service,
        _,
        load_repository,
    ) = build_service()

    association = build_association(
        source_object_id="unchanged-001",
        name="Unchanged Object.txt",
        sync_state=SyncState.UNCHANGED,
    )

    section = service.run(
        associations=[
            association,
        ],
        processing_job_id=PROCESSING_JOB_ID,
    )

    assert section.load_succeeded is True
    assert len(section.record_errors) == 1

    error = section.record_errors[0]

    assert (
        "not NEW or MODIFIED"
        in error["failure_reason"]
    )

    assert (
        error["sync_state"]
        == SyncState.UNCHANGED.value
    )

    load_repository.persist.assert_not_called()

    print(
        "PASS: UNCHANGED association rejected by Load."
    )


def test_repository_failure_continues_batch():
    """
    Verify one persistence failure is isolated and later
    associations continue loading.
    """

    persisted_ids = [
        str(
            uuid4()
        ),
        RuntimeError(
            "Synthetic Load persistence failure."
        ),
        str(
            uuid4()
        ),
    ]

    (
        service,
        _,
        load_repository,
    ) = build_service(
        persist_side_effect=persisted_ids,
    )

    associations = [
        build_association(
            source_object_id="load-before",
            name="Before Failure.txt",
            sync_state=SyncState.NEW,
        ),
        build_association(
            source_object_id="load-failure",
            name="Failure.txt",
            sync_state=SyncState.NEW,
        ),
        build_association(
            source_object_id="load-after",
            name="After Failure.txt",
            sync_state=SyncState.NEW,
        ),
    ]

    section = service.run(
        associations=associations,
        processing_job_id=PROCESSING_JOB_ID,
    )

    assert section.load_succeeded is True

    assert (
        load_repository
        .persist
        .call_count
        == 3
    )

    assert len(section.record_errors) == 1

    error = section.record_errors[0]

    assert (
        error["correlation_id"]
        == associations[1].correlation_id
    )

    assert (
        error["object_id"]
        == "load-failure"
    )

    assert (
        error["exception_type"]
        == "RuntimeError"
    )

    assert (
        error["failure_reason"]
        == "Synthetic Load persistence failure."
    )

    print(
        "PASS: Load persistence failure isolated "
        "and batch continued."
    )

    print(
        "PASS: Failed Load record preserved "
        "correlation identity."
    )


def test_missing_processing_job():
    """
    Verify Load requires an existing Processing Job ID.
    """

    (
        service,
        _,
        load_repository,
    ) = build_service()

    association = build_association(
        source_object_id="job-001",
        name="Processing Job Test.txt",
        sync_state=SyncState.NEW,
    )

    try:
        service.run(
            associations=[
                association,
            ],
            processing_job_id=None,
        )

        raise AssertionError(
            "Missing processing_job_id did not fail."
        )

    except ValueError as error:
        assert (
            str(error)
            == "processing_job_id is required."
        )

    load_repository.persist.assert_not_called()

    print(
        "PASS: Missing Processing Job rejected."
    )


def test_section_locking():
    """
    Verify LoadSection is locked after successful stage completion.
    """

    (
        service,
        _,
        _,
    ) = build_service()

    association = build_association(
        source_object_id="lock-001",
        name="Lock Test.txt",
        sync_state=SyncState.NEW,
    )

    section = service.run(
        associations=[
            association,
        ],
        processing_job_id=PROCESSING_JOB_ID,
    )

    assert section.load_succeeded is True
    assert section.is_locked is True

    assert isinstance(
        section.record_errors,
        tuple,
    )

    print(
        "PASS: LoadSection locked after completion."
    )


# ============================================================================
# Main
# ============================================================================


def main():
    """
    Run isolated LoadService tests.
    """

    print(
        "\nRunning LoadService isolated tests...\n"
    )

    test_new_association()
    test_modified_association()
    test_source_lookup_cache()
    test_correlation_mismatch()
    test_missing_stage_records()
    test_unchanged_rejected()
    test_repository_failure_continues_batch()
    test_missing_processing_job()
    test_section_locking()

    print(
        "\nLoadService isolated tests PASSED.\n"
    )


if __name__ == "__main__":
    main()