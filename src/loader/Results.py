from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar('T')

@dataclass
class Success(Generic[T]):
    data: T

@dataclass
class Error:
    message: str
    code: int | None = None
    solution: str | None = None
    exception: Exception = None