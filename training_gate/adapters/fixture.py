"""Build in-memory adapters from a JSON fixture of synthetic data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..models import Case, PlanDocument, PlanSection, TeamMember
from .memory import (
    InMemoryCaseTracker,
    InMemoryChat,
    InMemoryMailer,
    InMemoryPortal,
    InMemoryRoster,
    LocalFileStorage,
)


@dataclass
class Adapters:
    """The set of adapters a wiring function must return."""

    tracker: object
    portal: object
    roster: object
    mailer: object
    chat: object
    storage: object


def _date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def load_fixture(path: Path | str) -> dict:
    data = json.loads(Path(path).read_text())
    people = {p["member_id"]: TeamMember(**p) for p in data["people"]}
    cases = [
        Case(
            case_id=c["case_id"],
            display_name=c["display_name"],
            training_expires_on=_date(c.get("training_expires_on")),
            last_trained_on=_date(c.get("last_trained_on")),
        )
        for c in data["cases"]
    ]
    plans = [
        PlanDocument(
            case_id=p["case_id"],
            document_id=p["document_id"],
            version=p["version"],
            title=p["title"],
            published_on=date.fromisoformat(p["published_on"]),
            sections=tuple(
                PlanSection(s["heading"], tuple(s["bullets"])) for s in p["sections"]
            ),
        )
        for p in data["plans"]
    ]
    teams = {cid: [people[m] for m in ids] for cid, ids in data["teams"].items()}
    supervisors = {cid: people[mid] for cid, mid in data["supervisors"].items()}
    return {"people": people, "cases": cases, "plans": plans, "teams": teams, "supervisors": supervisors}


def build_adapters(fixture: str, deck_dir: str = "out/decks") -> Adapters:
    """Wiring entry point used by examples/config.example.toml."""
    world = load_fixture(fixture)
    return Adapters(
        tracker=InMemoryCaseTracker(world["cases"]),
        portal=InMemoryPortal(world["plans"]),
        roster=InMemoryRoster(world["teams"], world["supervisors"]),
        mailer=InMemoryMailer(),
        chat=InMemoryChat(),
        storage=LocalFileStorage(deck_dir),
    )
