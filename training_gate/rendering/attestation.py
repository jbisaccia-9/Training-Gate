"""Acknowledgment record as a dependency-free, single-page PDF."""

from __future__ import annotations

import textwrap
from datetime import datetime

from ..config import BrandTheme
from ..models import TrainingAssignment

WRAP_AT = 88
MAX_LINES = 46


def _pdf_text(value: str) -> str:
    latin = value.encode("latin-1", "replace").decode("latin-1")
    return latin.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _hex_to_rgb(color: str) -> str:
    r, g, b = (int(color[i : i + 2], 16) / 255 for i in (1, 3, 5))
    return f"{r:.3f} {g:.3f} {b:.3f}"


def attestation_lines(a: TrainingAssignment, generated_at: datetime) -> list[tuple[str, str]]:
    def stamp(value: datetime | None) -> str:
        return value.isoformat(timespec="minutes") if value else "n/a"

    rows = [
        ("Case", a.case_display_name),
        ("Case reference", a.case_id),
        ("Document", a.document_title),
        ("Document reference", f"{a.document_id} (version {a.document_version})"),
        ("Trainee", f"{a.member.name} <{a.member.email}>"),
        ("Supervisor copied", a.supervisor.name if a.supervisor else "n/a"),
        ("Reason assigned", a.trigger.value.replace("_", " ")),
        ("Training sent", stamp(a.sent_at)),
        ("Reminder sent", stamp(a.reminded_at)),
        ("Acknowledged", stamp(a.acknowledged_at)),
        ("Acknowledgment text", a.acknowledgement_excerpt or ""),
        ("Training deck SHA-256", a.deck_sha256),
        ("Assignment id", a.assignment_id),
        ("Record generated", stamp(generated_at)),
    ]
    lines: list[tuple[str, str]] = []
    for label, value in rows:
        wrapped = textwrap.wrap(f"{label}: {value}", WRAP_AT) or [f"{label}:"]
        lines.extend(("body", w) for w in wrapped)
    return lines[:MAX_LINES]


def render_attestation(
    a: TrainingAssignment, brand: BrandTheme, generated_at: datetime
) -> bytes:
    ops = [
        f"{_hex_to_rgb(brand.primary_color)} rg 0 742 612 50 re f",
        "BT 1 1 1 rg /F2 18 Tf 54 760 Td",
        f"({_pdf_text(brand.org_name)}) Tj ET",
        f"BT {_hex_to_rgb(brand.text_color)} rg /F2 15 Tf 54 712 Td",
        "(Training Acknowledgment Record) Tj ET",
        f"BT {_hex_to_rgb(brand.text_color)} rg /F1 10.5 Tf 15 TL 54 684 Td",
    ]
    for _, text in attestation_lines(a, generated_at):
        ops.append(f"({_pdf_text(text)}) Tj T*")
    ops.append("ET")
    ops.append(f"BT 0.4 0.4 0.4 rg /F1 8 Tf 54 40 Td ({_pdf_text(brand.footer_text)}) Tj ET")
    stream = "\n".join(ops).encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode()
    return bytes(out)
