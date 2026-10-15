"""Skeleton for wiring Training Gate to real systems.

Copy this file into your own private package, fill in each adapter, and point
`[adapters] wiring` in your config at `your_package.wiring:build_adapters`.

Keep credentials out of source control: read them from environment variables
or your secret manager here.
"""

from __future__ import annotations

import os
from collections.abc import Sequence

from training_gate.adapters.fixture import Adapters
from training_gate.models import Case, OutboundEmail, PlanDocument, Reply, TeamMember


class BoardTracker:
    """Work-tracking board, e.g. a project-management tool with a GraphQL/REST API.

    Map one board item to one `Case`; read the training-expiration date column
    and (optionally) the last-trained date column.
    """

    def __init__(self, api_token: str, board_id: str):
        self.api_token, self.board_id = api_token, board_id

    def list_cases(self) -> list[Case]:
        raise NotImplementedError


class PortalClient:
    """External document portal (often browser automation or a partner API).

    `latest_plan` must parse the document into `PlanSection`s for the deck;
    `upload_attestation` must return the portal's receipt or document id.
    """

    def latest_plan(self, case_id: str) -> PlanDocument | None:
        raise NotImplementedError

    def download(self, plan: PlanDocument) -> bytes:
        raise NotImplementedError

    def upload_attestation(self, case_id: str, filename: str, content: bytes) -> str:
        raise NotImplementedError


class WarehouseRoster:
    """Team assignments from a data warehouse (any DB-API / SQLAlchemy connection).

    Use a parameterized query and only select the columns the gate needs:
    member id, display name, work email, chat handle.
    """

    def team_for(self, case_id: str) -> Sequence[TeamMember]:
        raise NotImplementedError

    def supervisor_for(self, case_id: str) -> TeamMember | None:
        raise NotImplementedError


class WorkMailer:
    """Email provider API. `send` returns a conversation/thread id, and
    `replies_to` lists replies in that thread."""

    def send(self, email: OutboundEmail) -> str:
        raise NotImplementedError

    def replies_to(self, message_id: str) -> Sequence[Reply]:
        raise NotImplementedError


class WorkChat:
    """Team chat (direct or group message to the trainee and supervisor)."""

    def send(self, recipients: Sequence[TeamMember], text: str) -> None:
        raise NotImplementedError


class SharedDriveStorage:
    """File storage that returns an access-controlled link for the deck."""

    def publish(self, filename: str, content: bytes) -> str:
        raise NotImplementedError


def build_adapters() -> Adapters:
    return Adapters(
        tracker=BoardTracker(os.environ["BOARD_API_TOKEN"], os.environ["BOARD_ID"]),
        portal=PortalClient(),
        roster=WarehouseRoster(),
        mailer=WorkMailer(),
        chat=WorkChat(),
        storage=SharedDriveStorage(),
    )
