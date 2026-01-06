import re
from pathlib import Path
from typing import List

from constants import MIN_CHAPTER_LENGTH, SEPARATOR, CHAPTER_PATTERNS_ANCHORED
from formats.base import BaseBookParser
from models import Chapter
from utils.filenames import sanitize_filename
from utils.logging import setup_logging

logger = setup_logging()


class BookSplitter:
    """Оркестратор разбиения книги на главы"""

    def __init__(self, parser: BaseBookParser, output_dir: Path):
        """
        Args:
            parser: Парсер для конкретного формата книги
            output_dir: Директория для сохранения глав
            min_chapter_length: Минимальная длина главы
        """

        self.parser = parser
        self.output_dir = output_dir
        self.min_chapter_length = MIN_CHAPTER_LENGTH

    def split(self) -> List[str]:
        """
        Разбиваем книгу на главы и сохраняем.
        Возвращает список имён/путей сохранённых файлов.
        """
        self.output_dir.mkdir(exist_ok=True)
        saved_files: List[str] = []

        # ------- ШАГ 1: выбор стратегии без предварительного создания parse()-генератора -------
        strategy = None
        final_chapters: List[Chapter] = []

        # 1) структурные главы имеют приоритет
        if (
            hasattr(self.parser, "has_structural_chapters")
            and self.parser.has_structural_chapters()
        ):
            strategy = "STRUCTURAL"
            logger.info("Detected structural chapters.")
            # Вызов parse() теперь безопасен — мы знаем, что хотим структурный парсинг
            chapters_list = list(self.parser.parse())
            final_chapters = chapters_list

        # 2) текстовые маркеры
        elif (
            hasattr(self.parser, "has_textual_chapters")
            and self.parser.has_textual_chapters()
        ):
            strategy = "TEXTUAL"
            logger.info("Detected textual chapter markers.")
            # Попытка получить full_text: если парсер предоставляет кэшированный метод - используем его
            full_text = None

            if hasattr(self.parser, "_extract_full_text"):
                try:
                    full_text = self.parser._extract_full_text()
                except Exception as e:
                    logger.debug("Не удалось извлечь полный текст из парсера: %s", e)

            # в крайнем случае читаем parse() и склеиваем (медленнее)
            if not full_text:
                logger.debug(
                    "Fallback: собираем текст из parse() в один блок (медленно)."
                )
                parts = []
                for ch in self.parser.parse():
                    parts.append(ch.text)
                    # можно ограничить сколько читать, но это fallback
                full_text = "\n".join(parts)

            if not full_text:
                logger.warning(
                    "Не удалось получить полный текст для текстового сплита; переключаем на структурный парсинг."
                )
                chapters_list = list(self.parser.parse())
                final_chapters = chapters_list
                strategy = "STRUCTURAL-FALLBACK"
            else:
                final_chapters = self._split_text_into_chapters_from_text(full_text)

        # 3) эвристика по длине (fallback)
        else:
            strategy = "HEURISTIC"
            logger.debug("Using heuristic (length-based) strategy.")
            chapters_list = list(self.parser.parse())
            final_chapters = self._filter_by_length(chapters_list)

        logger.info(f"Выбрана стратегия разбиения: {strategy}")

        # ------- Сохранение глав -------
        for chapter in final_chapters:
            try:
                saved_files.append(self._save_chapter(chapter))
            except Exception as e:
                logger.error(
                    "Ошибка при сохранении главы %s: %s",
                    getattr(chapter, "title", "n/a"),
                    e,
                )

        return saved_files

    # ---------- STRATEGIES ----------

    def _filter_by_length(self, chapters: List[Chapter]) -> List[Chapter]:
        """
        Фильтруем главы по минимально допустимому размеру

        Args:
            chapters: Список глав

        Return:
            Отфильтрованный список глав
        """

        return [ch for ch in chapters if len(ch.text) >= MIN_CHAPTER_LENGTH]

    def _split_by_text_markers(self, chapters: List[Chapter]) -> List[Chapter]:
        """
        Разбиваем главы по текстовым маркерам

        Args:
            chapters: Список глав

        Return:
            Отфильтрованный список глав
        """

        from constants import CHAPTER_PATTERNS_ANCHORED

        full_text = "\n".join(ch.text for ch in chapters)

        matches = []

        for pattern in CHAPTER_PATTERNS_ANCHORED:
            matches = list(pattern.finditer(full_text))
            if len(matches) >= 2:
                break

        if not matches:
            return chapters

        result: List[Chapter] = []

        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)

            chunk = full_text[start:end].strip()
            title = match.group(0).strip()

            if len(chunk) < MIN_CHAPTER_LENGTH:
                continue

            result.append(Chapter(index=len(result) + 1, title=title, text=chunk))

        return result

    def _split_text_into_chapters_from_text(self, full_text: str) -> List[Chapter]:
        """
        Разбивает единый большой текст по текстовым маркерам (CHAPTER_PATTERNS_ANCHORED).
        Возвращает список Chapter.
        Если маркеров < 2, возвращает один Chapter со всем текстом.
        """
        # Быстрая нормализация
        text = full_text.replace("\u00a0", " ")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t]+", " ", text)

        # Ищем все вхождения маркеров (по всем паттернам) и собираем их позиции
        matches = []
        for pat in CHAPTER_PATTERNS_ANCHORED:
            for m in pat.finditer(text):
                matches.append((m.start(), m.end(), m.group(0)))
        # Если нет или мало — возвращаем единый кусок
        if len(matches) < 2:
            return [Chapter(index=1, title="", text=text)]

        # Сортируем по позиции
        matches.sort(key=lambda x: x[0])

        chapters: List[Chapter] = []
        for i, (start, end, title_raw) in enumerate(matches):
            chunk_start = start
            chunk_end = matches[i + 1][0] if i + 1 < len(matches) else len(text)
            chunk = text[chunk_start:chunk_end].strip()
            title = title_raw.strip()
            if not chunk:
                continue
            chapters.append(
                Chapter(
                    index=len(chapters) + 1,
                    title=title or f"Глава {len(chapters) + 1}",
                    text=chunk,
                )
            )
        return chapters

    # ---------- SAVE ----------

    def _save_chapter(self, chapter: Chapter) -> str:
        """
        Сохраняем главу

        Args:
            chapter: Глава

        Return:
            Путь к сохраненной главе
        """

        filename = chapter.format_filename(sanitize_filename)
        filepath = self.output_dir / filename

        content = chapter.format_content(SEPARATOR)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return filename
