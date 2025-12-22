import re

# Минимальная длина главы в символах
MIN_CHAPTER_LENGTH: int = 300

# Технические заголовки для пропуска
SKIP_TITLES: set = {
    "contents",
    "copyright",
    "table of contents",
    "toc",
    "содержание",
    "оглавление",
    "об авторе",
    "about the author",
    "acknowledgments",
    "благодарности",
    "dedication",
    "посвящение",
}

# Форматирование
SEPARATOR: str = "=" * 60

# Предкомпилированные регулярные выражения
TAG_STRIP_RE = re.compile(r"<[^>]+>")
STYLE_RE = re.compile(r"<style[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)
SCRIPT_RE = re.compile(r"<script[^>]*>.*?</script>", re.DOTALL | re.IGNORECASE)
P_TAG_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.DOTALL | re.IGNORECASE)
H_TAG_RE = re.compile(r"<h[1-6][^>]*>(.*?)</h[1-6]>", re.DOTALL | re.IGNORECASE)
FILENAME_CLEAN_RE = re.compile(r'[<>:"/\\|?*]')

# Паттерны для определения явных глав в тексте
CHAPTER_PATTERNS = [
    # Русские варианты
    re.compile(r"^глава\s+\d+", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^часть\s+\d+", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^раздел\s+\d+", re.IGNORECASE | re.MULTILINE),
    # Английские варианты
    re.compile(r"^chapter\s+\d+", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^part\s+\d+", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^section\s+\d+", re.IGNORECASE | re.MULTILINE),
    # Римские цифры
    re.compile(r"^глава\s+[IVXLCDM]+", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^chapter\s+[IVXLCDM]+", re.IGNORECASE | re.MULTILINE),
]

# FB2 namespace
FB2_NS = {"fb": "http://www.gribuser.ru/xml/fictionbook/2.0"}

# OPF namespace
OPF_NS = {"opf": "http://www.idpf.org/2007/opf"}
CONTAINER_NS = {"container": "urn:oasis:names:tc:opendocument:xmlns:container"}

# EPUB namespace
EPUB_NS = {"epub": "http://www.idpf.org/2007/ops"}
