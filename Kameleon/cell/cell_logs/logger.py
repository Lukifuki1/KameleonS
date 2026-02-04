import logging
import os

log_path = os.path.join(os.path.dirname(__file__), "cell.log")
os.makedirs(os.path.dirname(log_path), exist_ok=True)

logger = logging.getLogger("CELL")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.FileHandler(log_path)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

logger.info("Logger deluje pravilno.")
