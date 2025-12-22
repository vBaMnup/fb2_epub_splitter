import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterator

from .base import BaseBookParser
from constants import FB2_NS, SKIP_TITLES, CHAPTER_PATTERNS
from models import Chapter


class FB2Parser(BaseBookParser):
    """Парсер для формата FB2 (FictionBook 2.0)"""

    SUPPORTED_EXTENSIONS = {".fb2"}

    def __init__(self, book_path: Path):
        super().__init__(book_path)
        self._tree = None
        self._body = None

    def _load_tree(self):
        """
        Загружает дерево XML
        """
        if self._tree is None:
            self._tree = ET.parse(self.book_path)
            self._body = self._tree.getroot().find(".//fb:body", FB2_NS)

    def has_explicit_chapters(self) -> bool:
        """
        Проверяет, есть ли в книге явная разметка на главы

        Returns:
            True если книга имеет явное разделение на главы
        """

        self._load_tree()
        if self._body is None:
            return False

        # Получаем весь текст книги
        full_text = "".join(self._body.itertext())

        # Проверяем, есть ли в тексте названия глав
        chapter_count = 0
        for pattern in CHAPTER_PATTERNS:
            matches = pattern.findall(full_text)
            chapter_count = max(chapter_count, len(matches))

        return chapter_count >= 2

    def parse(self) -> Iterator[Chapter] | None:
        """
        Парсит книгу и возвращает итератор глав

        Returns:
            Итератор глав
        """

        self._load_tree()

        if self._body is None:
            return

        # Ищем секции первого уровня (главы)
        sections = self._body.findall("fb:section", FB2_NS)

        for index, section in enumerate(sections, start=1):
            chapter = self._parse_section(section, index)
            if chapter:
                yield chapter

    def _parse_section(self, section: ET.Element, index: int) -> Chapter | None:
        """
        Парсит одну секцию

        Args:
            section: Элемент секции
            index: Номер секции

        Returns:
            Глава или None
        """

        title_element = section.find("fb:title", FB2_NS)

        if title_element is not None:
            title = "".join(title_element.itertext()).strip()
        else:
            title = f"Глава {index}"

        # Пропускаем технические заголовки
        if title.lower().strip() in SKIP_TITLES:
            return

        # Собираем текст из параграфов
        text_parts = []
        for p in section.findall("fb:p", FB2_NS):
            paragraph = "".join(p.itertext()).strip()
            if paragraph:
                text_parts.append(f"{paragraph}\n\n")

        text = "".join(text_parts)

        return Chapter(index=index, title=title, text=text)
