from constants import FILENAME_CLEAN_RE


def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """
    Очищает имя файла от недопустимых символов

    Args:
        filename: Имя файла
        max_length: Максимальная длина имени файла

    Returns:
        Очищенное имя файла
    """

    # Убираем недопустимые символы
    filename = FILENAME_CLEAN_RE.sub("", filename)

    # Ограничиваем длину
    filename = filename[:max_length]

    # Убираем точки и пробелы в начале и конце
    filename = filename.strip(". ")

    return filename or "chapter"
