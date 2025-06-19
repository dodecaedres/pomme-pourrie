import logging
import json
from datetime import datetime

from sass_legal.core.config import settings

class JSONFormatter(logging.Formatter):
    """
    A custom logging formatter that outputs log records as JSON strings.

    This formatter includes standard log record attributes as well as a UTC timestamp.
    Exception information, if present, is also formatted and included.
    """
    def format(self, record: logging.LogRecord) -> str:
        """
        Formats the log record as a JSON string.

        Args:
            record: The LogRecord instance to format.

        Returns:
            A JSON string representation of the log record.
        """
        log_record = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(), # Formats the message with arguments
            "logger_name": record.name,
            "module": record.module,
            "funcName": record.funcName,
            "lineno": record.lineno,
        }
        # Add exception info if available
        if record.exc_info:
            # self.formatException is a method from logging.Formatter
            log_record["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            # self.formatStack is a method from logging.Formatter
            log_record["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(log_record, ensure_ascii=False)

def get_logger(name: str) -> logging.Logger:
    """
    Configures and returns a logger instance with a JSON formatter.

    The logger's level is determined by the `LOG_LEVEL` setting in the application's
    configuration. If an invalid level is specified, it defaults to INFO and logs a warning.
    The logger is configured not to propagate messages to the root logger to avoid
    duplicate logging if the root logger is also configured.

    Args:
        name: The name for the logger, typically `__name__` of the calling module.

    Returns:
        A configured `logging.Logger` instance.
    """
    logger = logging.getLogger(name)

    # Set level from settings - ensure it's valid
    level_name = settings.LOG_LEVEL.upper()
    level = logging.getLevelName(level_name)
    if not isinstance(level, int): # getLevelName returns the string itself if not found
        level = logging.INFO # Default to INFO if invalid level in settings
        logging.getLogger(__name__).warning(
            f"Invalid LOG_LEVEL '{settings.LOG_LEVEL}' in settings. Defaulting to INFO."
        )
    logger.setLevel(level)

    # Remove existing handlers to prevent duplicates if reconfigured
    if logger.hasHandlers():
        logger.handlers.clear()

    console_handler = logging.StreamHandler()
    formatter = JSONFormatter()
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    # Prevent log propagation to the root logger
    # This is important if the root logger has its own handlers (e.g., basicConfig is called elsewhere)
    # and we don't want duplicate messages.
    logger.propagate = False

    return logger

if __name__ == "__main__":
    # Example usage:
    # Create a .env file with LOG_LEVEL=DEBUG to test different levels
    # with open(".env", "w") as f:
    #     f.write("LOG_LEVEL=DEBUG\n")
    # settings.LOG_LEVEL = "DEBUG" # Or re-instantiate settings if it reads at init

    logger = get_logger("my_app_logger")

    logger.debug("This is a debug message.")
    logger.info("This is an info message.")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.")

    try:
        x = 1 / 0
    except ZeroDivisionError:
        logger.exception("Caught an exception (ERROR level automatically).")

    # To see the warning about invalid log level from get_logger itself:
    # original_level = settings.LOG_LEVEL
    # settings.LOG_LEVEL = "INVALID_LEVEL_TEST"
    # logger_test_invalid = get_logger("invalid_level_test_logger")
    # logger_test_invalid.info("Testing invalid level message - should not appear if level defaulted to INFO & this is info.")
    # settings.LOG_LEVEL = original_level # revert

    # import os
    # try:
    #     os.remove(".env")
    # except FileNotFoundError:
    #     pass
