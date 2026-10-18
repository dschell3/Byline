"""Shape checks on the models. No database needed, so these run in CI as is."""

from sqlalchemy import DateTime
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

import models  # noqa: F401  (importing registers every table on Base.metadata)
from db import Base

EXPECTED_TABLES = {
    "organization",
    "person",
    "membership",
    "team",
    "cohort",
    "track",
    "assignment",
    "submission",
    "review",
    "points_ledger",
    "notification",
    "audit_log",
}


def test_all_twelve_tables_are_defined() -> None:
    """The ERD's twelve tables, no more, no fewer."""
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_every_timestamp_is_timezone_aware() -> None:
    """The ERD rule: TIMESTAMPTZ everywhere, no naive datetimes."""
    naive = [
        f"{table.name}.{column.name}"
        for table in Base.metadata.tables.values()
        for column in table.columns
        if isinstance(column.type, DateTime) and not column.type.timezone
    ]
    assert naive == []


def test_schema_compiles_for_postgres() -> None:
    """Every CREATE TABLE renders against the Postgres dialect."""
    for table in Base.metadata.sorted_tables:
        ddl = str(CreateTable(table).compile(dialect=postgresql.dialect()))
        assert ddl.startswith("\nCREATE TABLE")
