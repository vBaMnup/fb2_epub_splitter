from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator


class BaseBookParser(ABC):
    """Базовый класс парсера книг"""

    SUPPORTED_EXTENSIONS = None

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

    # @abstractmethod
    def has_textual_chapters(self) -> bool:
        """Проверяет, есть ли в тексте маркеры глав вида:
        'Глава 1', 'Chapter II', 'Часть первая' и т.п.

        Returns:
            True, если есть хотя бы два совпадения
        """
        raise NotImplementedError

    @classmethod
    def supports(cls, book_path: Path) -> bool:
        """
        Проверяет, поддерживается ли данный формат

        Args:
            book_path (Path): Путь к книге

        Returns:
            True, если поддерживается
        """

        if not hasattr(cls, "SUPPORTED_EXTENSIONS"):
            return False
        return book_path.suffix.lower() in cls.SUPPORTED_EXTENSIONS
