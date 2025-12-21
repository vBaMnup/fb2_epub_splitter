import xml.etree.ElementTree as ET
from ..constants import STYLE_RE, SCRIPT_RE, TAG_STRIP_RE, P_TAG_RE, H_TAG_RE


class HtmlTextExtractor:
    """Извлекает текст из HTML/XHTML контента

    Использует два метода:
    1. ElementTree для валидного XHTML (быстро)
    2. Regex для невалидного HTML (fallback)
    """

    def extract(self, html: str) -> tuple[str, str]:
        """Извлекает заголовок и текст из HTML

        Args:
            html: HTML контент

        Returns:
            Кортеж (title, text)
        """

        # Удаляем style и script
        html = STYLE_RE.sub("", html)
        html = SCRIPT_RE.sub("", html)

        # Извлекаем заголовок
        title = self._extract_title(html)

        # Пробуем быстрый парсинг через ElementTree
        text = self._extract_text_etree(html)
        if text:
            return title, text

        # Fallback на regex
        return title, self._extract_text_regex(html)

    def _extract_title(self, html: str) -> str:
        """
        Извлекает заголовок из HTML

        Args:
            html: HTML контент

        Returns:
            Заголовок
        """

        title_match = H_TAG_RE.search(html)
        if title_match:
            return TAG_STRIP_RE.sub("", title_match.group(1)).strip()
        return ""

    def _extract_text_etree(self, html: str) -> str | None:
        """
        Извлекает текст через ElementTree (для валидного XHTML)

        Args:
            html: HTML контент

        Returns:
            Текст
        """

        try:
            # Оборачиваем в root если нужно
            if not html.strip().startswith("<?xml"):
                html = f"<root>{html}</root>"

            root = ET.fromstring(html)
            paragraphs = root.findall(".//p")

            if not paragraphs:
                return None

            # Собираем текст из параграфов
            parts = []
            for p in paragraphs:
                text = "".join(p.itertext()).strip()
                if text:
                    parts.append(text)

            return "\n\n".join(parts) + "\n\n" if parts else None

        except ET.ParseError:
            return None

    def _extract_text_regex(self, html: str) -> str:
        """
        Извлекает текст через regex (fallback для невалидного HTML)

        Args:
            html: HTML контент

        Returns:
            Текст
        """

        paragraphs = P_TAG_RE.findall(html)

        parts = []
        for p in paragraphs:
            clean_p = TAG_STRIP_RE.sub("", p).strip()
            if clean_p:
                parts.append(clean_p)

        return "\n\n".join(parts) + "\n\n" if parts else ""
