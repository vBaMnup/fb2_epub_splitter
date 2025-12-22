import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterator

from constants import FB2_NS, SKIP_TITLES, CHAPTER_PATTERNS
from models import Chapter
from .base import BaseBookParser


class FB2Parser(BaseBookParser):
    """Парсер для формата FB2 (FictionBook 2.0)"""

    SUPPORTED_EXTENSIONS = {".fb2"}

    def __init__(self, book_path: Path):
        super().__init__(book_path)
        self._tree: ET.ElementTree | None = None
        self._body: ET.Element | None = None

    def _load_tree(self) -> None:
        """Загружает дерево XML и body книги"""
        if self._tree is None:
            self._tree = ET.parse(self.book_path)
            self._body = self._tree.getroot().find(".//fb:body", FB2_NS)

    # --------- DETECTION LAYER ---------

    def has_structural_chapters(self) -> bool:
        """
        Проверяет, есть ли в книге структурные главы (section + title)

        Returns:
            True, если найдена хотя бы одна секция с осмысленным title
        """
        self._load_tree()

        if self._body is None:
            return False

        for section in self._body.findall("fb:section", FB2_NS):
            title = section.find("fb:title", FB2_NS)
            if title is not None and "".join(title.itertext()).strip():
                return True

        return False

    def has_textual_chapters(self) -> bool:
        """
        Проверяет, есть ли в тексте маркеры глав вида:
        'Глава 1', 'Chapter II', 'Часть первая' и т.п.
        """
        self._load_tree()

        if self._body is None:
            return False

        full_text = "".join(self._body.itertext())

        for pattern in CHAPTER_PATTERNS:
            matches = pattern.findall(full_text)
            if len(matches) >= 2:
                return True

        return False

    # --------- PARSING LAYER ---------

    def parse(self) -> Iterator[Chapter]:
        """
        Парсит книгу и возвращает главы,
        основываясь ТОЛЬКО на структурной разметке FB2.
        Эвристики здесь не применяются.
        """
        self._load_tree()

        if self._body is None:
            return

        sections = self._body.findall("fb:section", FB2_NS)

        for index, section in enumerate(sections, start=1):
            chapter = self._parse_section(section, index)
            if chapter:
                yield chapter

    def _parse_section(self, section: ET.Element, index: int) -> Chapter | None:
        """
        Парсит одну секцию FB2 в главу
        """
        title_element = section.find("fb:title", FB2_NS)

        if title_element is not None:
            title = "".join(title_element.itertext()).strip()
        else:
            title = ""

        # Пропускаем технические и пустые заголовки
        if title.lower().strip() in SKIP_TITLES:
            return None

        text_parts: list[str] = []
        for p in section.findall("fb:p", FB2_NS):
            paragraph = "".join(p.itertext()).strip()
            if paragraph:
                text_parts.append(paragraph)

        text = "\n\n".join(text_parts).strip()

        if not text:
            return None

        return Chapter(index=index, title=title or f"Глава {index}", text=text)
