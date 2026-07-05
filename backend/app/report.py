"""Exportable learning reports: a self-contained, printable HTML document
summarizing one quiz attempt.

Statelessness is the architecture rule here: the report is generated
entirely from the submitted answers in the request plus the currently
loaded pack — no accounts, no persistence, no new tables, no stored user
history. That keeps the no-auth constraint intact (there is nothing to
protect because nothing is kept), and it means the report is honest about
what it is: a snapshot the learner chooses to keep, produced locally.

Safety: every dynamic value — pack metadata, question text, option labels,
explanations, reference item titles, and the submitted values themselves —
passes through html.escape() before it touches the document. The output
embeds its own <style> and uses no external CSS, JS, fonts, or images, so
the file renders identically offline and prints cleanly.
"""
import html
from datetime import datetime, timezone

from sqlmodel import Session

from .models import PackMetadata, QuizQuestion, ReferenceItem


def _e(value) -> str:
    """Escape any value for safe embedding in HTML text or attributes."""
    return html.escape(str(value), quote=True)


def build_report_html(session: Session, answers: dict[str, int]) -> str:
    """Build the full report document. Raises KeyError for unknown question
    ids (the router maps that to a 400, mirroring /quiz/submit)."""
    meta = session.get(PackMetadata, 1)

    rows = []
    score = 0
    for qid, selected in answers.items():
        q = session.get(QuizQuestion, qid)
        if q is None:
            raise KeyError(qid)
        correct = selected == q.correct_index
        score += correct

        if isinstance(selected, int) and 0 <= selected < len(q.options):
            submitted_label = q.options[selected]
        else:
            submitted_label = f"(option {selected} — not a valid choice)"
        correct_label = q.options[q.correct_index]

        related = session.get(ReferenceItem, q.source_item_id)
        related_html = (
            f'<p class="related">Related reference: {_e(related.title)}'
            f' <span class="muted">(#/item/{_e(related.id)} in the app)</span></p>'
            if related else ""
        )

        status_cls = "ok" if correct else "bad"
        status_txt = "Correct" if correct else "Incorrect"
        rows.append(f"""
    <section class="question">
      <h3>{_e(q.question)}</h3>
      <p><span class="badge {status_cls}">{status_txt}</span></p>
      <p><strong>Your answer:</strong> {_e(submitted_label)}</p>
      <p><strong>Correct answer:</strong> {_e(correct_label)}</p>
      <p class="explanation"><strong>Explanation:</strong> {_e(q.explanation)}</p>
      {related_html}
    </section>""")

    total = len(answers)
    percent = round(100 * score / total) if total else 0
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    pack_block = (
        f"""
      <p class="packline">
        Content pack: <strong>{_e(meta.pack_name)}</strong>
        <span class="muted">({_e(meta.pack_id)} · v{_e(meta.pack_version)} · {_e(meta.domain_type)})</span>
      </p>
      <p class="disclaimer">{_e(meta.safety_notes)}</p>"""
        if meta else
        '<p class="disclaimer">Synthetic demo content only.</p>'
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>NavigatorEdu — Quiz Learning Report</title>
<style>
  /* Self-contained: no external assets. Print-first, screen-friendly. */
  body {{ font-family: Georgia, 'Times New Roman', serif; color: #1a2432;
         max-width: 46rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.55; }}
  h1 {{ font-size: 1.5rem; color: #12314f; margin-bottom: 0.25rem; }}
  h2 {{ font-size: 1.1rem; color: #12314f; border-bottom: 2px solid #e2e8f0;
        padding-bottom: 0.25rem; margin-top: 2rem; }}
  h3 {{ font-size: 1rem; color: #12314f; margin-bottom: 0.4rem; }}
  .muted {{ color: #64748b; font-size: 0.85em; }}
  .packline {{ margin: 0.2rem 0; }}
  .disclaimer {{ background: #f4f6f8; border-left: 3px solid #b98a2f;
                 padding: 0.6rem 0.9rem; font-size: 0.9rem; color: #475569; }}
  .scorebox {{ border: 1px solid #e2e8f0; border-radius: 6px;
               padding: 0.8rem 1rem; margin: 1rem 0; }}
  .scorebox .big {{ font-size: 1.6rem; color: #12314f; font-weight: bold; }}
  .question {{ border: 1px solid #e2e8f0; border-radius: 6px;
               padding: 0.9rem 1.1rem; margin: 0.9rem 0;
               page-break-inside: avoid; }}
  .question p {{ margin: 0.3rem 0; }}
  .badge {{ display: inline-block; font-size: 0.75rem; font-weight: bold;
            padding: 0.1rem 0.6rem; border-radius: 999px; }}
  .badge.ok  {{ background: #ecfdf5; color: #047857; border: 1px solid #047857; }}
  .badge.bad {{ background: #fef2f2; color: #b91c1c; border: 1px solid #b91c1c; }}
  .explanation {{ color: #334155; }}
  .related {{ font-size: 0.9rem; }}
  footer {{ margin-top: 2rem; padding-top: 0.8rem; border-top: 1px solid #e2e8f0;
            font-size: 0.8rem; color: #64748b; }}
  @media print {{
    body {{ margin: 0.5in; max-width: none; }}
    .question {{ break-inside: avoid; }}
  }}
</style>
</head>
<body>
  <header>
    <h1>NavigatorEdu — Quiz Learning Report</h1>
    <p class="muted">Synthetic content-pack education platform · portfolio demo</p>
    {pack_block}
  </header>

  <div class="scorebox">
    <p class="big">{score} / {total} ({percent}%)</p>
    <p class="muted">{total} question{"s" if total != 1 else ""} answered · {score} correct</p>
  </div>

  <h2>Questions</h2>
  {"".join(rows) if rows else '<p class="muted">No answers were submitted.</p>'}

  <footer>
    <p>Generated locally from submitted answers; not stored.</p>
    <p>Generated {generated} · All content is fictional and synthetic — educational
       demonstration only, not for real-world, operational, or clinical use.</p>
  </footer>
</body>
</html>
"""
