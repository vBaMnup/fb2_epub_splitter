from pathlib import Path

from .constants import MIN_CHAPTER_LENGTH, SEPARATOR
from .formats.base import BaseBookParser
from .models import Chapter
from .utils.filenames import sanitize_filename


class BookSplitter:
    """Оркестратор разбиения книги на главы"""

    def __init__(self, parser: BaseBookParser, output_dir: Path):
        """
        Args:
            parser: Парсер книги
            output_dir: Папка для сохранения глав
        """

        self.parser = parser
        self.output_dir = output_dir
        self.min_chapter_length = MIN_CHAPTER_LENGTH

    def split(self) -> list[str]:
        """
        Разбиение книги на главы и сохраняет их

        Returns:
            Список путей к сохраненным главам
        """

        self.output_dir.mkdir(exist_ok=True)

        saved_files = []

        for chapter in self.parser.parse():
            # Проверяем валидность главы
            if not chapter.is_valid(self.min_chapter_length):
                continue

            # Сохраняем главу
            filename = self._save_chapter(chapter)
            saved_files.append(filename)

        return saved_files

    def _save_chapter(self, chapter: Chapter) -> str:
        """
        Сохраняет главу в указанную папку

        Args:
            chapter: Глава

        Returns:
            Путь к сохраненной главе
        """

        filename = chapter.format_filename(sanitizer=sanitize_filename)
        filepath = self.output_dir / filename

        content = chapter.format_content(SEPARATOR)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return filepath
