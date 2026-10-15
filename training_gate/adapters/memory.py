"""In-memory adapters for tests, demos, and as a reference for real integrations."""

from __future__ import annotations

import itertools
from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from ..models import Case, OutboundEmail, PlanDocument, Reply, TeamMember


class InMemoryCaseTracker:
    def __init__(self, cases: Sequence[Case] = ()):
        self.cases = list(cases)

    def list_cases(self) -> list[Case]:
        return list(self.cases)


class InMemoryPortal:
    def __init__(self, plans: Sequence[PlanDocument] = ()):
        self.plans: dict[str, list[PlanDocument]] = defaultdict(list)
        for plan in plans:
            self.publish(plan)
        self.uploads: list[tuple[str, str, bytes]] = []

    def publish(self, plan: PlanDocument) -> None:
        self.plans[plan.case_id].append(plan)

    def latest_plan(self, case_id: str) -> PlanDocument | None:
        plans = self.plans.get(case_id)
        return max(plans, key=lambda p: p.published_on) if plans else None

    def download(self, plan: PlanDocument) -> bytes:
        return f"[synthetic source document {plan.document_id} v{plan.version}]".encode()

    def upload_attestation(self, case_id: str, filename: str, content: bytes) -> str:
        self.uploads.append((case_id, filename, content))
        return f"portal-receipt-{len(self.uploads):04d}"


class InMemoryRoster:
    def __init__(
        self,
        teams: dict[str, Sequence[TeamMember]] | None = None,
        supervisors: dict[str, TeamMember] | None = None,
    ):
        self.teams = {k: list(v) for k, v in (teams or {}).items()}
        self.supervisors = dict(supervisors or {})

    def team_for(self, case_id: str) -> list[TeamMember]:
        return list(self.teams.get(case_id, []))

    def supervisor_for(self, case_id: str) -> TeamMember | None:
        return self.supervisors.get(case_id)


class InMemoryMailer:
    def __init__(self):
        self.sent: dict[str, OutboundEmail] = {}
        self.replies: dict[str, list[Reply]] = defaultdict(list)
        self._ids = itertools.count(1)

    def send(self, email: OutboundEmail) -> str:
        message_id = f"msg-{next(self._ids):04d}"
        self.sent[message_id] = email
        return message_id

    def replies_to(self, message_id: str) -> list[Reply]:
        return list(self.replies.get(message_id, []))

    # test/demo helper
    def simulate_reply(self, to_address: str, body: str, at: datetime) -> str:
        message_id = next(mid for mid, e in self.sent.items() if to_address in e.to)
        self.replies[message_id].append(Reply(sender=to_address, body=body, received_at=at))
        return message_id


class InMemoryChat:
    def __init__(self):
        self.messages: list[tuple[tuple[str, ...], str]] = []

    def send(self, recipients: Sequence[TeamMember], text: str) -> None:
        handles = tuple(r.chat_handle or r.email for r in recipients)
        self.messages.append((handles, text))


class InMemoryStorage:
    def __init__(self):
        self.files: dict[str, bytes] = {}

    def publish(self, filename: str, content: bytes) -> str:
        self.files[filename] = content
        return f"memory://decks/{filename}"


class LocalFileStorage:
    """Writes decks to a local folder and returns file:// links."""

    def __init__(self, directory: Path | str):
        self.directory = Path(directory)

    def publish(self, filename: str, content: bytes) -> str:
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / filename
        path.write_bytes(content)
        return path.resolve().as_uri()
