"""
Synchronization Base Section Test

Purpose:
    Validates the common synchronization section locking contract.

Verifies:
    - A section begins unlocked.
    - Stage-owned values can be populated before locking.
    - Locking marks the section complete and immutable.
    - Supported mutable values are frozen when the section is locked.
    - Attempts to modify locked section state are rejected.

Does NOT:
    - Test a specific synchronization stage.
    - Execute synchronization.
    - Persist synchronization data.
    - Unlock completed sections.
"""

from scripts.sync.sync_base_section import BaseSection
from scripts.sync.sync_exceptions import SectionLockedError


class TestSection(BaseSection):

    def __init__(self):
        super().__init__()

        self.name = "Connector"
        self.count = 5
        self.items = ["One", "Two"]


def main():

    print("Creating section...")
    section = TestSection()

    print(f"Locked: {section.is_locked}")

    print("\nModifying before lock...")
    section.name = "Discovery"
    print(section.name)

    print("\nLocking section...")
    section.lock()

    print(f"Locked: {section.is_locked}")

    print("\nAttempting modification after lock...")

    try:
        section.name = "Extraction"
    except SectionLockedError as ex:
        print(f"PASS: {ex}")

    print("\nAttempting to add attribute...")

    try:
        section.new_field = 123
    except SectionLockedError as ex:
        print(f"PASS: {ex}")

    print("\nTesting frozen list...")

    print(type(section.items))

    try:
        section.items.append("Three")
    except Exception as ex:
        print(f"PASS: {type(ex).__name__}")

    print("\nBaseSection testing complete.")


if __name__ == "__main__":
    main()