from dataclasses import dataclass


@dataclass
class Chapter:
    """
    Класс для хранения информации о главе
    """

    index: int
    title: str
    text: str

    def is_valid(self, min_length: int) -> bool:
        """
        Проверяем является ли глава допустимой (минимальный размер)

        Args:
            min_length: Минимальная длина текста главы

        Returns:
            True, если глава допустима
        """

        return len(self.text) >= min_length

    def format_filename(self, sanitizer) -> str:
        """
        Форматируем имя файла главы

        Args:
            sanitizer: Объект санитизатора

        Returns:
            Форматированное имя файла
        """

        safe_title = (
            sanitizer.sanitize(self.title) if self.title else f"chapter_{self.index}"
        )
        return f"{self.index:03d}_{safe_title}.txt"

    def format_content(self, separator: str) -> str:
        """
        Форматируем содержимое главы

        Args:
            separator: Разделитель между заголовком и текстом

        Returns:
            Форматированное содержимое главы
        """

        return f"{separator}\n{self.title}\n{separator}\n\n{self.text}"
