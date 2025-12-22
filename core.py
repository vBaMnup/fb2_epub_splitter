from pathlib import Path
from typing import List

from constants import MIN_CHAPTER_LENGTH, SEPARATOR
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
        """

        self.parser = parser
        self.output_dir = output_dir
        self.min_chapter_length = MIN_CHAPTER_LENGTH

    def split(self) -> List[str]:
        """
        Разбиваем книгу на главы"

        Return:
            Список путей к сохраненным главам
        """

        saved_files: List[str] = []

        # 1. Получаем базовые главы (структурные, если есть)
        chapters = list(self.parser.parse())

        # 2. Выбор стратегии
        if (
            hasattr(self.parser, "has_structural_chapters")
            and self.parser.has_structural_chapters()
        ):
            final_chapters = chapters
            strategy = "STRUCTURAL"

        elif (
            hasattr(self.parser, "has_textual_chapters")
            and self.parser.has_textual_chapters()
        ):
            final_chapters = self._split_by_text_markers(chapters)
            strategy = "TEXTUAL"

        else:
            final_chapters = self._filter_by_length(chapters)
            strategy = "HEURISTIC"

        logger.info(f"Выбрана стратегия разбиения: {strategy}")

        # 3. Сохранение
        for chapter in final_chapters:
            saved_files.append(self._save_chapter(chapter))

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

        from constants import CHAPTER_PATTERNS

        full_text = "\n".join(ch.text for ch in chapters)
        matches = []

        for pattern in CHAPTER_PATTERNS:
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
