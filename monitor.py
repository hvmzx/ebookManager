import os
from ebook_processor import EbookProcessor
import logging
import time
from logger import setup_logger
from config import *

logger = setup_logger("MONITOR")

def start_monitoring():
    os.makedirs(watch_directory, exist_ok=True)
    os.makedirs(output_directory, exist_ok=True)

    books_folder_in = os.path.join(watch_directory, 'books')
    mangas_folder_in = os.path.join(watch_directory, 'mangas')
    os.makedirs(books_folder_in, exist_ok=True)
    os.makedirs(mangas_folder_in, exist_ok=True)

    if BOOK_MONITORING:
        processor_books = EbookProcessor(watch_directory=books_folder_in, is_manga=False)

    if MANGA_MONITORING:
        processor_mangas = EbookProcessor(watch_directory=mangas_folder_in, is_manga=True)

    try:
        while True:
            if BOOK_MONITORING:
                processor_books.scan_directory()
            if MANGA_MONITORING:
                processor_mangas.scan_directory()

            if MONITORING_INTERVAL == 0:
                logger.info("Scan complete. Monitoring stopped due to 0 scan interval.")
                break
            else:
                logger.info(f'Waiting for {MONITORING_INTERVAL} seconds before checking again')
                time.sleep(MONITORING_INTERVAL)
    except KeyboardInterrupt:
        logger.debug("Monitoring stopped.")