"""SQLite FTS5 search index for reference items.

Design: a standalone FTS5 virtual table (`item_fts`) rebuilt from scratch by
`rebuild_fts()` at the end of every seed. Because seeding is clear-then-load
and is the *only* write path for content (CLI, SEED_PATH, and the pack
browser's POST /packs/select all call the same `seed()`), rebuild-at-seed
keeps the index exactly in sync with the loaded pack — no triggers, no
incremental-update bookkeeping, and stale search results across pack
switches are structurally impossible.

Indexed columns: title, summary, body_md, and the space-joined tags (so a
query can match tag words, preserving the pre-FTS behavior). `item_id` is
stored UNINDEXED for joining back to the ORM rows.

Query semantics: user input is tokenized on whitespace, each token is
phrase-quoted (so FTS5 operators like OR/NEAR/- in user input are inert),
and the final token gets a `*` prefix wildcard — typing "prob" finds
"probe". Matching is case-insensitive via FTS5's default unicode61
tokenizer. This is a deliberate semantic change from the old linear scan
(token/prefix matching rather than arbitrary substring), which is standard
search behavior and what an index can serve at scale.

Safety fallback (documented per the milestone requirements): if the FTS
table doesn't exist — possible only on a database that has never been
seeded, since every seed creates it — `search_item_ids` returns no matches
instead of raising. That is the entire fallback; there is no secondary
search implementation.

Scope note: this is local demo search over synthetic packs — the point is
demonstrating the upgrade path named in the code since v02, not production
search infrastructure (no ranking tuning, no highlighting, no analyzers).
"""
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, select

from .models import ReferenceItem

FTS_TABLE = "item_fts"


def rebuild_fts(session: Session) -> int:
    """Drop and rebuild the FTS index from the reference items in `session`.

    Called by seed() after content is loaded (autoflush makes pending rows
    visible to the SELECT). Returns the number of rows indexed.
    """
    session.execute(text(f"DROP TABLE IF EXISTS {FTS_TABLE}"))
    session.execute(text(
        f"CREATE VIRTUAL TABLE {FTS_TABLE} "
        "USING fts5(item_id UNINDEXED, title, summary, body_md, tags)"
    ))
    items = session.exec(select(ReferenceItem)).all()
    for item in items:
        session.execute(
            text(
                f"INSERT INTO {FTS_TABLE} (item_id, title, summary, body_md, tags) "
                "VALUES (:item_id, :title, :summary, :body_md, :tags)"
            ),
            {
                "item_id": item.id,
                "title": item.title,
                "summary": item.summary,
                "body_md": item.body_md,
                "tags": " ".join(item.tags),
            },
        )
    return len(items)


def _fts_match_expression(q: str) -> str | None:
    """Turn raw user input into a safe FTS5 MATCH expression.

    Each whitespace token is phrase-quoted (embedded double quotes doubled),
    which neutralizes FTS5 query syntax in user input; the last token gets a
    prefix wildcard. Returns None when the input has no usable tokens — the
    caller treats that as "no query supplied".
    """
    tokens = [t.replace('"', '""') for t in q.split() if t.strip('"')]
    if not tokens:
        return None
    quoted = [f'"{t}"' for t in tokens]
    quoted[-1] += "*"
    return " ".join(quoted)


def search_item_ids(session: Session, q: str) -> list[str] | None:
    """Item IDs matching `q`, best match first (FTS5 bm25 rank).

    Returns None when the query has no usable tokens (treat as no filter),
    and [] when nothing matches — including the never-seeded-database
    fallback described in the module docstring.
    """
    match = _fts_match_expression(q)
    if match is None:
        return None
    try:
        rows = session.execute(
            text(
                f"SELECT item_id FROM {FTS_TABLE} "
                f"WHERE {FTS_TABLE} MATCH :match ORDER BY rank"
            ),
            {"match": match},
        ).all()
    except OperationalError:
        return []  # FTS table absent: DB was never seeded, so no content anyway
    return [row[0] for row in rows]
