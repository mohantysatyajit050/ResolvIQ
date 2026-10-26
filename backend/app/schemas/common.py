from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """One page of a list, plus the numbers a client needs to ask for the next page."""

    items: list[T]
    total: int
    limit: int
    offset: int
