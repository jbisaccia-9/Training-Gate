"""Ports: the interfaces Training Gate needs from the outside world.

Implement these for your own systems (a project board, a document portal, a
data warehouse, an email provider, a chat tool, file storage). The engine only
ever talks to these protocols, so no vendor SDK leaks into the core logic.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Protocol

from .models import Case, OutboundEmail, PlanDocument, Reply, TeamMember


class CaseTracker(Protocol):
    """Work-tracking board (e.g. a kanban / project-management board)."""

    def list_cases(self) -> Iterable[Case]: ...


class DocumentPortal(Protocol):
    """External portal where plan documents are published and proof is filed."""

    def latest_plan(self, case_id: str) -> PlanDocument | None: ...

    def download(self, plan: PlanDocument) -> bytes: ...

    def upload_attestation(self, case_id: str, filename: str, content: bytes) -> str:
        """Upload proof of completion. Returns a receipt / document reference."""
        ...


class TeamRoster(Protocol):
    """Source of truth for who is assigned to a case (e.g. a data warehouse)."""

    def team_for(self, case_id: str) -> Sequence[TeamMember]: ...

    def supervisor_for(self, case_id: str) -> TeamMember | None: ...


class Mailer(Protocol):
    def send(self, email: OutboundEmail) -> str:
        """Send an email. Returns a message/thread id used to find replies."""
        ...

    def replies_to(self, message_id: str) -> Sequence[Reply]: ...


class ChatNotifier(Protocol):
    def send(self, recipients: Sequence[TeamMember], text: str) -> None: ...


class DeckStorage(Protocol):
    """Somewhere to put the generated deck so it can be linked to."""

    def publish(self, filename: str, content: bytes) -> str:
        """Store the file. Returns a shareable URI."""
        ...
