import os
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Iterator

from .base import BaseBookParser
from ..constants import OPF_NS, CONTAINER_NS, SKIP_TITLES
from ..extractors.html import HtmlTextExtractor
from ..models import Chapter


class EPUBParser(BaseBookParser):
    """Парсер для формата EPUB"""

    SUPPORTED_EXTENSIONS = {".epub"}

    def __init__(self, book_path: Path):
        super().__init__(book_path)
        self.html_extractor = HtmlTextExtractor()

    def parse(self) -> Iterator[Chapter]:
        """
        Парсит EPUB файл и возвращает главы

        Returns:
            Итератор глав
        """

        with zipfile.ZipFile(self.book_path, "r") as epub:
            opf_path = self._find_opf(epub)
            if not opf_path:
                return

            # Парсим OPF для получения списка глав
            chapter_paths = self._get_chapter_paths(epub, opf_path)

            # Обрабатываем каждую главу
            index = 1
            for chapter_path in chapter_paths:
                chapter = self._parse_chapter(epub, chapter_path, index)
                if chapter:
                    yield chapter
                    index += 1

    def _find_opf(self, epub: zipfile.ZipFile) -> str | None:
        """
        Находит путь к файлу content.opf

        Args:
            epub: EPUB файл

        Returns:
            Путь к файлу content.opf
        """

        # Проверяем META-INF/container.xml
        try:
            container = epub.read("META-INF/container.xml").decode("utf-8")
            container_root = ET.fromstring(container)
            rootfile = container_root.find(".//container:rootfile", CONTAINER_NS)
            if rootfile is not None:
                return rootfile.get("full-path")
        except:
            pass

        # Ищем вручную
        for name in epub.namelist():
            if name.endswith(".opf"):
                return name

        return None

    def _get_chapter_paths(self, epub: zipfile.ZipFile, opf_path: str) -> list[str]:
        """
        Получает список путей к главам из OPF файла

        Args:
            epub: EPUB файл
            opf_path: Путь к файлу content.opf

        Returns:
            Список путей к главам
        """

        opf_content = epub.read(opf_path).decode("utf-8")
        opf_root = ET.fromstring(opf_content)

        # Получаем manifest и spine
        manifest = opf_root.find(".//opf:manifest", OPF_NS)
        spine = opf_root.find(".//opf:spine", OPF_NS)

        if manifest is None or spine is None:
            return []

        # Создаем словарь id -> href
        id_to_href = {}
        for item in manifest.findall(".//opf:item", OPF_NS):
            item_id = item.get("id")
            href = item.get("href")
            if href and href.endswith((".html", ".xhtml", ".htm")):
                id_to_href[item_id] = href

        # Собираем пути в порядке spine
        base_path = os.path.dirname(opf_path)
        chapter_paths = []

        for itemref in spine.findall(".//opf:itemref", OPF_NS):
            idref = itemref.get("idref")
            if idref in id_to_href:
                full_path = os.path.join(base_path, id_to_href[idref]).replace(
                    "\\", "/"
                )
                chapter_paths.append(full_path)

        return chapter_paths

    def _parse_chapter(
        self, epub: zipfile.ZipFile, chapter_path: str, index: int
    ) -> Chapter | None:
        """
        Парсит одну главу EPUB

        Args:
            epub: EPUB файл
            chapter_path: Путь к главе
            index: Номер главы

        Returns:
            Глава
        """

        try:
            html = epub.read(chapter_path).decode("utf-8")
            title, text = self.html_extractor.extract(html)

            # Проверка на технический контент
            if not text.strip():
                return None

            if title.lower().strip() in SKIP_TITLES:
                return None

            return Chapter(index=index, title=title or f"Глава {index}", text=text)

        except Exception:
            return None
