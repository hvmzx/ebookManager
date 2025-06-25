import os
import time
from datetime import datetime
from ebook_processor import EbookProcessor
from config import book_monitoring, manga_monitoring, scan_schedule, watch_directory
from logger import setup_logger
import croniter

logger = setup_logger("MONITOR")

def get_next_run_time(last_run):
    """Get the next scheduled run time based on the cron schedule."""
    if not last_run:
        return datetime.now()
    
    cron = croniter.croniter(scan_schedule, last_run)
    return cron.get_next(datetime)

def format_seconds(seconds):
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")
    return ' '.join(parts)

def start_monitoring(watch_directory):
    books_folder = os.path.join(watch_directory, 'books')
    mangas_folder = os.path.join(watch_directory, 'mangas')
    
    logger.info(f"Watch directory: {watch_directory}")
    logger.info(f"Books input folder: {books_folder}")
    logger.info(f"Manga input folder: {mangas_folder}")
    
    # Create directories if they don't exist
    os.makedirs(books_folder, exist_ok=True)
    os.makedirs(mangas_folder, exist_ok=True)
    
    # Initialize processors
    processor_books = None
    processor_mangas = None
    
    if book_monitoring:
        logger.info('Starting book monitoring...')
        processor_books = EbookProcessor(watch_directory=books_folder, is_manga=False)
    
    if manga_monitoring:
        logger.info('Starting manga monitoring...')
        processor_mangas = EbookProcessor(watch_directory=mangas_folder, is_manga=True)
    
    last_run = None
    
    while True:
        try:
            current_time = datetime.now()
            next_run = get_next_run_time(last_run)
            
            if current_time >= next_run:
                logger.info('Starting scheduled scan...')
                
                if book_monitoring:
                    logger.debug("Checking books directory...")
                    book_files = [
                        os.path.join(root, file_name)
                        for root, _, files in os.walk(books_folder)
                        for file_name in files
                        if file_name.endswith(('.kepub.epub', '.epub'))
                    ]
                    book_count = len(book_files)
                    logger.debug(f"Found {book_count} book {'file' if book_count == 1 else 'files'}: {[os.path.basename(f) for f in book_files]}")
                    processor_books.scan_directory()
                
                if manga_monitoring:
                    logger.debug("Checking manga directory...")
                    manga_files = [
                        os.path.join(root, file_name)
                        for root, _, files in os.walk(mangas_folder)
                        for file_name in files
                        if file_name.endswith('.cbz')
                    ]
                    manga_count = len(manga_files)
                    logger.debug(f"Found {manga_count} manga {'file' if manga_count == 1 else 'files'}: {[os.path.basename(f) for f in manga_files]}")
                    processor_mangas.scan_directory()
                
                last_run = current_time
                logger.info('Scheduled scan completed')
            else:
                # Calculate seconds until next run
                sleep_seconds = (next_run - current_time).total_seconds()
                logger.info(f'Next scan scheduled in {format_seconds(sleep_seconds)}')
                time.sleep(sleep_seconds)
            
        except KeyboardInterrupt:
            logger.info('Monitoring stopped by user')
            break
        except Exception as e:
            logger.error(f'Error during monitoring: {e}')
            # On error, wait 5 minutes before retrying
            time.sleep(300)

if __name__ == '__main__':
    logger.info("Starting monitor with configuration:")
    logger.info(f"Book monitoring: {book_monitoring}")
    logger.info(f"Manga monitoring: {manga_monitoring}")
    logger.info(f"Scan schedule: {scan_schedule}")
    start_monitoring(watch_directory)