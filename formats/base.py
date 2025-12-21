from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator


class BaseBookParser(ABC):
    """Базовый класс парсера книг"""

    def __init__(self, book_path: Path):
        self.book_path = book_path

        if not self.book_path.exists():
            raise ValueError(f"Книга {book_path} не найдена")

    @abstractmethod
    def parse(self) -> Iterator["Chapter"]:
        """
        Парсит книгу и возвращает итератор глав

        Returns:
            Итератор глав
        """

        raise NotImplementedError

    @classmethod
    @abstractmethod
    def supports(cls, book_path: Path) -> bool:
        """
        Проверяет, поддерживается ли данный формат

        Args:
            book_path (Path): Путь к книге

        Returns:
            True, если поддерживается
        """

        raise NotImplementedError
