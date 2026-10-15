"""Configuration, loadable from TOML."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path

_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
_FONT_FAMILY = re.compile(r"^[\w\s,\-'\"]+$")


@dataclass(frozen=True)
class BrandTheme:
    """Look and feel of generated decks and attestation records."""

    org_name: str = "Example Organization"
    primary_color: str = "#1F4E79"
    accent_color: str = "#F2A900"
    background_color: str = "#FFFFFF"
    text_color: str = "#1A1A1A"
    font_family: str = "'Segoe UI', Helvetica, Arial, sans-serif"
    footer_text: str = "Internal training material. Do not forward."

    def __post_init__(self) -> None:
        for name in ("primary_color", "accent_color", "background_color", "text_color"):
            if not _HEX_COLOR.match(getattr(self, name)):
                raise ValueError(f"brand.{name} must be a #RRGGBB hex color")
        if not _FONT_FAMILY.match(self.font_family):
            raise ValueError("brand.font_family contains unsupported characters")


@dataclass(frozen=True)
class GateConfig:
    renewal_window_days: int = 30
    reminder_after_days: int = 7
    acknowledgement_keyword: str = "reviewed"
    # On the first run for a case, record the current team without training
    # anyone, so turning the tool on doesn't email every existing member.
    baseline_on_first_run: bool = True
    state_path: str = ".training-gate/state.json"
    brand: BrandTheme = field(default_factory=BrandTheme)


@dataclass(frozen=True)
class AppConfig:
    gate: GateConfig
    wiring: str
    wiring_options: dict


def _pick(cls, data: dict) -> dict:
    allowed = {f.name for f in fields(cls)}
    unknown = set(data) - allowed
    if unknown:
        raise ValueError(f"Unknown {cls.__name__} keys: {sorted(unknown)}")
    return data


def load_config(path: Path | str) -> AppConfig:
    raw = tomllib.loads(Path(path).read_text())
    brand = BrandTheme(**_pick(BrandTheme, raw.get("brand", {})))
    gate = GateConfig(**_pick(GateConfig, raw.get("gate", {})), brand=brand)
    adapters = raw.get("adapters", {})
    if "wiring" not in adapters:
        raise ValueError("[adapters] wiring = 'module:function' is required")
    return AppConfig(gate=gate, wiring=adapters["wiring"], wiring_options=adapters.get("options", {}))
