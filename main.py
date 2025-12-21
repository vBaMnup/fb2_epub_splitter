import logging
import os
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


class BookSplitter:
    """Класс для разбиения книг FB2 и EPUB на отдельные главы

    Оптимизирован для производительности:
    - Использует прямые XPath вместо рекурсивных
    - Компилирует regex один раз
    - Избегает конкатенации строк
    - Фильтрует технические файлы
    """

    # Компилируем regex один раз для всех экземпляров
    _TAG_STRIP_RE = re.compile(r"<[^>]+>")
    _STYLE_RE = re.compile(r"<style[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)
    _SCRIPT_RE = re.compile(r"<script[^>]*>.*?</script>", re.DOTALL | re.IGNORECASE)
    _P_TAG_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.DOTALL | re.IGNORECASE)
    _H_TAG_RE = re.compile(r"<h[1-6][^>]*>(.*?)</h[1-6]>", re.DOTALL | re.IGNORECASE)
    _FILENAME_CLEAN_RE = re.compile(r'[<>:"/\\|?*]')

    # Технические заголовки для пропуска
    _SKIP_TITLES = {
        "contents",
        "copyright",
        "table of contents",
        "toc",
        "содержание",
        "оглавление",
        "об авторе",
        "about the author",
    }

    # Минимальная длина главы (символов)
    _MIN_CHAPTER_LENGTH = 300

    def __init__(self, book_path):
        self.book_path = Path(book_path)
        self.book_format = self.book_path.suffix.lower()
        self.output_dir = self.book_path.parent / f"{self.book_path.stem}_chapters"

        # Предкомпилируем строки-константы
        self._separator = "=" * 60

        if self.book_format not in [".fb2", ".epub"]:
            raise ValueError("Поддерживаются только форматы FB2 и EPUB")

    def split(self):
        """Основной метод разбиения книги"""
        if self.book_format == ".fb2":
            return self._split_fb2()
        elif self.book_format == ".epub":
            return self._split_epub()

    def _split_fb2(self):
        """Разбиение FB2 файла (оптимизированная версия)"""
        logger.info(f"Обработка FB2 файла: {self.book_path.name}")

        # Парсинг XML
        tree = ET.parse(self.book_path)
        root = tree.getroot()

        # Определяем namespace
        ns = {"fb": "http://www.gribuser.ru/xml/fictionbook/2.0"}

        # Ищем body элемент
        body = root.find(".//fb:body", ns)
        if body is None:
            logger.warning("Не найден элемент body в FB2 файле")
            return []

        # Создаем выходную директорию
        self.output_dir.mkdir(exist_ok=True)

        chapters = []
        chapter_num = 1

        # ОПТИМИЗАЦИЯ: используем прямой поиск вместо рекурсивного .//)
        # Это находит только секции первого уровня (настоящие главы)
        sections = body.findall("fb:section", ns)

        if not sections:
            logger.warning("Главы не найдены")
            return []

        for section in sections:
            # ОПТИМИЗАЦИЯ: прямой поиск title (не рекурсивный)
            title_elem = section.find("fb:title", ns)
            if title_elem is not None:
                title = "".join(title_elem.itertext()).strip()
            else:
                title = f"Глава {chapter_num}"

            # Проверка на технический контент
            if self._is_skip_title(title):
                continue

            # Очищаем название файла от недопустимых символов
            safe_title = self._sanitize_filename(title)
            filename = f"{chapter_num:03d}_{safe_title}.txt"

            # ОПТИМИЗАЦИЯ: используем list вместо конкатенации строк
            chapter_parts = [
                f"{self._separator}\n",
                f"{title}\n",
                f"{self._separator}\n\n",
            ]

            # ОПТИМИЗАЦИЯ: прямой поиск параграфов (не рекурсивный)
            for p in section.findall("fb:p", ns):
                paragraph = "".join(p.itertext()).strip()
                if paragraph:
                    chapter_parts.append(f"{paragraph}\n\n")

            # Проверка минимальной длины
            chapter_text = "".join(chapter_parts)
            if len(chapter_text) < self._MIN_CHAPTER_LENGTH:
                continue

            # Сохраняем главу
            output_path = self.output_dir / filename
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(chapter_text)

            chapters.append(filename)
            logger.info(f"✓ Сохранена: {filename}")
            chapter_num += 1

        return chapters

    def _split_epub(self):
        """Разбиение EPUB файла (оптимизированная версия)"""
        logger.info(f"Обработка EPUB файла: {self.book_path.name}")

        # Создаем выходную директорию
        self.output_dir.mkdir(exist_ok=True)

        chapters = []
        chapter_num = 1

        with zipfile.ZipFile(self.book_path, "r") as epub:
            # Ищем content.opf для получения списка глав
            opf_path = self._find_opf(epub)
            if not opf_path:
                logger.warning("Не найден файл content.opf")
                return []

            # Парсим OPF файл
            opf_content = epub.read(opf_path).decode("utf-8")
            opf_root = ET.fromstring(opf_content)

            # Определяем namespace для OPF
            ns_opf = {"opf": "http://www.idpf.org/2007/opf"}

            # Получаем список HTML файлов глав
            manifest = opf_root.find(".//opf:manifest", ns_opf)
            spine = opf_root.find(".//opf:spine", ns_opf)

            if manifest is None or spine is None:
                logger.warning("Не найдены элементы manifest или spine")
                return []

            # Создаем словарь id -> href
            id_to_href = {}
            for item in manifest.findall(".//opf:item", ns_opf):
                item_id = item.get("id")
                href = item.get("href")
                if href and href.endswith((".html", ".xhtml", ".htm")):
                    id_to_href[item_id] = href

            # Обрабатываем главы по порядку из spine
            base_path = os.path.dirname(opf_path)

            for itemref in spine.findall(".//opf:itemref", ns_opf):
                idref = itemref.get("idref")
                if idref in id_to_href:
                    chapter_path = os.path.join(base_path, id_to_href[idref]).replace(
                        "\\", "/"
                    )

                    try:
                        chapter_html = epub.read(chapter_path).decode("utf-8")
                        title, text = self._extract_html_content(chapter_html)

                        # ОПТИМИЗАЦИЯ: фильтрация технических файлов
                        if not text.strip() or len(text) < self._MIN_CHAPTER_LENGTH:
                            continue

                        if self._is_skip_title(title):
                            continue

                        # Формируем имя файла
                        if title:
                            safe_title = self._sanitize_filename(title)
                        else:
                            safe_title = f"chapter_{chapter_num}"

                        filename = f"{chapter_num:03d}_{safe_title}.txt"

                        # Сохраняем главу
                        output_path = self.output_dir / filename
                        with open(output_path, "w", encoding="utf-8") as f:
                            f.write(f"{self._separator}\n")
                            f.write(f"{title or f'Глава {chapter_num}'}\n")
                            f.write(f"{self._separator}\n\n")
                            f.write(text)

                        chapters.append(filename)
                        logger.info(f"✓ Сохранена: {filename}")
                        chapter_num += 1

                    except Exception as e:
                        logger.debug(f"Пропуск {chapter_path}: {e}")
                        continue

        return chapters

    def _find_opf(self, epub):
        """Находит путь к файлу content.opf в EPUB"""
        # Сначала проверяем META-INF/container.xml
        try:
            container = epub.read("META-INF/container.xml").decode("utf-8")
            container_root = ET.fromstring(container)
            ns = {"container": "urn:oasis:names:tc:opendocument:xmlns:container"}
            rootfile = container_root.find(".//container:rootfile", ns)
            if rootfile is not None:
                return rootfile.get("full-path")
        except:
            pass

        # Если не нашли, ищем вручную
        for name in epub.namelist():
            if name.endswith(".opf"):
                return name

        return None

    def _extract_html_content(self, html):
        """Извлекает заголовок и текст из HTML (оптимизированная версия)"""
        # Удаляем теги style и script (предкомпилированные regex)
        html = self._STYLE_RE.sub("", html)
        html = self._SCRIPT_RE.sub("", html)

        # Ищем заголовок
        title = ""
        title_match = self._H_TAG_RE.search(html)
        if title_match:
            title = self._TAG_STRIP_RE.sub("", title_match.group(1)).strip()

        # ОПТИМИЗАЦИЯ: пробуем парсить как валидный XHTML
        text = self._extract_text_etree(html)
        if text:
            return title, text

        # Fallback: используем regex для невалидного HTML
        return title, self._extract_text_regex(html)

    def _extract_text_etree(self, html):
        """Извлечение текста через ElementTree (быстро для валидного XHTML)"""
        try:
            # Пробуем обернуть в корневой элемент если нужно
            if not html.strip().startswith("<?xml"):
                html = f"<root>{html}</root>"

            root = ET.fromstring(html)

            # Ищем все параграфы
            paragraphs = root.findall(".//p")
            if not paragraphs:
                return None

            # ОПТИМИЗАЦИЯ: list comprehension вместо конкатенации
            parts = []
            for p in paragraphs:
                text = "".join(p.itertext()).strip()
                if text:
                    parts.append(text)

            return "\n\n".join(parts) + "\n\n" if parts else None

        except ET.ParseError:
            # Невалидный XHTML - вернем None для fallback
            return None

    def _extract_text_regex(self, html):
        """Извлечение текста через regex (fallback для невалидного HTML)"""
        # Извлекаем текст из параграфов (предкомпилированный regex)
        paragraphs = self._P_TAG_RE.findall(html)

        # ОПТИМИЗАЦИЯ: list + join вместо конкатенации
        parts = []
        for p in paragraphs:
            clean_p = self._TAG_STRIP_RE.sub("", p).strip()
            if clean_p:
                parts.append(clean_p)

        return "\n\n".join(parts) + "\n\n" if parts else ""

    def _is_skip_title(self, title):
        """Проверяет, является ли заголовок техническим"""
        if not title:
            return False
        return title.lower().strip() in self._SKIP_TITLES

    def _sanitize_filename(self, filename):
        """Очищает имя файла от недопустимых символов (оптимизированная версия)"""
        # ОПТИМИЗАЦИЯ: используем предкомпилированный regex
        filename = self._FILENAME_CLEAN_RE.sub("", filename)
        # Ограничиваем длину
        filename = filename[:100]
        # Убираем точки и пробелы в начале и конце
        filename = filename.strip(". ")
        return filename or "chapter"


def main():
    """Главная функция программы"""
    print("=" * 60)
    print("  РАЗБИВАТЕЛЬ КНИГ НА ГЛАВЫ (FB2/EPUB)")
    print("  Оптимизированная версия для больших файлов")
    print("=" * 60)
    print()

    # Запрашиваем путь к файлу
    book_path = input("Введите путь к книге (FB2 или EPUB): ").strip().strip('"')

    if not os.path.exists(book_path):
        logger.error(f"Файл не найден: {book_path}")
        return

    try:
        # Создаем экземпляр разбивателя
        splitter = BookSplitter(book_path)

        # Разбиваем книгу
        chapters = splitter.split()

        print()
        print("=" * 60)
        logger.info(f"✅ Успешно разбито на {len(chapters)} глав(ы)")
        logger.info(f"📁 Главы сохранены в: {splitter.output_dir}")
        print("=" * 60)

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
