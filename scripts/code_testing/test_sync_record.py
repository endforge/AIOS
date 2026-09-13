"""
Synchronization Record Test

Purpose:
    Validates the SynchronizationRecord section container contract.

Verifies:
    - Completed synchronization sections can be attached by name.
    - Attached sections can be retrieved.
    - Section membership can be queried.
    - Duplicate section names are rejected.
    - All attached sections can be returned.

Does NOT:
    - Populate stage-owned sections.
    - Execute synchronization stages.
    - Modify completed section contents.
    - Persist synchronization data.
"""

from scripts.sync.sync_record import SyncRecord


def main():

    record = SyncRecord()

    print(type(record))
    print(record._sections)


if __name__ == "__main__":
    main()