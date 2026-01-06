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
CHAPTER_PATTERNS_ANCHORED = [
    re.compile(r"^\s*глава[\s.:—-]*(\d+|[IVXLCDM]+)", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*часть[\s.:—-]*(\d+|[IVXLCDM]+)", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*раздел[\s.:—-]*(\d+|[IVXLCDM]+)", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*chapter[\s.:—-]*(\d+|[IVXLCDM]+)", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*part[\s.:—-]*(\d+|[IVXLCDM]+)", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*section[\s.:—-]*(\d+|[IVXLCDM]+)", re.IGNORECASE | re.MULTILINE),
]

# Бэкап—универсальные (без ^) — на случай, если нормализация не помогла
CHAPTER_PATTERNS_ANYWHERE = [
    re.compile(r"глава[\s.:—-]*(\d+|[IVXLCDM]+)", re.IGNORECASE),
    re.compile(r"часть[\s.:—-]*(\d+|[IVXLCDM]+)", re.IGNORECASE),
    re.compile(r"раздел[\s.:—-]*(\d+|[IVXLCDM]+)", re.IGNORECASE),
    re.compile(r"chapter[\s.:—-]*(\d+|[IVXLCDM]+)", re.IGNORECASE),
    re.compile(r"part[\s.:—-]*(\d+|[IVXLCDM]+)", re.IGNORECASE),
    re.compile(r"section[\s.:—-]*(\d+|[IVXLCDM]+)", re.IGNORECASE),
]


# FB2 namespace
FB2_NS = {"fb": "http://www.gribuser.ru/xml/fictionbook/2.0"}

# OPF namespace
OPF_NS = {"opf": "http://www.idpf.org/2007/opf"}
CONTAINER_NS = {"container": "urn:oasis:names:tc:opendocument:xmlns:container"}

# EPUB namespace
EPUB_NS = {"epub": "http://www.idpf.org/2007/ops"}
