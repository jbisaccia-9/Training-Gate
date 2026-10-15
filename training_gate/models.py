"""Domain models.

Everything here is deliberately generic. A *case* is any unit of work that has
a governing *plan document* and a *team* of people who must be trained on it.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from enum import Enum


@dataclass(frozen=True)
class Case:
    """A record on the work-tracking board."""

    case_id: str
    display_name: str
    training_expires_on: date | None
    last_trained_on: date | None = None


@dataclass(frozen=True)
class TeamMember:
    """A person who can receive training or be copied on it."""

    member_id: str
    name: str
    email: str
    chat_handle: str | None = None


@dataclass(frozen=True)
class PlanSection:
    heading: str
    bullets: tuple[str, ...]


@dataclass(frozen=True)
class PlanDocument:
    """The governing document a team must be trained on, as found in the portal."""

    case_id: str
    document_id: str
    version: str
    title: str
    published_on: date
    sections: tuple[PlanSection, ...]
    filename: str = "plan-document.pdf"
    media_type: str = "application/pdf"


@dataclass(frozen=True)
class Attachment:
    filename: str
    content: bytes
    media_type: str


@dataclass(frozen=True)
class OutboundEmail:
    to: tuple[str, ...]
    cc: tuple[str, ...]
    subject: str
    body: str
    attachments: tuple[Attachment, ...] = ()


@dataclass(frozen=True)
class Reply:
    sender: str
    body: str
    received_at: datetime


class Trigger(str, Enum):
    EXPIRING_RENEWAL = "expiring_renewal"
    NEW_TEAM_MEMBER = "new_team_member"


class AssignmentStatus(str, Enum):
    SENT = "sent"
    REMINDED = "reminded"
    ACKNOWLEDGED = "acknowledged"
    FILED = "filed"


OPEN_STATUSES = frozenset(
    {AssignmentStatus.SENT, AssignmentStatus.REMINDED, AssignmentStatus.ACKNOWLEDGED}
)


def assignment_key(case_id: str, document_id: str, version: str, member_id: str) -> str:
    raw = f"{case_id}|{document_id}|{version}|{member_id}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class TrainingAssignment:
    """One person's obligation to review one version of one plan document."""

    assignment_id: str
    case_id: str
    case_display_name: str
    document_id: str
    document_version: str
    document_title: str
    member: TeamMember
    supervisor: TeamMember | None
    trigger: Trigger
    deck_uri: str
    deck_sha256: str
    message_id: str
    sent_at: datetime
    status: AssignmentStatus = AssignmentStatus.SENT
    reminded_at: datetime | None = None
    acknowledged_at: datetime | None = None
    acknowledgement_excerpt: str | None = None
    filed_at: datetime | None = None
    filing_receipt: str | None = None
    history: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["trigger"] = self.trigger.value
        data["status"] = self.status.value
        for key in ("sent_at", "reminded_at", "acknowledged_at", "filed_at"):
            value = getattr(self, key)
            data[key] = value.isoformat() if value else None
        return data

    @classmethod
    def from_dict(cls, data: dict) -> TrainingAssignment:
        data = dict(data)
        data["member"] = TeamMember(**data["member"])
        data["supervisor"] = TeamMember(**data["supervisor"]) if data.get("supervisor") else None
        data["trigger"] = Trigger(data["trigger"])
        data["status"] = AssignmentStatus(data["status"])
        for key in ("sent_at", "reminded_at", "acknowledged_at", "filed_at"):
            data[key] = datetime.fromisoformat(data[key]) if data.get(key) else None
        return cls(**data)
