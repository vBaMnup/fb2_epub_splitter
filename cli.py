import sys
from pathlib import Path

from formats.base import BaseBookParser
from core import BookSplitter
from formats.fb2 import FB2Parser
from formats.epub import EPUBParser
from utils.logging import setup_logging


def get_parser(book_path: Path) -> BaseBookParser:
    """Фабрика парсеров - определяет нужный парсер по расширению файла

    Args:
        book_path: Путь к файлу книги

    Returns:
        Экземпляр парсера

    Raises:
        ValueError: Если формат не поддерживается
    """

    if FB2Parser.supports(book_path):
        return FB2Parser(book_path)

    if EPUBParser.supports(book_path):
        return EPUBParser(book_path)

    raise ValueError(f"Формат {book_path.suffix} не поддерживается")


def run():
    """Главная функция CLI"""
    logger = setup_logging()

    print("=" * 60)
    print("  РАЗБИВАТЕЛЬ КНИГ НА ГЛАВЫ (FB2/EPUB)")
    print("  Архитектура: Clean Architecture + SOLID")
    print("=" * 60)
    print()

    # Запрашиваем путь к файлу
    book_path_str = input("Введите путь к книге (FB2 или EPUB): ").strip().strip('"')
    book_path = Path(book_path_str)

    if not book_path.exists():
        logger.error(f"❌ Файл не найден: {book_path}")
        sys.exit(1)

    try:
        # Определяем парсер
        logger.info(f"📖 Обработка: {book_path.name}")
        parser = get_parser(book_path)

        # Создаем выходную директорию
        output_dir = book_path.parent / f"{book_path.stem}_chapters"

        # Разбиваем книгу
        splitter = BookSplitter(parser, output_dir)
        saved_files = splitter.split()

        # Выводим результат
        print()
        print("=" * 60)
        logger.info(f"✅ Успешно разбито на {len(saved_files)} глав(ы)")
        logger.info(f"📁 Главы сохранены в: {output_dir}")
        print("=" * 60)

        # Показываем несколько первых файлов
        if saved_files:
            print("\nПервые главы:")
            for filename in saved_files[:5]:
                logger.info(f"  ✓ {filename}")
            if len(saved_files) > 5:
                logger.info(f"  ... и еще {len(saved_files) - 5}")

    except ValueError as e:
        logger.error(f"❌ {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run()
