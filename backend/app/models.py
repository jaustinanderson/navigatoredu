"""SQLModel table definitions.

List-valued fields (tags, options, guided_steps, ...) are stored as JSON
columns — the simplest correct choice for SQLite and easy to migrate to
proper join tables later if needed.
"""
from sqlmodel import JSON, Column, Field, SQLModel


class Category(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    slug: str = Field(index=True)
    description: str
    parent_id: str | None = Field(default=None, foreign_key="category.id")


class Disclaimer(SQLModel, table=True):
    id: str = Field(primary_key=True)
    applies_to: str
    text: str


class ReferenceItem(SQLModel, table=True):
    id: str = Field(primary_key=True)
    category_id: str = Field(foreign_key="category.id", index=True)
    title: str
    summary: str
    body_md: str
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    difficulty: str
    disclaimer_id: str = Field(foreign_key="disclaimer.id")
    is_synthetic: bool = True


class TrainingNote(SQLModel, table=True):
    id: str = Field(primary_key=True)
    module: str
    order: int
    title: str
    body_md: str
    related_item_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON))


class PracticeCase(SQLModel, table=True):
    id: str = Field(primary_key=True)
    category_id: str = Field(foreign_key="category.id", index=True)
    title: str
    scenario_md: str
    guided_steps: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    expected_outcome_md: str
    difficulty: str
    is_synthetic: bool = True


class QuizQuestion(SQLModel, table=True):
    id: str = Field(primary_key=True)
    category_id: str = Field(foreign_key="category.id", index=True)
    question: str
    options: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    correct_index: int
    explanation: str
    source_item_id: str = Field(foreign_key="referenceitem.id")


class PackMetadata(SQLModel, table=True):
    """Single-row table describing the content pack currently loaded in the DB.

    Storing metadata in the database (rather than re-reading SEED_PATH at
    request time) means the API reports exactly what was seeded, survives
    restarts, and stays consistent with every other endpoint's data source.
    The fixed primary key enforces the single-row invariant via upsert.
    """
    id: int = Field(default=1, primary_key=True)
    pack_id: str
    pack_name: str
    pack_version: str
    pack_description: str
    domain_type: str
    synthetic_only: bool
    intended_use: str
    safety_notes: str
