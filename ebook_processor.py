#ebook_processor.py
import os
import shutil
import subprocess
import re
from ebooklib import epub
from metadata_fetcher import fetch_book_info
from logger import *
from config import *
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = setup_logger("EBOOK PROCESSOR")

class EbookProcessor:
    def __init__(self, watch_directory, is_manga):
        self.watch_directory = watch_directory
        self.is_manga = is_manga
        self.stability_time = stability_time
        self.MAX_THREADS = MAX_THREADS

    def scan_directory(self):
        if self.is_manga:
            files_to_process = [
                os.path.join(root, file_name)
                for root, _, files in os.walk(self.watch_directory)
                for file_name in files
                if file_name.endswith('.cbz') 
            ]
        else:
            files_to_process = [
                os.path.join(root, file_name)
                for root, _, files in os.walk(self.watch_directory)
                for file_name in files
                if file_name.endswith(('.kepub.epub', '.epub'))
            ]

        with ThreadPoolExecutor(max_workers=self.MAX_THREADS) as executor:
            futures = [executor.submit(self.process_ebook, file_path) for file_path in files_to_process]
            for future in as_completed(futures):
                try:
                    future.result() 
                except Exception as e:
                    logger.error(f"Error processing file: {e}")

    def process_ebook(self, file_path):
        if self.is_manga:
            series, title, authors, index = self.extract_manga_metadata(file_path)
            if KCC_PROCESS:
                file_path = self.process_with_kcc(file_path, title, authors)
        elif not self.is_manga:
            series, title, authors, index, date, description = self.extract_book_metadata(file_path)
            if UPDATE_METADATA:
                fetched_series, fetched_title, fetched_authors, fetched_index, fetched_date, fetched_description = fetch_book_info(title, authors)
                self.update_metadata(
                    file_path,
                    current_metadata=(series, title, authors, index, date, description),
                    fetched_metadata=(fetched_series, fetched_title, fetched_authors, fetched_index, fetched_date, fetched_description)
                )
        self.rename_and_move_file(file_path, title, series)

    def extract_book_metadata(self, file_path):
        book = epub.read_epub(file_path)
        title = book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else None
        authors_raw = book.get_metadata('DC', 'creator')
        authors = [author[0] for author in authors_raw] if authors_raw else []
        description = book.get_metadata('DC', 'description')[0][0] if book.get_metadata('DC', 'description') else None
        date = book.get_metadata('DC', 'date')[0][0] if book.get_metadata('DC', 'date') else None
        index = book.get_metadata('OPF', 'calibre:series_index')[0][0] if book.get_metadata('OPF', 'calibre:series_index') else None
        series = book.get_metadata('OPF', 'calibre:series')[0][0] if book.get_metadata('OPF', 'calibre:series') else None

        log_metadata_section(logger, "EXTRACTED METADATA", {
            "title": title,
            "authors": authors,
            "description": description,
            "date": date,
            "series": series,
            "index": index if index else None
        })
        return series, title, authors, index, date, description

    def extract_manga_metadata(self, file_path):
        """Extract metadata for manga file."""
        file_name = os.path.basename(file_path)
        filename = file_name.replace('_', ' ').replace('.cbz', '').strip()
        chapter_match = re.search(r'(Chapter\s*\d+)(.*)', filename, re.IGNORECASE)

        if not chapter_match:
            return None
        chapter_str = chapter_match.group(1).strip()
        rest_of_title = chapter_match.group(2).strip()
        chapter_number = re.search(r'\d+', chapter_str).group()
        title = f"{chapter_str} {rest_of_title}".strip()

        prefix = filename[:chapter_match.start()].strip()
        author = None
        series = os.path.basename(os.path.dirname(file_path))
        if prefix:
            parts = [p.strip().rstrip('-').strip() for p in prefix.split(' - ')]
            if len(parts) == 2:
                author, series = parts  # Now it should capture 'Oda' as the author
            elif len(parts) == 1:
                series = parts[0]

        authors = [author.strip()] if author else []

        log_metadata_section(logger, "EXTRACTED METADATA", {
            "title": title,
            "authors": authors,
            "series": series,
            "index": chapter_number if chapter_number else None,  # Optional formatting
        })

        return series, title, authors, chapter_number

    def process_with_kcc(self, file_path, title, authors):
        """Process file using KCC tool."""
        logger.info(f'Launching KCC with options "{KCC_OPTIONS}"')
        output_dir = os.path.dirname(file_path)
        command = f'python3 {kcc_path}kcc-c2e.py "{file_path}" {KCC_OPTIONS} -d -o "{output_dir}" -t "{title}" -a "{", ".join(authors)}"'
        result = subprocess.run(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if result.returncode == 0:
            logger.info(f'KCC processed "{title}" successfully')
        else:
            logger.error(f'Error processing manga "{title}" with KCC, return code: {result.returncode}')
    
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        new_file_path = next(
            (
                os.path.join(output_dir, f)
                for f in os.listdir(output_dir)
                if f.startswith(base_name) and not f.endswith(".cbz")
            ),
            None
        )
        return new_file_path

    def update_metadata(self, file_path, current_metadata, fetched_metadata):
        curr_series, curr_title, curr_authors, curr_index, curr_date, curr_desc = current_metadata
        fetched_series, fetched_title, fetched_authors, fetched_index, fetched_date, fetched_desc = fetched_metadata

        book = epub.read_epub(file_path)

        # TITLE
        if not curr_title:
            if fetched_title:
                book.set_title(fetched_title)

        # AUTHORS
        if not curr_authors:
            if fetched_authors:
                for author in fetched_authors:
                    book.add_author(author)

        # SERIES
        if not curr_series:
            if fetched_series:
                series_id = fetched_series.lower().replace(" ", "-")
                book.add_metadata(None, 'meta', fetched_series, {'property': 'belongs-to-collection', 'id': series_id})
                if not curr_index:
                    if fetched_index:
                        book.add_metadata(None, 'meta', 'series', {'refines': f'#{series_id}', 'property': 'collection-type'})
                        book.add_metadata(None, 'meta', fetched_index, {'refines': f'#{series_id}', 'property': 'group-position'})

        # DESCRIPTION
        if not curr_desc:
            if fetched_desc:
                book.add_metadata('DC', 'description', fetched_desc)

        # DATE
        if not curr_date:
            if fetched_date:
                book.add_metadata('DC', 'date', fetched_date)

        log_metadata_section(logger, "UPDATED METADATA", {
            "title": fetched_title if not curr_title else None,
            "authors": fetched_authors if not curr_authors else None,
            "description": fetched_desc if not curr_desc else None,
            "date": fetched_date if not curr_date else None,
            "series": fetched_series if not curr_series else None,
            "index": fetched_index if not curr_index and fetched_index else None
        })

        epub.write_epub(file_path, book)

    def rename_and_move_file(self, file_path, title, series):
        if self.is_manga:
            output_path = os.path.join(output_directory, "mangas", series)
        else:
            output_path = os.path.join(output_directory, "books", title)
        os.makedirs(output_path, exist_ok=True)
        match = re.match(r"(.*?)(\.[^.]+(?:\.[^.]+)*)$", file_path)
        file_extension = match.group(2)
        new_file_name = f"{title}{file_extension}"
        new_output_path = os.path.join(output_path, new_file_name)
        shutil.move(file_path, new_output_path)
        logger.info(f'File renamed and moved to: {new_output_path}')
