import logging


def setup_logging(level=logging.INFO) -> logging.Logger:
    """
    Настраиваем логгирование для приложения

    Args:
        level: Уровень логирования

    Returns:
        Объект логгера
    """

    logging.basicConfig(level=level, format="%(message)s")

    return logging.getLogger(__name__)
