#!/usr/bin/env python3
"""Fail if tracked files look like they contain personal or private information.

Checks every git-tracked text file for:
  * SSN-shaped numbers and US phone numbers
  * email addresses outside reserved example domains
  * record-identifier keywords that should never appear in a public repo
  * any term in a local, untracked denylist (.pii-denylist) or the
    PII_DENYLIST environment variable (comma separated). Put your real
    employer, client, vendor, and system names there; they stay off GitHub.

Usage: python scripts/pii_scan.py [paths...]
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOWED_EMAIL_DOMAINS = re.compile(r"@(example\.(com|org|net)|anthropic\.com)$", re.IGNORECASE)

PATTERNS = {
    "ssn-like number": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "phone number": re.compile(r"(?<![\w-])\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b"),
    "email address": re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+"),
    "record identifier keyword": re.compile(
        r"\b(date\s+of\s+birth|d\.?o\.?b\.?:|medical\s+record\s+(number|no)|mrn\s*[:#]|"
        r"social\s+security|member\s+id\s*[:#]|policy\s+(number|no)\s*[:#])",
        re.IGNORECASE,
    ),
}


def tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
    ).stdout.decode()
    return [ROOT / p for p in out.split("\0") if p]


def denylist() -> list[str]:
    terms = [t.strip() for t in os.environ.get("PII_DENYLIST", "").split(",")]
    path = ROOT / ".pii-denylist"
    if path.exists():
        terms += [line.strip() for line in path.read_text().splitlines()]
    return [t for t in terms if t and not t.startswith("#")]


def scan(paths: list[Path]) -> list[str]:
    private = [(t, re.compile(rf"\b{re.escape(t)}\b", re.IGNORECASE)) for t in denylist()]
    findings = []
    for path in paths:
        if path.resolve() == Path(__file__).resolve():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue
        rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        for number, line in enumerate(text.splitlines(), start=1):
            for label, pattern in PATTERNS.items():
                for match in pattern.finditer(line):
                    if label == "email address" and ALLOWED_EMAIL_DOMAINS.search(match.group()):
                        continue
                    findings.append(f"{rel}:{number}: {label}")
            for _, pattern in private:
                if pattern.search(line):
                    # Never echo the private term itself into CI logs.
                    findings.append(f"{rel}:{number}: denylisted term")
    return findings


def main(argv: list[str]) -> int:
    paths = [Path(p).resolve() for p in argv] or tracked_files()
    findings = scan(paths)
    for finding in findings:
        print(finding)
    print(f"pii-scan: {len(paths)} file(s) checked, {len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
