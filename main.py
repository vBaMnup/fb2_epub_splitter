import os
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import re


class BookSplitter:
    """Класс для разбиения книг FB2 и EPUB на отдельные главы"""

    def __init__(self, book_path):
        self.book_path = Path(book_path)
        self.book_format = self.book_path.suffix.lower()
        self.output_dir = self.book_path.parent / f"{self.book_path.stem}_chapters"

        if self.book_format not in ['.fb2', '.epub']:
            raise ValueError("Поддерживаются только форматы FB2 и EPUB")

    def split(self):
        """Основной метод разбиения книги"""
        if self.book_format == '.fb2':
            return self._split_fb2()
        elif self.book_format == '.epub':
            return self._split_epub()

    def _split_fb2(self):
        """Разбиение FB2 файла"""
        print(f"Обработка FB2 файла: {self.book_path.name}")

        # Парсинг XML
        tree = ET.parse(self.book_path)
        root = tree.getroot()

        # Определяем namespace
        ns = {'fb': 'http://www.gribuser.ru/xml/fictionbook/2.0'}

        # Ищем body элемент
        body = root.find('.//fb:body', ns)
        if body is None:
            print("Не найден элемент body в FB2 файле")
            return []

        # Создаем выходную директорию
        self.output_dir.mkdir(exist_ok=True)

        chapters = []
        chapter_num = 1

        # Ищем все секции (главы)
        sections = body.findall('.//fb:section', ns)

        if not sections:
            print("Главы не найдены")
            return []

        for section in sections:
            # Получаем заголовок главы
            title_elem = section.find('.//fb:title', ns)
            if title_elem is not None:
                title = ''.join(title_elem.itertext()).strip()
            else:
                title = f"Глава {chapter_num}"

            # Очищаем название файла от недопустимых символов
            safe_title = self._sanitize_filename(title)
            filename = f"{chapter_num:03d}_{safe_title}.txt"

            # Получаем весь текст главы
            chapter_text = []
            chapter_text.append(f"{'=' * 60}\n")
            chapter_text.append(f"{title}\n")
            chapter_text.append(f"{'=' * 60}\n\n")

            # Собираем все параграфы
            for p in section.findall('.//fb:p', ns):
                paragraph = ''.join(p.itertext()).strip()
                if paragraph:
                    chapter_text.append(paragraph + "\n\n")

            # Сохраняем главу
            output_path = self.output_dir / filename
            with open(output_path, 'w', encoding='utf-8') as f:
                f.writelines(chapter_text)

            chapters.append(filename)
            print(f"✓ Сохранена: {filename}")
            chapter_num += 1

        return chapters

    def _split_epub(self):
        """Разбиение EPUB файла"""
        print(f"Обработка EPUB файла: {self.book_path.name}")

        # Создаем выходную директорию
        self.output_dir.mkdir(exist_ok=True)

        chapters = []
        chapter_num = 1

        with zipfile.ZipFile(self.book_path, 'r') as epub:
            # Ищем content.opf для получения списка глав
            opf_path = self._find_opf(epub)
            if not opf_path:
                print("Не найден файл content.opf")
                return []

            # Парсим OPF файл
            opf_content = epub.read(opf_path).decode('utf-8')
            opf_root = ET.fromstring(opf_content)

            # Определяем namespace для OPF
            ns_opf = {'opf': 'http://www.idpf.org/2007/opf'}

            # Получаем список HTML файлов глав
            manifest = opf_root.find('.//opf:manifest', ns_opf)
            spine = opf_root.find('.//opf:spine', ns_opf)

            if manifest is None or spine is None:
                print("Не найдены элементы manifest или spine")
                return []

            # Создаем словарь id -> href
            id_to_href = {}
            for item in manifest.findall('.//opf:item', ns_opf):
                item_id = item.get('id')
                href = item.get('href')
                if href and href.endswith(('.html', '.xhtml', '.htm')):
                    id_to_href[item_id] = href

            # Обрабатываем главы по порядку из spine
            base_path = os.path.dirname(opf_path)

            for itemref in spine.findall('.//opf:itemref', ns_opf):
                idref = itemref.get('idref')
                if idref in id_to_href:
                    chapter_path = os.path.join(base_path, id_to_href[idref]).replace('\\', '/')

                    try:
                        chapter_html = epub.read(chapter_path).decode('utf-8')
                        title, text = self._extract_html_content(chapter_html)

                        if not text.strip():
                            continue

                        # Формируем имя файла
                        if title:
                            safe_title = self._sanitize_filename(title)
                        else:
                            safe_title = f"chapter_{chapter_num}"

                        filename = f"{chapter_num:03d}_{safe_title}.txt"

                        # Сохраняем главу
                        output_path = self.output_dir / filename
                        with open(output_path, 'w', encoding='utf-8') as f:
                            f.write(f"{'=' * 60}\n")
                            f.write(f"{title or f'Глава {chapter_num}'}\n")
                            f.write(f"{'=' * 60}\n\n")
                            f.write(text)

                        chapters.append(filename)
                        print(f"✓ Сохранена: {filename}")
                        chapter_num += 1

                    except Exception as e:
                        print(f"Ошибка при обработке {chapter_path}: {e}")
                        continue

        return chapters

    def _find_opf(self, epub):
        """Находит путь к файлу content.opf в EPUB"""
        # Сначала проверяем META-INF/container.xml
        try:
            container = epub.read('META-INF/container.xml').decode('utf-8')
            container_root = ET.fromstring(container)
            ns = {'container': 'urn:oasis:names:tc:opendocument:xmlns:container'}
            rootfile = container_root.find('.//container:rootfile', ns)
            if rootfile is not None:
                return rootfile.get('full-path')
        except:
            pass

        # Если не нашли, ищем вручную
        for name in epub.namelist():
            if name.endswith('.opf'):
                return name

        return None

    def _extract_html_content(self, html):
        """Извлекает заголовок и текст из HTML"""
        # Удаляем теги, оставляя текст
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)

        # Ищем заголовок
        title_match = re.search(r'<h[1-6][^>]*>(.*?)</h[1-6]>', html, re.IGNORECASE | re.DOTALL)
        title = ''
        if title_match:
            title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()

        # Извлекаем текст из параграфов
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL | re.IGNORECASE)
        text = ''
        for p in paragraphs:
            clean_p = re.sub(r'<[^>]+>', '', p).strip()
            if clean_p:
                text += clean_p + "\n\n"

        return title, text

    def _sanitize_filename(self, filename):
        """Очищает имя файла от недопустимых символов"""
        # Убираем недопустимые символы
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # Ограничиваем длину
        filename = filename[:100]
        # Убираем точки в начале и конце
        filename = filename.strip('. ')
        return filename or "chapter"


def main():
    """Главная функция программы"""
    print("=" * 60)
    print("  РАЗБИВАТЕЛЬ КНИГ НА ГЛАВЫ (FB2/EPUB)")
    print("=" * 60)
    print()

    # Запрашиваем путь к файлу
    book_path = input("Введите путь к книге (FB2 или EPUB): ").strip().strip('"')

    if not os.path.exists(book_path):
        print(f"❌ Файл не найден: {book_path}")
        return

    try:
        # Создаем экземпляр разбивателя
        splitter = BookSplitter(book_path)

        # Разбиваем книгу
        chapters = splitter.split()

        print()
        print("=" * 60)
        print(f"✅ Успешно разбито на {len(chapters)} глав(ы)")
        print(f"📁 Главы сохранены в: {splitter.output_dir}")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()