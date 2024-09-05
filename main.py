import os
import re
import zipfile
import xml.etree.ElementTree as ET
import ebookmeta
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import colorlog 
import logging

SUCCESS_LEVEL_NUM = 25
logging.addLevelName(SUCCESS_LEVEL_NUM, "SUCCESS")

def success(self, message, *args, **kwargs):
    if self.isEnabledFor(SUCCESS_LEVEL_NUM):
        self._log(SUCCESS_LEVEL_NUM, message, args, **kwargs)

logging.Logger.success = success

# Configure logging with color
logger = colorlog.getLogger()
logger.setLevel(logging.INFO)
handler = colorlog.StreamHandler()
formatter = colorlog.ColoredFormatter(
    '%(asctime)s - %(levelname)s - %(message)s',
    log_colors={
        'DEBUG':    'cyan',
        'INFO':     'white',
        'SUCCESS':  'green',  # Color for SUCCESS level
        'WARNING':  'yellow',
        'ERROR':    'red',
        'CRITICAL': 'red,bg_white',
    }
)
handler.setFormatter(formatter)
logger.addHandler(handler)

class EbookHandler(FileSystemEventHandler):
    def __init__(self, watch_directory, is_manga=False):
        self.watch_directory = watch_directory
        self.is_manga = is_manga

    def get_epub_metadata(self, file_path):
        try:
            meta = ebookmeta.get_metadata(file_path)
            title = meta.title
            creators = meta.author_list
            series = meta.series
            series_index = meta.series_index
            return title, creators, series, series_index
        except Exception as e:
            logger.error(f"Error reading EPUB metadata: {e}")
            return '', [], '', ''

    def update_epub_metadata(self, file_path, series, series_index, title):
        try:
            # Update metadata using ebookmeta
            meta = ebookmeta.get_metadata(file_path)
            meta.title = title
            meta.series = series
            meta.series_index = series_index
            ebookmeta.set_metadata(file_path, meta)
            # logging.info(f'Metadata updated successfully in {file_path}')
        except Exception as e:
            logger.error(f"Error updating EPUB metadata: {e}")

    def process_file(self, file_path):
        # Extract file name and extension
        file_name = os.path.basename(file_path)
        name, ext = os.path.splitext(file_name)

        if self.is_manga:
            # Parse manga file name
            parts = re.split(r' - ', name, maxsplit=2)
            if len(parts) != 3:
                logger.info(f'Filename does not match expected manga pattern: {file_name}')
                return

            authors, series, chapter_title = parts
            chapter_number = re.search(r'Chapter (\d+)', chapter_title)
            if chapter_number:
                chapter_number = chapter_number.group(1)
                title = chapter_title.replace(f'Chapter {chapter_number} ', '')
            else:
                chapter_number = ''
                title = chapter_title

            # Prepare metadata
            authors = [author.strip() for author in authors.split(',')]
            title = title.strip()
            series = series.strip()
            series_index = chapter_number.strip()

            # Create folder structure and rename file
            folder_name = os.path.join(self.watch_directory, 'mangas', series)
            os.makedirs(folder_name, exist_ok=True)
            new_file_name = f"{series} - Chapter {chapter_number} {title}{ext}"
            new_file_path = os.path.join(folder_name, new_file_name)
            os.rename(file_path, new_file_path)

            # Update metadata
            self.update_epub_metadata(new_file_path, series, series_index, title)

            logger.success(f'Processed and renamed manga: /ebooks/mangas/{file_name} -> {folder_name}/{new_file_name}')

        else:
            # Process book files
            # Replace underscores with spaces, and handle author and title extraction
            name = name.replace('_', ' ')
            name = re.sub(r'\s*[\;&,]\s*', ', ', name)  # Replace ; & , with ,
            name = re.sub(r'\s*\(.*?\)', '', name)  # Remove (XXXX) if it matches the extension

            # Split authors and title
            parts = re.split(r' - ', name, maxsplit=1)
            if len(parts) != 2:
                logger.info(f'Filename does not match expected book pattern: {file_name}')
                return

            authors, title = parts
            authors = authors.strip()
            title = title.strip()

            # Extract metadata
            metadata_title, metadata_authors, _, _ = self.get_epub_metadata(file_path)
            
            if metadata_title:
                title = metadata_title
            if metadata_authors:
                authors = ', '.join(metadata_authors)

            # Create folder structure and rename file
            folder_name = os.path.join(self.watch_directory, 'books', title)
            os.makedirs(folder_name, exist_ok=True)
            new_file_name = f"{authors} - {title}{ext}"
            new_file_path = os.path.join(folder_name, new_file_name)
            os.rename(file_path, new_file_path)

            # Update metadata
            self.update_epub_metadata(new_file_path, '', '', title)

            logger.info(f'Processed and renamed book: /ebooks/books/{file_name} -> {folder_name}/{new_file_name}')

    def on_created(self, event):
        if os.path.isfile(event.src_path):
            logger.info(f'New file detected: {event.src_path}')
            self.process_file(event.src_path)

def start_monitoring(watch_directory, book_monitoring, manga_monitoring):
    if book_monitoring:
        logger.info(f'Starting book monitoring on: {os.path.join(watch_directory, "books")}')
        event_handler_books = EbookHandler(watch_directory, is_manga=False)
        observer_books = Observer()
        observer_books.schedule(event_handler_books, path=os.path.join(watch_directory, 'books'), recursive=False)
        observer_books.start()

    if manga_monitoring:
        logger.info(f'Starting manga monitoring on: {os.path.join(watch_directory, "mangas")}')
        event_handler_mangas = EbookHandler(watch_directory, is_manga=True)
        observer_mangas = Observer()
        observer_mangas.schedule(event_handler_mangas, path=os.path.join(watch_directory, 'mangas'), recursive=False)
        observer_mangas.start()

    try:
        while True:
            pass
    except KeyboardInterrupt:
        if book_monitoring:
            observer_books.stop()
        if manga_monitoring:
            observer_mangas.stop()
    if book_monitoring:
        observer_books.join()
    if manga_monitoring:
        observer_mangas.join()

if __name__ == "__main__":
    import os
    book_monitoring = os.getenv('BOOK_MONITORING', 'false').lower() == 'true'
    manga_monitoring = os.getenv('MANGA_MONITORING', 'false').lower() == 'true'
    watch_directory = '/ebooks'

    start_monitoring(watch_directory, book_monitoring, manga_monitoring)
