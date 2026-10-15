"""The orchestrator: one call to `TrainingGate.run()` is one scheduled run."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from .config import GateConfig
from .models import (
    Attachment,
    AssignmentStatus,
    Case,
    OutboundEmail,
    PlanDocument,
    TeamMember,
    TrainingAssignment,
    Trigger,
    assignment_key,
)
from .ports import CaseTracker, ChatNotifier, DeckStorage, DocumentPortal, Mailer, TeamRoster
from .rendering.attestation import render_attestation
from .rendering.deck import render_deck
from .state import JsonStateStore

_QUOTE_START = re.compile(r"^\s*(>|On .+wrote:|-----Original Message-----|From:)", re.IGNORECASE)
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def is_acknowledgement(body: str, keyword: str) -> bool:
    """True when the first line of the reply's own text starts with the keyword.

    Deliberately strict: "Reviewed, thanks" counts; "not reviewed yet" and a
    keyword that only appears in the quoted original message do not.
    """
    for line in body.splitlines():
        if _QUOTE_START.match(line):
            return False
        if line.strip():
            return re.match(rf"^\s*{re.escape(keyword)}\b", line, re.IGNORECASE) is not None
    return False


def _first_line(body: str) -> str:
    return next((line.strip() for line in body.splitlines() if line.strip()), "")[:200]


def _safe(value: str) -> str:
    return _SAFE_NAME.sub("-", value).strip("-")


@dataclass
class RunEvent:
    kind: str
    case_id: str
    detail: str = ""


@dataclass
class RunReport:
    started_at: datetime
    events: list[RunEvent] = field(default_factory=list)

    def add(self, kind: str, case_id: str, detail: str = "") -> None:
        self.events.append(RunEvent(kind, case_id, detail))

    def count(self, kind: str) -> int:
        return sum(1 for e in self.events if e.kind == kind)

    def summary(self) -> str:
        lines = [f"Training Gate run @ {self.started_at.isoformat(timespec='minutes')}"]
        lines += [f"  [{e.kind}] {e.case_id} {e.detail}".rstrip() for e in self.events]
        if not self.events:
            lines.append("  nothing to do")
        return "\n".join(lines)


class TrainingGate:
    def __init__(
        self,
        *,
        config: GateConfig,
        tracker: CaseTracker,
        portal: DocumentPortal,
        roster: TeamRoster,
        mailer: Mailer,
        chat: ChatNotifier,
        storage: DeckStorage,
        state: JsonStateStore,
        clock: Callable[[], datetime] = utc_now,
    ):
        self.config = config
        self.tracker = tracker
        self.portal = portal
        self.roster = roster
        self.mailer = mailer
        self.chat = chat
        self.storage = storage
        self.state = state
        self.clock = clock

    # ------------------------------------------------------------------ run

    def run(self) -> RunReport:
        now = self.clock()
        report = RunReport(started_at=now)
        for case in self.tracker.list_cases():
            try:
                self._evaluate_case(case, now, report)
            except Exception as exc:  # one bad case must not block the others
                report.add("error", case.case_id, f"{type(exc).__name__}: {exc}")
        self._collect_acknowledgements(now, report)
        self._send_reminders(now, report)
        self.state.save()
        return report

    # ------------------------------------------------- detection (part 1 + 2)

    def _is_expiring(self, case: Case, now: datetime) -> bool:
        if case.training_expires_on is None:
            return False
        horizon = now.date() + timedelta(days=self.config.renewal_window_days)
        return case.training_expires_on <= horizon

    def _evaluate_case(self, case: Case, now: datetime, report: RunReport) -> None:
        team = list(self.roster.team_for(case.case_id))
        targets: dict[str, tuple[TeamMember, Trigger]] = {}
        plan: PlanDocument | None = None

        # Part 1: training expiring soon -> look for a newly published document.
        if self._is_expiring(case, now):
            plan = self.portal.latest_plan(case.case_id)
            if plan is None:
                report.add("expiring_no_document", case.case_id)
            elif case.last_trained_on is not None and plan.published_on <= case.last_trained_on:
                report.add("expiring_awaiting_new_document", case.case_id, f"latest v{plan.version}")
            elif any(
                self.state.find(case.case_id, plan.document_id, plan.version, m.member_id)
                for m in team
            ):
                report.add("renewal_in_progress", case.case_id, f"v{plan.version}")
            else:
                for member in team:
                    targets[member.member_id] = (member, Trigger.EXPIRING_RENEWAL)

        # Part 2: anyone newly assigned to the team needs the current document.
        known = self.state.known_members(case.case_id)
        if known is None and self.config.baseline_on_first_run:
            report.add("baseline_recorded", case.case_id, f"{len(team)} member(s)")
        else:
            newcomers = [m for m in team if m.member_id not in (known or set())]
            if newcomers:
                plan = plan or self.portal.latest_plan(case.case_id)
                if plan is None:
                    report.add("new_member_no_document", case.case_id)
                else:
                    for member in newcomers:
                        targets.setdefault(member.member_id, (member, Trigger.NEW_TEAM_MEMBER))

        if targets and plan is not None:
            self._dispatch(case, plan, list(targets.values()), now, report)
        # Only remember the team once dispatch succeeded, so failures retry.
        self.state.set_known_members(case.case_id, {m.member_id for m in team})

    # ------------------------------------------------------------- delivery

    def _dispatch(
        self,
        case: Case,
        plan: PlanDocument,
        targets: Iterable[tuple[TeamMember, Trigger]],
        now: datetime,
        report: RunReport,
    ) -> None:
        pending = [
            (m, t)
            for m, t in targets
            if not self.state.find(case.case_id, plan.document_id, plan.version, m.member_id)
        ]
        if not pending:
            return

        keyword = self.config.acknowledgement_keyword
        deck = render_deck(case, plan, self.config.brand, keyword)
        deck_name = f"training-deck_{_safe(case.case_id)}_v{_safe(plan.version)}.html"
        deck_uri = self.storage.publish(deck_name, deck)
        deck_sha = hashlib.sha256(deck).hexdigest()
        source = self.portal.download(plan)
        supervisor = self.roster.supervisor_for(case.case_id)

        for member, trigger in pending:
            email = OutboundEmail(
                to=(member.email,),
                cc=(supervisor.email,) if supervisor else (),
                subject=f"Required training: {plan.title} ({case.display_name})",
                body=self._training_email_body(case, plan, member, trigger, deck_uri),
                attachments=(
                    Attachment(deck_name, deck, "text/html"),
                    Attachment(plan.filename, source, plan.media_type),
                ),
            )
            message_id = self.mailer.send(email)
            self.state.add(
                TrainingAssignment(
                    assignment_id=assignment_key(
                        case.case_id, plan.document_id, plan.version, member.member_id
                    ),
                    case_id=case.case_id,
                    case_display_name=case.display_name,
                    document_id=plan.document_id,
                    document_version=plan.version,
                    document_title=plan.title,
                    member=member,
                    supervisor=supervisor,
                    trigger=trigger,
                    deck_uri=deck_uri,
                    deck_sha256=deck_sha,
                    message_id=message_id,
                    sent_at=now,
                    history=[f"{now.isoformat()} sent ({trigger.value})"],
                )
            )
            report.add("training_sent", case.case_id, f"{member.member_id} ({trigger.value})")

    def _training_email_body(
        self, case: Case, plan: PlanDocument, member: TeamMember, trigger: Trigger, deck_uri: str
    ) -> str:
        reason = {
            Trigger.EXPIRING_RENEWAL: "the current training on file is expiring and an updated plan document was published",
            Trigger.NEW_TEAM_MEMBER: "you were recently added to this case's team",
        }[trigger]
        return (
            f"Hello {member.name},\n\n"
            f"You are receiving this training because {reason}.\n\n"
            f"Case: {case.display_name}\n"
            f"Document: {plan.title} (version {plan.version})\n"
            f"Slide deck: {deck_uri}\n\n"
            "Please review the attached slide deck and source document, then reply to this "
            f'email with "{self.config.acknowledgement_keyword.upper()}" on the first line to '
            "confirm completion. Your reply is recorded and filed as proof of training.\n\n"
            f"{self.config.brand.org_name}\n"
        )

    # ------------------------------------------------- acknowledgement + filing

    def _collect_acknowledgements(self, now: datetime, report: RunReport) -> None:
        keyword = self.config.acknowledgement_keyword
        for a in self.state.open_assignments():
            try:
                if a.status != AssignmentStatus.ACKNOWLEDGED:
                    reply = next(
                        (
                            r
                            for r in self.mailer.replies_to(a.message_id)
                            if r.sender.strip().lower() == a.member.email.lower()
                            and is_acknowledgement(r.body, keyword)
                        ),
                        None,
                    )
                    if reply is None:
                        continue
                    a.status = AssignmentStatus.ACKNOWLEDGED
                    a.acknowledged_at = reply.received_at
                    a.acknowledgement_excerpt = _first_line(reply.body)
                    a.history.append(f"{now.isoformat()} acknowledged")
                    report.add("acknowledged", a.case_id, a.member.member_id)
                self._file(a, now, report)
            except Exception as exc:
                report.add("error", a.case_id, f"{a.member.member_id}: {type(exc).__name__}: {exc}")

    def _file(self, a: TrainingAssignment, now: datetime, report: RunReport) -> None:
        pdf = render_attestation(a, self.config.brand, now)
        filename = (
            f"training-acknowledgment_{_safe(a.case_id)}_v{_safe(a.document_version)}"
            f"_{_safe(a.member.member_id)}.pdf"
        )
        a.filing_receipt = self.portal.upload_attestation(a.case_id, filename, pdf)
        a.filed_at = now
        a.status = AssignmentStatus.FILED
        a.history.append(f"{now.isoformat()} filed ({a.filing_receipt})")
        report.add("filed", a.case_id, f"{a.member.member_id} -> {a.filing_receipt}")

    # ------------------------------------------------------------- follow-up

    def _send_reminders(self, now: datetime, report: RunReport) -> None:
        due = timedelta(days=self.config.reminder_after_days)
        for a in self.state.open_assignments():
            if a.status != AssignmentStatus.SENT or now - a.sent_at < due:
                continue
            recipients = [a.member] + ([a.supervisor] if a.supervisor else [])
            text = (
                f"Reminder: training for {a.case_display_name} ({a.document_title}, "
                f"v{a.document_version}) is still awaiting acknowledgment from {a.member.name}. "
                f"Slide deck: {a.deck_uri}. Reply "
                f'"{self.config.acknowledgement_keyword.upper()}" to the original email once reviewed.'
            )
            try:
                self.chat.send(recipients, text)
            except Exception as exc:
                report.add("error", a.case_id, f"reminder {a.member.member_id}: {exc}")
                continue
            a.status = AssignmentStatus.REMINDED
            a.reminded_at = now
            a.history.append(f"{now.isoformat()} chat reminder sent")
            report.add("reminder_sent", a.case_id, a.member.member_id)
