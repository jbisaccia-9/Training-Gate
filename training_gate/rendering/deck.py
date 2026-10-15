"""Branded, self-contained HTML slide deck built from a plan document.

The output is a single HTML file with no external requests: it opens in any
browser, prints one slide per page, and can be attached to an email or linked
from a chat message.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

from ..config import BrandTheme
from ..models import Case, PlanDocument

MAX_BULLETS_PER_SLIDE = 6


@dataclass(frozen=True)
class Slide:
    heading: str
    bullets: tuple[str, ...] = ()
    kicker: str = ""


def build_slides(case: Case, plan: PlanDocument, keyword: str) -> list[Slide]:
    slides = [
        Slide(
            heading=plan.title,
            kicker="Required training",
            bullets=(
                f"Case: {case.display_name}",
                f"Document version {plan.version}, published {plan.published_on.isoformat()}",
            ),
        )
    ]
    for section in plan.sections:
        chunks = [
            section.bullets[i : i + MAX_BULLETS_PER_SLIDE]
            for i in range(0, max(len(section.bullets), 1), MAX_BULLETS_PER_SLIDE)
        ]
        for index, chunk in enumerate(chunks):
            heading = section.heading if index == 0 else f"{section.heading} (cont.)"
            slides.append(Slide(heading=heading, bullets=tuple(chunk)))
    slides.append(
        Slide(
            heading="Confirm completion",
            kicker="Next step",
            bullets=(
                f'Reply to the training email with "{keyword.upper()}" on the first line.',
                "Your reply generates a dated acknowledgment record that is filed automatically.",
                "Questions about the content? Ask your supervisor before replying.",
            ),
        )
    )
    return slides


def render_deck(case: Case, plan: PlanDocument, brand: BrandTheme, keyword: str) -> bytes:
    slides = build_slides(case, plan, keyword)
    total = len(slides)
    sections = []
    for number, slide in enumerate(slides, start=1):
        bullets = "".join(f"<li>{escape(b)}</li>" for b in slide.bullets)
        kicker = f'<p class="kicker">{escape(slide.kicker)}</p>' if slide.kicker else ""
        cls = "slide title" if number == 1 else "slide"
        sections.append(
            f'<section class="{cls}" data-n="{number}">'
            f"{kicker}<h1>{escape(slide.heading)}</h1><ul>{bullets}</ul>"
            f'<footer><span>{escape(brand.org_name)} · {escape(brand.footer_text)}</span>'
            f"<span>{number} / {total}</span></footer></section>"
        )

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(plan.title)} | {escape(brand.org_name)}</title>
<style>
  :root {{
    --primary: {brand.primary_color};
    --accent: {brand.accent_color};
    --bg: {brand.background_color};
    --text: {brand.text_color};
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; height: 100%; background: #2b2b2b; font-family: {brand.font_family}; }}
  .slide {{
    display: none; position: relative; width: min(100vw, 177.78vh); aspect-ratio: 16 / 9;
    margin: auto; background: var(--bg); color: var(--text); padding: 6% 7% 8%;
    border-top: 1.2vh solid var(--primary); overflow: hidden;
  }}
  .slide.active {{ display: block; }}
  .slide h1 {{ color: var(--primary); font-size: clamp(20px, 4.2vh, 44px); margin: 0 0 3%; }}
  .slide ul {{ font-size: clamp(14px, 2.8vh, 28px); line-height: 1.5; padding-left: 1.2em; }}
  .slide li::marker {{ color: var(--accent); }}
  .kicker {{ color: var(--accent); text-transform: uppercase; letter-spacing: .12em;
            font-weight: 700; font-size: clamp(11px, 1.8vh, 18px); margin: 0 0 1%; }}
  .title {{ background: var(--primary); color: #fff; border-top-color: var(--accent); }}
  .title h1 {{ color: #fff; font-size: clamp(26px, 6vh, 64px); margin-top: 8%; }}
  footer {{ position: absolute; left: 7%; right: 7%; bottom: 4%; display: flex;
           justify-content: space-between; font-size: clamp(10px, 1.5vh, 14px); opacity: .75; }}
  .hint {{ color: #bbb; text-align: center; font-size: 12px; padding: 8px; }}
  @media print {{
    body {{ background: none; }}
    .slide {{ display: block; width: 100%; page-break-after: always; }}
    .hint {{ display: none; }}
  }}
</style>
</head>
<body>
{"".join(sections)}
<p class="hint">Use ← → (or click) to move between slides. Print to save every slide.</p>
<script>
  const slides = Array.from(document.querySelectorAll('.slide'));
  let i = 0;
  const show = n => {{ i = Math.max(0, Math.min(slides.length - 1, n));
    slides.forEach((s, k) => s.classList.toggle('active', k === i)); }};
  document.addEventListener('keydown', e => {{
    if (['ArrowRight', 'PageDown', ' '].includes(e.key)) show(i + 1);
    if (['ArrowLeft', 'PageUp'].includes(e.key)) show(i - 1);
  }});
  document.addEventListener('click', e => show(e.clientX > innerWidth / 2 ? i + 1 : i - 1));
  show(0);
</script>
</body>
</html>
"""
    return html.encode("utf-8")
