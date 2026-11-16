import logging
from pathlib import Path

from core.load_settings import load_settings
from core.setup_logging import setup_logging

setup_logging()
settings = load_settings()
logger = logging.getLogger('ingestion')

INPUT_PATH = Path(settings['data']['raw_dir'])

def load_data(input_file: str | None = None) -> str:
    """Đọc file markdown/text và trả về nội dung dạng str."""
    if not input_file:
        logger.error("Input file name is missing")
        return ""

    input_file_path = INPUT_PATH / input_file
    if not input_file_path.exists():
        logger.error(f"Source file does not exist : {input_file_path}")
        return ""

    try:
        return input_file_path.read_text(encoding="utf-8")
    except Exception:
        logger.exception(f"Error occurred when readding file {input_file_path}")
        return ""


if __name__ == "__main__":
    print(load_data("s11858-023-01511-5.md")[:200])