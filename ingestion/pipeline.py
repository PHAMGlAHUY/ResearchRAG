from ingestion.load_data import load_data
from ingestion.chunking.chunker import split_text_into_chunks

import logging
from core.load_settings import load_settings
from core.setup_logging import setup_logging

from vectorstore.upsert import upsert_chunks

setup_logging()
settings = load_settings()
logger = logging.getLogger('ingestion')

input_file_path = "2005.11401v4.md"

def run_ingestion_pipeline():
    print("--- INITIATE PIPELINE INGESTION ---")
    raw_content = load_data(input_file_path)

    if raw_content:
        # Bước 2: Chunker xử lý
        chunks = split_text_into_chunks(raw_content, source=input_file_path)
        print(f"--- Completed: generated {len(chunks)} chunks for embedding! ---")

        upsert_chunks(chunks)
        logger.info("--- All chunks have been upserted to vector store ---")

    else:
        print("--- Failed: Unable to read source file! ---")
        return []


if __name__ == "__main__":
    run_ingestion_pipeline()