from enum import Enum

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Every table class inherits from this."""


def check_in(column: str, enum_class: type[Enum]) -> str:
    """Build the SQL text for a CHECK that only allows the values of an enum."""
    values = ", ".join(f"'{member.value}'" for member in enum_class)
    return f"{column} IN ({values})"
