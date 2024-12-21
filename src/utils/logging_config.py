import logging
from rich.logging import RichHandler

def setup_logging():
    FORMAT = "%(message)s"
    logging.basicConfig(
        level="INFO",
        format=FORMAT,
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, tracebacks_show_locals=True)]
    )
    return logging.getLogger("pos_revenue") 