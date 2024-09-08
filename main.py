import os
import re
import time
import threading
import ebooklib
from ebooklib import epub
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
    def __init__(self, watch_directory, is_manga=False, stability_time=2):
        self.watch_directory = watch_directory
        self.is_manga = is_manga
        self.stability_time = stability_time  # Time to wait for file stability

    def is_file_stable(self, file_path):
        """Check if the file size remains constant for a period of time."""
        try:
            initial_size = os.path.getsize(file_path)
            time.sleep(self.stability_time)
            final_size = os.path.getsize(file_path)
            return initial_size == final_size
        except FileNotFoundError:
            return False

    def update_epub_metadata(self, file_path, series, series_index, title, authors):
        try:
            # Load the EPUB file
            book = epub.read_epub(file_path)

            # Update the title if empty
            if not book.get_metadata('DC', 'title'):
                book.set_title(title)

            # Add the author metadata
            if not book.get_metadata('DC', 'creator'):
                for author in authors:
                    book.add_author(author)

            # Add the Kobo specific metadata for series and series index
            if series:
                # Generate series_id from series name
                series_id = series.lower().replace(" ", "-")
                book.add_metadata(None, 'meta', series, {'property': 'belongs-to-collection', 'id': series_id})
                book.add_metadata(None, 'meta', 'series', {'refines': f'#{series_id}', 'property': 'collection-type'})
                book.add_metadata(None, 'meta', series_index, {'refines': f'#{series_id}', 'property': 'group-position'})

            # Save the updated EPUB
            epub.write_epub(file_path, book)

        except Exception as e:
            logger.error(f"Error updating EPUB metadata: {e}")

    def process_file(self, file_path):
        """Process the file based on whether it's a book or manga."""
        file_name = os.path.basename(file_path)
        
        # Handle .kepub.epub and other extensions
        if file_name.endswith('.kepub.epub'):
            name = file_name[:-11]  # Remove ".kepub.epub" to get the base name
            ext = '.kepub.epub'
        else:
            name, ext = os.path.splitext(file_name)

        if self.is_manga:
            # Parse manga file name
            parts = re.split(r' - ', name, maxsplit=2)
            if len(parts) != 3:
                logger.info(f'Filename does not match expected manga pattern: {file_name}')
                return

            authors, series, title = parts
            chapter_number_match = re.search(r'Chapter (\d+)', title)
            chapter_number = chapter_number_match.group(1).lstrip('0') if chapter_number_match else ''

            volume_number_match = re.search(r'Vol\.?\s*(\d+)', title, re.IGNORECASE)
            volume_number = volume_number_match.group(1) if volume_number_match else ''

            # Prepare metadata
            authors = [author.strip() for author in authors.split(',')]
            title = title.strip()
            series = series.strip()
            chapter_number = chapter_number.strip()
            volume_number = volume_number.strip()
            if volume_number and chapter_number:
                series_index = f"{volume_number}.{chapter_number}"
            elif volume_number:
                series_index = volume_number
            elif chapter_number:
                series_index = chapter_number
            else:
                series_index = ''

            # Create folder structure and rename file
            folder_name = os.path.join(self.watch_directory, 'mangas', series)
            os.makedirs(folder_name, exist_ok=True)
            new_file_name = f"{series} - {title}{ext}"
            new_file_path = os.path.join(folder_name, new_file_name)
            os.rename(file_path, new_file_path)

            # Update metadata
            self.update_epub_metadata(new_file_path, series, series_index, title, authors)

            logger.success(f'Processed and renamed manga: /ebooks/mangas/{file_name} -> {folder_name}/{new_file_name}')

        else:
            # Process book files
            name = name.replace('_', ' ')
            name = re.sub(r'\s*[\;&,]\s*', ', ', name)  # Replace ; & , with ,
            name = re.sub(r'\s*\(.*?\)', '', name)  # Remove (XXXX)

            # Split authors and title
            parts = re.split(r' - ', name, maxsplit=1)
            if len(parts) != 2:
                logger.info(f'Filename does not match expected book pattern: {file_name}')
                book = epub.read_epub(file_path)
                title = book.get_metadata('DC', 'title')[0][0]
                authors = book.get_metadata('DC', 'creator')
                authors = [author[0] for author in authors]
                authors = ', '.join(authors)
            else:   
                authors, title = parts
            title = title.strip()            
            # Create folder structure and rename file
            folder_name = os.path.join(self.watch_directory, 'books', title)
            os.makedirs(folder_name, exist_ok=True)
            new_file_name = f"{authors} - {title}{ext}"
            new_file_path = os.path.join(folder_name, new_file_name)
            os.rename(file_path, new_file_path)
            authors = [author.strip() for author in authors.split(',')]
            # Update metadata
            if len(parts) == 2:
                self.update_epub_metadata(new_file_path, '', '', title, authors)
            logger.info(f'Processed and renamed book: {file_name} -> {folder_name}/{new_file_name}')

    def handle_new_file(self, file_path):
        """Handle new file creation in a thread."""
        if self.is_file_stable(file_path):
            self.process_file(file_path)
        else:
            logger.warning(f'File {file_path} was not stable, skipping processing.')

    def on_created(self, event):
        if os.path.isfile(event.src_path):
            logger.info(f'New file detected: {event.src_path}')
            # Start a new thread to handle file processing
            threading.Thread(target=self.handle_new_file, args=(event.src_path,)).start()

def start_monitoring(watch_directory, book_monitoring, manga_monitoring, stability_time=2):
    if book_monitoring:
        logger.info(f'Starting book monitoring on: {os.path.join(watch_directory, "books")}')
        event_handler_books = EbookHandler(watch_directory, is_manga=False, stability_time=stability_time)
        observer_books = Observer()
        observer_books.schedule(event_handler_books, path=os.path.join(watch_directory, 'books'), recursive=False)
        observer_books.start()

    if manga_monitoring:
        logger.info(f'Starting manga monitoring on: {os.path.join(watch_directory, "mangas")}')
        event_handler_mangas = EbookHandler(watch_directory, is_manga=True, stability_time=stability_time)
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

    start_monitoring(watch_directory, book_monitoring, manga_monitoring, stability_time=10)
