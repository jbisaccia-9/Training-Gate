"""Durable run state: which assignments exist and who was on each team last run."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .models import OPEN_STATUSES, TrainingAssignment, assignment_key


class JsonStateStore:
    """Single-file JSON state. Swap for a database table in production."""

    SCHEMA_VERSION = 1

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else None
        self.assignments: dict[str, TrainingAssignment] = {}
        self._known_members: dict[str, list[str]] = {}
        if self.path and self.path.exists():
            self._load()

    def _load(self) -> None:
        data = json.loads(self.path.read_text())
        self.assignments = {
            key: TrainingAssignment.from_dict(value)
            for key, value in data.get("assignments", {}).items()
        }
        self._known_members = data.get("known_members", {})

    def save(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "assignments": {k: a.to_dict() for k, a in self.assignments.items()},
            "known_members": self._known_members,
        }
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True))
        os.replace(tmp, self.path)

    def known_members(self, case_id: str) -> set[str] | None:
        """Members seen on the case last run, or None if the case is new to us."""
        if case_id not in self._known_members:
            return None
        return set(self._known_members[case_id])

    def set_known_members(self, case_id: str, member_ids: set[str]) -> None:
        self._known_members[case_id] = sorted(member_ids)

    def find(
        self, case_id: str, document_id: str, version: str, member_id: str
    ) -> TrainingAssignment | None:
        return self.assignments.get(assignment_key(case_id, document_id, version, member_id))

    def add(self, assignment: TrainingAssignment) -> None:
        self.assignments[assignment.assignment_id] = assignment

    def open_assignments(self) -> list[TrainingAssignment]:
        return [a for a in self.assignments.values() if a.status in OPEN_STATUSES]
