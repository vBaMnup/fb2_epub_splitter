import xml.etree.ElementTree as ET
from typing import Iterator

from .base import BaseBookParser
from ..constants import FB2_NS, SKIP_TITLES
from ..models import Chapter


class FB2Parser(BaseBookParser):
    """Парсер для формата FB2 (FictionBook 2.0)"""

    SUPPORTED_EXTENSIONS = {".fb2"}

    def parse(self) -> Iterator[Chapter] | None:
        """
        Парсит книгу и возвращает итератор глав

        Returns:
            Итератор глав
        """

        tree = ET.parse(self.book_path)
        root = tree.getroot()

        # Ищем body элемент
        body = root.find(".//fb:body", FB2_NS)
        if body is None:
            return

        # Ищем секции первого уровня (главы)
        sections = body.findall("fb:section", FB2_NS)

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
