"""Command line entry points: `demo` (synthetic walkthrough) and `run` (scheduled job)."""

from __future__ import annotations

import argparse
import importlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .adapters.fixture import build_adapters, load_fixture
from .config import GateConfig, load_config
from .engine import TrainingGate
from .state import JsonStateStore

DEFAULT_FIXTURE = Path(__file__).resolve().parent.parent / "examples" / "synthetic_cases.json"


def _import(target: str):
    module, _, attr = target.partition(":")
    return getattr(importlib.import_module(module), attr)


def cmd_run(args: argparse.Namespace) -> int:
    app = load_config(args.config)
    adapters = _import(app.wiring)(**app.wiring_options)
    gate = TrainingGate(
        config=app.gate,
        state=JsonStateStore(app.gate.state_path),
        **vars(adapters),
    )
    report = gate.run()
    print(report.summary())
    return 1 if report.count("error") else 0


def cmd_demo(args: argparse.Namespace) -> int:
    """Simulate three scheduled runs over eight days against synthetic data."""
    out = Path(args.out)
    adapters = build_adapters(str(args.fixture), deck_dir=str(out / "decks"))
    world = load_fixture(args.fixture)
    start = datetime(2026, 3, 2, 13, 0, tzinfo=timezone.utc)
    clock = {"now": start}
    gate = TrainingGate(
        config=GateConfig(state_path=str(out / "state.json")),
        state=JsonStateStore(),
        clock=lambda: clock["now"],
        **vars(adapters),
    )

    def run(label: str) -> None:
        print(f"\n=== {label} ===")
        print(gate.run().summary())

    run("Day 0: first scheduled run")

    clock["now"] = start + timedelta(days=1)
    adapters.roster.teams["CASE-1002"].append(world["people"]["TM-D"])
    adapters.mailer.simulate_reply(
        "member.a@example.com", "Reviewed - thank you.\n\n> original message", clock["now"]
    )
    print("\n(Team Member D joins Case Bravo; Team Member A replies 'Reviewed')")
    run("Day 1")

    clock["now"] = start + timedelta(days=8)
    adapters.mailer.simulate_reply("member.d@example.com", "REVIEWED", clock["now"])
    print("\n(Team Member D replies 'REVIEWED'; Team Member B has not replied)")
    run("Day 8")

    gate.state.path = out / "state.json"
    gate.state.save()
    (out / "attestations").mkdir(parents=True, exist_ok=True)
    for _, filename, content in adapters.portal.uploads:
        (out / "attestations" / filename).write_bytes(content)
    with open(out / "chat-log.txt", "w") as fh:
        for handles, text in adapters.chat.messages:
            fh.write(f"to {', '.join(handles)}: {text}\n")
    with open(out / "outbox.txt", "w") as fh:
        for message_id, email in adapters.mailer.sent.items():
            names = ", ".join(a.filename for a in email.attachments)
            fh.write(
                f"--- {message_id}\nTo: {', '.join(email.to)}\nCc: {', '.join(email.cc)}\n"
                f"Subject: {email.subject}\nAttachments: {names}\n\n{email.body}\n"
            )
    print(f"\nOutputs written to {out.resolve()}/ (decks/, attestations/, outbox.txt, chat-log.txt, state.json)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="training-gate", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="walk through a synthetic scenario")
    demo.add_argument("--fixture", default=DEFAULT_FIXTURE)
    demo.add_argument("--out", default="out")
    demo.set_defaults(func=cmd_demo)

    run = sub.add_parser("run", help="perform one scheduled run")
    run.add_argument("--config", required=True)
    run.set_defaults(func=cmd_run)

    args = parser.parse_args(argv)
    return args.func(args)
