import os
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Iterator

from constants import (
    OPF_NS,
    CONTAINER_NS,
    SKIP_TITLES,
    CHAPTER_PATTERNS_ANCHORED,
    CHAPTER_PATTERNS_ANYWHERE,
)
from core import logger
from extractors.html import HtmlTextExtractor
from models import Chapter
from .base import BaseBookParser


class EPUBParser(BaseBookParser):
    """Парсер для формата EPUB"""

    SUPPORTED_EXTENSIONS = {".epub"}
    MAX_ANALYSIS_FILES = 10
    MIN_CHAPTER_MATCHES = 2

    def __init__(self, book_path: Path):
        super().__init__(book_path)
        self.html_extractor = HtmlTextExtractor()
        self._full_text_checked = False
        self._full_text = None

    def _extract_full_text(
        self, max_files: int = 1000, max_chars: int = 1000000000000000000
    ) -> str:
        """
        Извлекает текст из EPUB для анализа (включая titles и основные XHTML).
        Стратегия:
         1) Пытаемся найти OPF через META-INF/container.xml
         2) Если OPF найден — используем manifest+spine, читаем файлы в spine по порядку
         3) Если OPF не найден — сканируем namelist() и берём релевантные .xhtml/.html/.htm файлы
         4) Используем HtmlTextExtractor для извлечения title и текста, вставляем \n вокруг title
         5) Останавливаемся при достижении max_files или max_chars
        """
        text_parts: list[str] = []
        accumulated = 0
        files_read = 0

        def _append_piece(piece: str) -> bool:
            """Добавить кусок в результирующий буфер; вернуть True если дальше читать не нужно."""
            nonlocal accumulated, text_parts
            if not piece:
                return False
            # Нормализация минимальна — заменяем NBSP и приводим переводы строк
            piece = piece.replace("\u00a0", " ")
            piece = piece.replace("\r\n", "\n").replace("\r", "\n")
            # Удаляем лишние табы/повторные пробелы (но сохраняем переносы строк)
            piece = re.sub(r"[ \t]+", " ", piece)
            text_parts.append(piece)
            accumulated += len(piece)
            if max_chars is not None and accumulated >= max_chars:
                return True
            return False

        try:
            with zipfile.ZipFile(self.book_path, "r") as epub:
                # 1) Попытка найти OPF через container.xml
                opf_path = None
                try:
                    container_xml = epub.read("META-INF/container.xml").decode(
                        "utf-8", errors="replace"
                    )
                    try:
                        container_root = ET.fromstring(container_xml)
                        rootfile = container_root.find(
                            ".//container:rootfile", CONTAINER_NS
                        )
                        if rootfile is not None:
                            opf_path = rootfile.get("full-path")
                    except ET.ParseError:
                        logger.debug("Не удалось распарсить container.xml")
                except KeyError:
                    logger.debug("META-INF/container.xml не найден в EPUB")

                chapter_file_paths: list[str] = []

                if opf_path:
                    # 2) Разбор OPF
                    try:
                        opf_content = epub.read(opf_path).decode(
                            "utf-8", errors="replace"
                        )
                        opf_root = ET.fromstring(opf_content)

                        manifest = opf_root.find(".//opf:manifest", OPF_NS)
                        spine = opf_root.find(".//opf:spine", OPF_NS)

                        id_to_href: dict[str, str] = {}
                        if manifest is not None:
                            for item in manifest.findall(".//opf:item", OPF_NS):
                                href = item.get("href")
                                item_id = item.get("id")
                                media_type = item.get("media-type", "")
                                # выбираем только html/xhtml
                                if (
                                    href
                                    and item_id
                                    and media_type
                                    and "html" in media_type
                                ):
                                    id_to_href[item_id] = href

                        if spine is not None:
                            base = os.path.dirname(opf_path)
                            for itemref in spine.findall(".//opf:itemref", OPF_NS):
                                idref = itemref.get("idref")
                                if idref in id_to_href:
                                    # формируем путь внутри архива
                                    href = id_to_href[idref]
                                    full_path = os.path.normpath(
                                        os.path.join(base, href)
                                    ).replace("\\", "/")
                                    chapter_file_paths.append(full_path)
                    except Exception as e:
                        logger.debug(f"Ошибка при разборе OPF: {e}")
                        chapter_file_paths = []

                # 3) Фолбэк: если spine пустой — сканируем namelist()
                if not chapter_file_paths:
                    # собираем candidate files, предпочитая OEBPS/, Text/, и затем все xhtml/html
                    all_names = epub.namelist()
                    candidates = [
                        n
                        for n in all_names
                        if n.lower().endswith((".xhtml", ".html", ".htm"))
                    ]

                    # Сортируем так, чтобы файлы в OEBPS/ и Text/ шли первыми
                    def _score_name(name: str) -> int:
                        name_low = name.lower()
                        if name_low.startswith("oebps/"):
                            return 0
                        if "text" in name_low and (
                            name_low.endswith(".xhtml") or name_low.endswith(".html")
                        ):
                            return 1
                        return 2

                    candidates.sort(key=lambda n: (_score_name(n), n))
                    chapter_file_paths = candidates

                # 4) Читаем файлы в порядке chapter_file_paths
                for path in chapter_file_paths:
                    if max_files is not None and files_read >= max_files:
                        logger.debug("Достигнут лимит файлов для анализа (max_files)")
                        break

                    try:
                        raw = epub.read(path)
                    except KeyError:
                        # Файл может быть указан несоотносящимся href; пропускаем
                        continue
                    except Exception as e:
                        logger.debug(f"Ошибка чтения {path}: {e}")
                        continue

                    try:
                        html = raw.decode("utf-8", errors="replace")
                    except Exception:
                        # На всякий случай ещё одна попытка без явного декодирования
                        html = raw.decode("utf-8", errors="replace")

                    # Используем html_extractor для получения title и текста
                    try:
                        title, text = self.html_extractor.extract(html)
                    except Exception as e:
                        logger.debug(f"HtmlTextExtractor failed for {path}: {e}")
                        # fallback: просто берем сырый текст (удалить теги простым способом)
                        text = re.sub(r"<[^>]+>", " ", html)
                        title = ""

                    # Вставляем title на отдельной строке, чтобы маркеры типа "Глава" не склеивались
                    if title:
                        stop = _append_piece(title + "\n")
                        if stop:
                            return "\n".join(text_parts)

                    stop = _append_piece(text)
                    files_read += 1
                    if stop:
                        break

                # Если не собрали ничего — логируем
                if not text_parts:
                    logger.debug(
                        "Не удалось извлечь текстовые части из EPUB (нет подходящих HTML-файлов)"
                    )
                    return ""

                # Собираем результат
                result = "\n".join(text_parts)
                # Дополнительная финальная нормализация: удаляем подряд идущие пустые строки
                result = re.sub(r"\n{3,}", "\n\n", result)
                return result

        except zipfile.BadZipFile:
            logger.error("Файл не является корректным ZIP/EPUB")
            return ""
        except Exception as e:
            logger.error(f"Неожиданная ошибка при извлечении текста EPUB: {e}")
            return ""

    # ---------- CHAPTER DETECTION ----------

    def has_textual_chapters(self) -> bool:
        """
        Комбинированная проверка:
         1) пробуем найти заголовки с ^ (anchored)
         2) если не нашли — делаем мягкую нормализацию (вставка \n перед 'Глава' и т.п.)
            и повторяем поиск с теми же паттернами
         3) как последний шаг — ищем незакреплённые варианты CHAPTER_PATTERNS_ANYWHERE
        """

        if self._full_text is None:
            self._full_text = self._extract_full_text()
            logger.info(f"📖 Извлечено текста: {len(self._full_text)} символов")

        if not self._full_text:
            logger.info("Не удалось извлечь текст для поиска меток глав")
            return False

        text = self._full_text.replace("\u00a0", " ")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t]+", " ", text)

        logger.info("🔎 Поиск меток глав...")

        # 1) Быстрая проверка для анкорных паттернов (^)
        count = 0
        for p in CHAPTER_PATTERNS_ANCHORED:
            print(p)
            for _ in p.finditer(text):
                count += 1
                logger.info(f"✅ Паттерн '{p.pattern}' найден {count} раз")
                if count >= 2:
                    return True

        logger.info("🔎 Поиск меток глав... (повтор)")

        # 2) Если не найдено, делаем лёгкую нормализацию: вставляем перевод строки перед словом 'Глава' и аналогами,
        #    когда оно напрямую примыкает к букве/цифре предыдущего токена (случай "влиянияГлава")
        #    Это — минимальное вмешательство, только для детекции.
        normalized = re.sub(
            r"(?<=[A-Za-zА-Яа-яЁё0-9])(?=(глава|часть|раздел|chapter|part|section))",
            "\n",
            text,
            flags=re.IGNORECASE,
        )

        # дополнительная безопасная нормализация: если перед 'Глава' был символ без пробела, мы вставили \n,
        # также удалим возможные подряд \n для аккуратности
        normalized = re.sub(r"\n{2,}", "\n", normalized)

        count = 0
        for p in CHAPTER_PATTERNS_ANCHORED:
            for _ in p.finditer(normalized):
                count += 1
                if count >= 2:
                    return True

        # 3) Финальный шаг — если всё ещё нет, ищем вхождение в любом месте (менее строго)
        count = 0
        for p in CHAPTER_PATTERNS_ANYWHERE:
            for _ in p.finditer(text):
                count += 1
                print(count)
                if count >= 2:
                    return True

        return False

    # ---------- MAIN PARSE ----------

    def parse(self) -> Iterator[Chapter]:
        logger.info(f"📖 Обработка EPUB: {self.book_path.name}")

        if self.has_textual_chapters():
            logger.info(
                "ℹ️ Текстовая разметка глав обнаружена - используется другой сплиттер"
            )
            return

        with zipfile.ZipFile(self.book_path, "r") as epub:
            opf_path = self._find_opf(epub)
            if not opf_path:
                logger.error("❌ OPF не найден")
                return

            chapter_paths = self._get_chapter_paths(epub, opf_path)

            index = 1
            for chapter_path in chapter_paths:
                chapter = self._parse_chapter(epub, chapter_path, index)
                if chapter:
                    yield chapter
                    index += 1

    # ---------- HELPERS ----------

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = text.replace("\u00a0", " ")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        return re.sub(r"[ \t]+", " ", text)

    def _find_opf(self, epub: zipfile.ZipFile) -> str | None:
        try:
            container = epub.read("META-INF/container.xml").decode("utf-8")
            root = ET.fromstring(container)
            rootfile = root.find(".//container:rootfile", CONTAINER_NS)
            if rootfile is not None:
                return rootfile.get("full-path")
        except Exception:
            pass

        for name in epub.namelist():
            if name.endswith(".opf"):
                return name
        return None

    def _get_chapter_paths(self, epub: zipfile.ZipFile, opf_path: str) -> list[str]:
        opf_content = epub.read(opf_path).decode("utf-8")
        root = ET.fromstring(opf_content)

        manifest = root.find(".//opf:manifest", OPF_NS)
        spine = root.find(".//opf:spine", OPF_NS)

        if manifest is None or spine is None:
            return []

        id_to_href = {
            item.get("id"): item.get("href")
            for item in manifest.findall(".//opf:item", OPF_NS)
            if item.get("href", None).endswith((".html", ".xhtml", ".htm"))
        }

        base_path = os.path.dirname(opf_path)
        paths = []

        for itemref in spine.findall(".//opf:itemref", OPF_NS):
            idref = itemref.get("idref")
            if idref in id_to_href:
                paths.append(
                    os.path.join(base_path, id_to_href[idref]).replace("\\", "/")
                )
        return paths

    def _parse_chapter(
        self, epub: zipfile.ZipFile, chapter_path: str, index: int
    ) -> Chapter | None:
        try:
            html = epub.read(chapter_path).decode("utf-8", errors="ignore")
            title, text = self.html_extractor.extract(html)

            if not text.strip():
                return None

            if title.lower().strip() in SKIP_TITLES:
                return None

            return Chapter(
                index=index,
                title=title or f"Глава {index}",
                text=text,
            )
        except Exception:
            return None
