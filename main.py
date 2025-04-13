import os, re, time, subprocess, shutil, logging, sys, warnings
from ebooklib import epub
from concurrent.futures import ThreadPoolExecutor, as_completed

SUCCESS_LEVEL_NUM = 25
book_monitoring = os.getenv('BOOK_MONITORING', 'false').lower() == 'true'
manga_monitoring = os.getenv('MANGA_MONITORING', 'false').lower() == 'true'
scan_interval = int(os.getenv('MONITORING_INTERVAL', 60))
max_threads = int(os.getenv('MAX_THREADS', 4))
watch_directory =  '/app/ebooks/ebooks_in'
output_directory = '/app/ebooks/ebooks_out'
kcc_options = os.getenv('KCC_OPTIONS', '')
kcc_path = '/usr/local/bin/kcc/'

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Create logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # Log everything from DEBUG and up

# Set up console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)  # Capture DEBUG logs too

# Optional: Format (you can customize this)
formatter = logging.Formatter('%(levelname)-8s: %(message)s')
console_handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(console_handler)

warnings.filterwarnings("ignore", module="ebooklib")


class EbookProcessor:
    def __init__(self, watch_directory, is_manga=False, stability_time=10, max_threads=4):
        self.watch_directory = watch_directory
        self.is_manga = is_manga
        self.stability_time = stability_time  # Time to wait for file stability
        self.max_threads = max_threads  # Number of threads to use

    def scan_directory(self):
        """Scan the directory for new files."""
        if self.is_manga:
            # Process all files for mangas, including those inside subfolders
            files_to_process = [
                os.path.join(root, file_name)
                for root, _, files in os.walk(self.watch_directory)
                for file_name in files
                if file_name.endswith('.cbz')  # Only process .cbz files
            ]
        else:
            # Only process .epub and .kepub.epub files for books
            files_to_process = [
                os.path.join(root, file_name)
                for root, _, files in os.walk(self.watch_directory)
                for file_name in files
                if file_name.endswith(('.kepub.epub', '.epub'))  # Only process EPUB files
            ]

        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            futures = [executor.submit(self.process_file, file_path) for file_path in files_to_process]
            for future in as_completed(futures):
                try:
                    future.result()  # This will raise any exceptions caught in the thread
                except Exception as e:
                    logger.error(f"Error processing file: {e}")

    def process_file(self, file_path):
        """Process the file based on whether it's a book or manga."""
        file_name = os.path.basename(file_path)
        # Handle .cbz manga files
        logger.info(self.is_manga)
        
        if self.is_manga and file_name.endswith('.cbz'):
            # Get the immediate parent folder (series name)
            series = os.path.basename(os.path.dirname(file_path))  # This is the series name
            
            # Clean up the filename to extract metadata
            filename = file_name.replace('_', ' ').replace('.cbz', '').strip()
            chapter_match = re.search(r'(Chapter\s*\d+)(.*)', filename, re.IGNORECASE)
            
            if not chapter_match:
                return None
            chapter_str = chapter_match.group(1).strip()
            rest_of_title = chapter_match.group(2).strip()
            chapter_number = re.search(r'\d+', chapter_str).group()

            title = f"{chapter_str} {rest_of_title}".strip()

            # Handle the part before "Chapter"
            prefix = filename[:chapter_match.start()].strip()

            author = None

            # If there's a prefix, try to extract author
            if prefix:
                parts = [p.strip().rstrip('-').strip() for p in prefix.split(' - ')]
                if len(parts) == 2:
                    author, series = parts  # Now it should capture 'Oda' as the author
                elif len(parts) == 1:
                    series = parts[0]

            # Prepare metadata
            authors = [author.strip()] if author else []
            title = title.strip()
            chapter_number = chapter_number.strip()
            series_index = chapter_number
            logger.debug(f"METADATA PARSED: Authors: {authors} | Title: {title} | Chapter: {chapter_number} | Index: {series_index}")
            
            # Process the file using KCC if necessary
            #output_path = os.path.join(output_path, {series})
            output_path = os.path.join(output_directory, "mangas", series)
            os.makedirs(output_path, exist_ok=True)
            logger.info(f"Manga \"{title}\" found")
            if kcc_options:
                output_dir = os.path.dirname(file_path)
                command = f'python3 {kcc_path}kcc-c2e.py "{file_path}" {kcc_options} -d -o \"{output_dir}\" -t \"{title}\" -a \"{', '.join(authors)}\"'
                #logger.debug(f"KCC CMD: {command}")
                result = subprocess.run(command, shell=True, cwd=os.path.dirname(kcc_path), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if result.returncode == 0:
                    logger.info(f'KCC processed \"{title}\" successfully')
                else:
                    logger.error(f'Error processing manga \"{title}\" with KCC, return code: {result.returncode}')
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                new_file_path = next(
                    (
                        os.path.join(output_dir, f)
                        for f in os.listdir(output_dir)
                        if f.startswith(base_name) and not f.endswith(".cbz")
                    ),
                    None
                )

                # Extract the file extension
                match = re.match(r"(.*?)(\.[^.]+(?:\.[^.]+)*)$", new_file_path)
                base_name = match.group(1)
                file_extension = match.group(2)

                # Create the new file name with the extension
                new_file_name = f"{title}{file_extension}"

                # Construct the new file path
                new_output_path = os.path.join(output_path, new_file_name)
                # Rename the file
                shutil.move(new_file_path, new_output_path)
                
                # Update metadata
                self.update_epub_metadata(new_output_path, series, series_index, title, authors)

                logger.info(
                    f'Manga "{title}" metadata updated and moved to output directory'
                )
        elif not self.is_manga and file_name.endswith('.epub'):
            logger.debug("Processing book")
            book = epub.read_epub(file_path)
            title = book.get_metadata('DC', 'title')[0][0]
            authors = book.get_metadata('DC', 'creator')
            authors = [author[0] for author in authors]
            authors = ', '.join(authors)
            logger.debug(f"METADATA PARSED: Authors: {authors} | Title: {title}")
            
            output_path = os.path.join(output_directory, "books", title)
            os.makedirs(output_path, exist_ok=True)
            new_output_path = os.path.join(output_path, f"{title}.epub")
            
            shutil.move(file_path, new_output_path)

            logger.info(
                f'Book "{title}" has been moved to output directory'
            )
            
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

def start_monitoring(watch_directory, book_monitoring, manga_monitoring, stability_time=10, scan_interval=30, max_threads=4):
    os.makedirs(watch_directory, exist_ok=True)
    os.makedirs(output_directory, exist_ok=True)

    books_folder_in = os.path.join(watch_directory, 'books')
    mangas_folder_in = os.path.join(watch_directory, 'mangas')
    os.makedirs(books_folder_in, exist_ok=True)
    os.makedirs(mangas_folder_in, exist_ok=True)

    books_folder_out = os.path.join(output_directory, 'books')
    mangas_folder_out = os.path.join(output_directory, 'mangas')
    os.makedirs(books_folder_out, exist_ok=True)
    os.makedirs(mangas_folder_out, exist_ok=True)

    if book_monitoring:
        logger.info("Book monitoring enabled.")
        if not os.path.exists(books_folder_in):
            logger.info(f'Books folder does not exist. Creating: {books_folder_in}')
            os.makedirs(books_folder_in, exist_ok=True)
        processor_books = EbookProcessor(watch_directory=books_folder_in, is_manga=False, stability_time=stability_time, max_threads=max_threads)

    if manga_monitoring:
        logger.info("Manga monitoring enabled.")
        if not os.path.exists(mangas_folder_in):
            logger.info(f'Mangas folder does not exist. Creating: {mangas_folder_in}')
            os.makedirs(mangas_folder_in, exist_ok=True)
        processor_mangas = EbookProcessor(watch_directory=mangas_folder_in, is_manga=True, stability_time=stability_time, max_threads=max_threads)

    try:
        while True:
            if book_monitoring:
                processor_books.scan_directory()

            if manga_monitoring:
                processor_mangas.scan_directory()

            logger.debug(f'Waiting for {scan_interval} seconds before checking again')
            time.sleep(scan_interval)
    except KeyboardInterrupt:
        logger.debug("Monitoring stopped.")

if __name__ == "__main__":
    start_monitoring(watch_directory, book_monitoring, manga_monitoring, stability_time=10, scan_interval=scan_interval, max_threads=max_threads)