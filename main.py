import os, re, time, subprocess, glob
from ebooklib import epub
import colorlog 
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

SUCCESS_LEVEL_NUM = 25
logging.addLevelName(SUCCESS_LEVEL_NUM, "SUCCESS")
book_monitoring = os.getenv('BOOK_MONITORING', 'false').lower() == 'true'
manga_monitoring = os.getenv('MANGA_MONITORING', 'false').lower() == 'true'
scan_interval = int(os.getenv('MONITORING_INTERVAL', 30))
max_threads = int(os.getenv('MAX_THREADS', 4))
watch_directory = '/ebooks'
kcc_options = os.getenv('KCC_OPTIONS', '')

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

class EbookProcessor:
    def __init__(self, watch_directory, is_manga=False, stability_time=10, max_threads=4):
        self.watch_directory = watch_directory
        self.is_manga = is_manga
        self.stability_time = stability_time  # Time to wait for file stability
        self.max_threads = max_threads  # Number of threads to use

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
                #logger.info(f'Filename does not match expected manga pattern: {file_name}')
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

            #Process Ebook with KCC
            if kcc_options:
                command = f"python /usr/local/bin/kcc/kcc-c2e.py {kcc_options} \"{file_path}\" -o \"{os.path.dirname(file_path)}\"" 
                logger.success(f'{command}')
                subprocess.run(command, shell=True) 
                logger.success(f'{"KCC processed manga successfully"}')
            
                # Check for either .epub or .kepub.epub output
                output_dir = os.path.dirname(file_path)
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                new_file_path = None

                # Use glob to check for both potential output files
                for ext in ['.epub', '.kepub.epub']:
                    potential_file = os.path.join(output_dir, f"{base_name}{ext}")
                    if os.path.exists(potential_file):
                        new_file_path = potential_file
                        break

                if not new_file_path:
                    logger.error(f'KCC output file not found for {file_path}')
                    return
                else:
                    logger.success(f'KCC output file found: {new_file_path}')
                    file_path = new_file_path

            # Create folder structure and rename file
            if ext in ['.epub', '.kepub.epub']:
                folder_name = os.path.join(self.watch_directory, series)
                os.makedirs(folder_name, exist_ok=True)
                new_file_name = f"{title}{ext}"
                new_file_path = os.path.join(folder_name, new_file_name)
                os.rename(file_path, new_file_path)

                # Update metadata
                self.update_epub_metadata(new_file_path, series, series_index, title, authors)

                logger.success(f'Processed and renamed manga: {file_name} -> {new_file_path}')
            else:
                logger.success(f'File is not an epub')

        elif ext == ".epub":
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
            folder_name = os.path.join(self.watch_directory, title)
            os.makedirs(folder_name, exist_ok=True)
            new_file_name = f"{authors} - {title}{ext}"
            new_file_path = os.path.join(folder_name, new_file_name)
            os.rename(file_path, new_file_path)
            authors = [author.strip() for author in authors.split(',')]
            # Update metadata
            if len(parts) == 2:
                self.update_epub_metadata(new_file_path, '', '', title, authors)
            logger.success(f'Processed and renamed book: {file_name} -> {new_file_path}')

    def scan_directory(self):
        """Scan the directory for new files."""
        if self.is_manga:
            # Process all files for mangas
            files_to_process = [
                os.path.join(self.watch_directory, file_name)
                for file_name in os.listdir(self.watch_directory)
                if os.path.isfile(os.path.join(self.watch_directory, file_name))  # Process all files
            ]
        else:
            # Only process .epub and .kepub.epub files for books
            files_to_process = [
                os.path.join(self.watch_directory, file_name)
                for file_name in os.listdir(self.watch_directory)
                if file_name.endswith(('.kepub.epub', '.epub'))  # Only process EPUB files
            ]

        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            futures = [executor.submit(self.process_file, file_path) for file_path in files_to_process]
            for future in as_completed(futures):
                try:
                    future.result()  # This will raise any exceptions caught in the thread
                except Exception as e:
                    logger.error(f"Error processing file: {e}")

def start_monitoring(watch_directory, book_monitoring, manga_monitoring, stability_time=10, scan_interval=30, max_threads=4):
    books_folder = os.path.join(watch_directory, 'books')
    mangas_folder = os.path.join(watch_directory, 'mangas')
    if book_monitoring:
        if not os.path.exists(books_folder):
            logger.info(f'Books folder does not exist. Creating: {books_folder}')
            os.makedirs(books_folder, exist_ok=True)
        logger.info(f'Starting book scan on: {os.path.join(watch_directory, "books")}')
        processor_books = EbookProcessor(watch_directory=books_folder, is_manga=False, stability_time=stability_time, max_threads=max_threads)

    if manga_monitoring:
        if not os.path.exists(mangas_folder):
            logger.info(f'Mangas folder does not exist. Creating: {mangas_folder}')
            os.makedirs(mangas_folder, exist_ok=True)
        logger.info(f'Starting manga scan on: {os.path.join(watch_directory, "mangas")}')
        processor_mangas = EbookProcessor(watch_directory=mangas_folder, is_manga=True, stability_time=stability_time, max_threads=max_threads)

    try:
        while True:
            if book_monitoring:
                processor_books.scan_directory()

            if manga_monitoring:
                processor_mangas.scan_directory()

            time.sleep(scan_interval)
    except KeyboardInterrupt:
        logger.info("Monitoring stopped.")

if __name__ == "__main__":
    start_monitoring(watch_directory, book_monitoring, manga_monitoring, stability_time=10, scan_interval=scan_interval, max_threads=max_threads)
