from pathlib import Path

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

    def split(self) -> list[str]:
        """Разбивает книгу на главы и сохраняет их

        Returns:
            Список имен сохраненных файлов
        """

        # Создаем выходную директорию
        self.output_dir.mkdir(exist_ok=True)

        # Проверяем, есть ли явная разметка глав
        has_explicit = self.parser.has_textual_chapters()

        if has_explicit:
            logger.info("✓ Обнаружена явная разметка глав в тексте")
            logger.info("  Фильтрация по минимальной длине ОТКЛЮЧЕНА")
        else:
            logger.info("✓ Явная разметка не найдена")
            logger.info(
                f"  Используется фильтрация по минимальной длине ({self.min_chapter_length} символов)"
            )

        saved_files = []

        for chapter in self.parser.parse():
            # Если есть явная разметка - сохраняем все главы
            # Если нет - проверяем минимальную длину
            if has_explicit or chapter.is_valid(self.min_chapter_length):
                filename = self._save_chapter(chapter)
                saved_files.append(filename)
                logger.info(f"  ✓ Сохранена: {filename}")

        return saved_files

    def _save_chapter(self, chapter: Chapter) -> str:
        """Сохраняет главу в файл"""

        filename = chapter.format_filename(sanitize_filename)
        filepath = self.output_dir / filename

        content = chapter.format_content(SEPARATOR)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return filename
