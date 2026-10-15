import json
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from training_gate import GateConfig, JsonStateStore, TrainingGate, is_acknowledgement
from training_gate.adapters.memory import (
    InMemoryCaseTracker,
    InMemoryChat,
    InMemoryMailer,
    InMemoryPortal,
    InMemoryRoster,
    InMemoryStorage,
)
from training_gate.models import AssignmentStatus, Case, PlanDocument, PlanSection, TeamMember

T0 = datetime(2026, 3, 2, 13, 0, tzinfo=timezone.utc)
A = TeamMember("TM-A", "Team Member A", "member.a@example.com", "@a")
B = TeamMember("TM-B", "Team Member B", "member.b@example.com", "@b")
C = TeamMember("TM-C", "Team Member C", "member.c@example.com", "@c")
SUP = TeamMember("SUP-1", "Supervisor One", "supervisor.one@example.com", "@sup")


def plan(case_id="CASE-1", version="2", published=date(2026, 2, 20)):
    return PlanDocument(
        case_id=case_id,
        document_id=f"DOC-{case_id}",
        version=version,
        title="Service Plan",
        published_on=published,
        sections=(PlanSection("Goals", ("Goal 1: placeholder.",)),),
    )


class Harness:
    def __init__(self, cases, plans, teams, config=None, state=None):
        self.now = T0
        self.tracker = InMemoryCaseTracker(cases)
        self.portal = InMemoryPortal(plans)
        self.roster = InMemoryRoster(teams, {c.case_id: SUP for c in cases})
        self.mailer = InMemoryMailer()
        self.chat = InMemoryChat()
        self.storage = InMemoryStorage()
        self.state = state or JsonStateStore()
        self.gate = TrainingGate(
            config=config or GateConfig(),
            tracker=self.tracker,
            portal=self.portal,
            roster=self.roster,
            mailer=self.mailer,
            chat=self.chat,
            storage=self.storage,
            state=self.state,
            clock=lambda: self.now,
        )

    def run(self, days=0):
        self.now = T0 + timedelta(days=days)
        return self.gate.run()


EXPIRING = Case("CASE-1", "Case One", date(2026, 3, 20), last_trained_on=date(2025, 3, 15))
NOT_EXPIRING = Case("CASE-2", "Case Two", date(2026, 12, 1), last_trained_on=date(2025, 12, 1))


class DetectionTests(unittest.TestCase):
    def test_expiring_case_with_new_document_trains_whole_team(self):
        h = Harness([EXPIRING], [plan()], {"CASE-1": [A, B]})
        report = h.run()
        self.assertEqual(report.count("training_sent"), 2)
        sent = list(h.mailer.sent.values())
        self.assertEqual({e.to[0] for e in sent}, {A.email, B.email})
        self.assertTrue(all(e.cc == (SUP.email,) for e in sent))
        self.assertEqual(len(h.storage.files), 1)
        self.assertEqual([a.filename for a in sent[0].attachments][1], "plan-document.pdf")

    def test_expiring_case_without_newer_document_waits(self):
        old = plan(published=date(2025, 3, 1))
        h = Harness([EXPIRING], [old], {"CASE-1": [A]})
        report = h.run()
        self.assertEqual(report.count("training_sent"), 0)
        self.assertEqual(report.count("expiring_awaiting_new_document"), 1)

    def test_case_outside_window_is_left_alone(self):
        h = Harness([NOT_EXPIRING], [plan("CASE-2")], {"CASE-2": [A]})
        self.assertEqual(h.run().count("training_sent"), 0)

    def test_first_run_baselines_team_then_trains_only_newcomers(self):
        h = Harness([NOT_EXPIRING], [plan("CASE-2")], {"CASE-2": [A]})
        self.assertEqual(h.run().count("baseline_recorded"), 1)
        h.roster.teams["CASE-2"].append(C)
        report = h.run(days=1)
        self.assertEqual(report.count("training_sent"), 1)
        self.assertEqual(list(h.mailer.sent.values())[0].to, (C.email,))

    def test_baseline_can_be_disabled(self):
        h = Harness(
            [NOT_EXPIRING], [plan("CASE-2")], {"CASE-2": [A]},
            config=GateConfig(baseline_on_first_run=False),
        )
        self.assertEqual(h.run().count("training_sent"), 1)

    def test_runs_are_idempotent(self):
        h = Harness([EXPIRING], [plan()], {"CASE-1": [A, B]})
        h.run()
        report = h.run()
        self.assertEqual(report.count("training_sent"), 0)
        self.assertEqual(report.count("renewal_in_progress"), 1)
        self.assertEqual(len(h.mailer.sent), 2)

    def test_newer_version_triggers_a_new_round(self):
        h = Harness([EXPIRING], [plan()], {"CASE-1": [A]})
        h.run()
        h.portal.publish(plan(version="3", published=date(2026, 3, 1)))
        self.assertEqual(h.run(days=1).count("training_sent"), 1)

    def test_one_failing_case_does_not_stop_the_run(self):
        h = Harness([EXPIRING, NOT_EXPIRING], [plan()], {"CASE-1": [A], "CASE-2": [B]})
        h.roster.team_for = lambda cid: (_ for _ in ()).throw(RuntimeError("boom")) if cid == "CASE-2" else [A]
        report = h.run()
        self.assertEqual(report.count("error"), 1)
        self.assertEqual(report.count("training_sent"), 1)


class AcknowledgementTests(unittest.TestCase):
    def setUp(self):
        self.h = Harness([EXPIRING], [plan()], {"CASE-1": [A, B]})
        self.h.run()

    def test_reviewed_reply_files_pdf_attestation(self):
        self.h.mailer.simulate_reply(A.email, "Reviewed, thanks!", T0 + timedelta(hours=3))
        report = self.h.run(days=1)
        self.assertEqual(report.count("filed"), 1)
        case_id, filename, pdf = self.h.portal.uploads[0]
        self.assertEqual(case_id, "CASE-1")
        self.assertTrue(filename.endswith("_TM-A.pdf"))
        self.assertTrue(pdf.startswith(b"%PDF-1.4") and pdf.rstrip().endswith(b"%%EOF"))
        self.assertIn(b"Team Member A", pdf)

    def test_reply_from_someone_else_does_not_count(self):
        message_id = next(m for m, e in self.h.mailer.sent.items() if A.email in e.to)
        from training_gate.models import Reply

        self.h.mailer.replies[message_id].append(Reply(SUP.email, "Reviewed", T0))
        self.assertEqual(self.h.run(days=1).count("filed"), 0)

    def test_filing_failure_is_retried_next_run(self):
        self.h.mailer.simulate_reply(A.email, "Reviewed", T0)
        upload = self.h.portal.upload_attestation
        self.h.portal.upload_attestation = lambda *a: (_ for _ in ()).throw(OSError("portal down"))
        report = self.h.run(days=1)
        self.assertEqual(report.count("acknowledged"), 1)
        self.assertEqual(report.count("error"), 1)
        self.h.portal.upload_attestation = upload
        self.assertEqual(self.h.run(days=2).count("filed"), 1)


class ReminderTests(unittest.TestCase):
    def test_single_chat_reminder_after_a_week(self):
        h = Harness([EXPIRING], [plan()], {"CASE-1": [A]})
        h.run()
        self.assertEqual(h.run(days=6).count("reminder_sent"), 0)
        self.assertEqual(h.run(days=7).count("reminder_sent"), 1)
        self.assertEqual(h.run(days=8).count("reminder_sent"), 0)
        handles, text = h.chat.messages[0]
        self.assertEqual(handles, ("@a", "@sup"))
        self.assertIn("memory://decks/", text)

    def test_acknowledgement_after_reminder_still_files(self):
        h = Harness([EXPIRING], [plan()], {"CASE-1": [A]})
        h.run()
        h.run(days=7)
        h.mailer.simulate_reply(A.email, "reviewed", T0 + timedelta(days=9))
        self.assertEqual(h.run(days=9).count("filed"), 1)
        assignment = next(iter(h.state.assignments.values()))
        self.assertEqual(assignment.status, AssignmentStatus.FILED)
        self.assertIsNotNone(assignment.reminded_at)


class KeywordTests(unittest.TestCase):
    def test_keyword_matching(self):
        yes = ["Reviewed", "REVIEWED - thank you", "\n\n  reviewed.\n> old text"]
        no = ["not reviewed yet", "I have not", "> Reviewed", "", "On Mon, X wrote:\nReviewed", "Reviewedish"]
        for body in yes:
            self.assertTrue(is_acknowledgement(body, "reviewed"), body)
        for body in no:
            self.assertFalse(is_acknowledgement(body, "reviewed"), body)


class StateTests(unittest.TestCase):
    def test_state_round_trips_to_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            h = Harness([EXPIRING], [plan()], {"CASE-1": [A]}, state=JsonStateStore(path))
            h.run()
            reloaded = JsonStateStore(path)
            self.assertEqual(len(reloaded.assignments), 1)
            self.assertEqual(reloaded.known_members("CASE-1"), {"TM-A"})
            self.assertEqual(json.loads(path.read_text())["schema_version"], 1)


if __name__ == "__main__":
    unittest.main()
