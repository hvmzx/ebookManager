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
import zipfile
import xml.etree.ElementTree as ET
from epub_metadata_handler import edit_epub_metadata, extract_epub_metadata

logger = setup_logger("PROCESSOR")

class EbookProcessor:
    def __init__(self, watch_directory, is_manga):
        self.watch_directory = watch_directory
        self.is_manga = is_manga
        self.stability_time = stability_time
        self.max_threads = max_threads

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

        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            futures = [executor.submit(self.process_ebook, file_path) for file_path in files_to_process]
            for future in as_completed(futures):
                try:
                    future.result() 
                except Exception as e:
                    logger.error(f"Error processing file: {e}")

    def process_ebook(self, file_path):
        filename = os.path.basename(file_path)
        logger.info(f"{'='*60}")
        logger.info(f"PROCESSING {'MANGA' if self.is_manga else 'BOOK'}: {filename}")
        logger.info(f"{'='*60}")
        
        if self.is_manga:
            series, title, authors, index = self.extract_manga_metadata(file_path)
            if kcc_process:
                file_path = self.process_with_kcc(file_path, title, authors)
                logger.info(f'KCC processed file: {file_path}')
            if manga_update_metadata:
                edit_epub_metadata(
                    file_path,
                    current_metadata=(None, None, None, None, None, None),
                    fetched_metadata=(series, title, authors, index, None, None),
                    update_mode='partial'
                )
        elif not self.is_manga:
            series, title, authors, index, date, description = extract_epub_metadata(file_path) #self.extract_book_metadata(file_path)
            if book_update_metadata:
                fetched_series, fetched_title, fetched_authors, fetched_index, fetched_date, fetched_description = fetch_book_info(title, authors)
                edit_epub_metadata(
                    file_path,
                    current_metadata=(series, title, authors, index, date, description),
                    fetched_metadata=(fetched_series, fetched_title, fetched_authors, fetched_index, fetched_date, fetched_description),
                    update_mode='complete'
                )
                # Use the fetched metadata for filename (cleaner, updated data)
                title, authors, series = fetched_title, fetched_authors, fetched_series
        self.rename_and_move_file(file_path, title, series, authors)


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
        series = None if os.path.basename(os.path.dirname(file_path)).lower() == "mangas" else os.path.basename(os.path.dirname(file_path))
        if prefix:
            parts = [p.strip().rstrip('-').strip() for p in prefix.split(' - ')]
            if len(parts) == 2:
                author, series = parts  # Now it should capture 'Oda' as the author
            elif len(parts) == 1:
                series = parts[0]

        authors = [author.strip()] if author else []

        logger.info(f"📚 MANGA METADATA EXTRACTED:")
        log_metadata_section(logger, "", {
            "title": title,
            "authors": authors,
            "series": series,
            "index": chapter_number if chapter_number else None,  # Optional formatting
        })

        return series, title, authors, chapter_number

    def process_with_kcc(self, file_path, title, authors):
        """Process file using KCC tool."""
        logger.info(f'Launching KCC with options "{kcc_options}"')
        output_dir = os.path.dirname(file_path)
        command = f'python3 {kcc_path}kcc-c2e.py "{file_path}" {kcc_options} -d -o "{output_dir}" -t "{title}" -a "{", ".join(authors)}"'
        result = subprocess.run(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if result.returncode == 0:
            logger.info(f'KCC processed "{title}" successfully')
        else:
            logger.error(f'Error processing manga "{title}" with KCC, return code: {result.returncode}')
            return file_path  # Return original file if KCC processing fails
    
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        new_file_path = next(
            (
                os.path.join(output_dir, f)
                for f in os.listdir(output_dir)
                if f.startswith(base_name) and not f.endswith(".cbz")
            ),
            None
        )
        return new_file_path if new_file_path else file_path

    def rename_and_move_file(self, file_path, title, series, authors=None):
        filename = os.path.basename(file_path)
        
        if self.is_manga:
            output_path = os.path.join(output_directory, "mangas")
            if series:
                output_path = os.path.join(output_path, series)
            # For manga, use just the title as the filename
            new_file_name_base = title
        else:
            output_path = os.path.join(output_directory, "books")
            if title:
                output_path = os.path.join(output_path, title)
            # For books, use "Authors - Title" format
            if authors and len(authors) > 0:
                # Join multiple authors with " & " which is the standard for ebooks
                authors_str = " & ".join(authors)
                new_file_name_base = f"{authors_str} - {title}"
            else:
                new_file_name_base = title
        
        os.makedirs(output_path, exist_ok=True)
        
        # Get the proper file extension for ebooks
        if file_path.endswith('.kepub.epub'):
            file_extension = '.kepub.epub'
        elif file_path.endswith('.epub'):
            file_extension = '.epub'
        elif file_path.endswith('.cbz'):
            file_extension = '.cbz'
        else:
            # Fallback to the last extension for other file types
            file_extension = os.path.splitext(file_path)[1]
        
        new_file_name = f"{new_file_name_base}{file_extension}"
        new_output_path = os.path.join(output_path, new_file_name)
        # Get the original directory before moving
        original_dir = os.path.dirname(file_path)
        
        shutil.move(file_path, new_output_path)
        
        # Clean up empty directories after moving the file
        self.cleanup_empty_directories(original_dir)
        
        logger.info(f"{'='*60}")
        logger.info(f"✅ COMPLETED: {os.path.basename(new_output_path)}")
        logger.info(f"{'='*60}")

    def cleanup_empty_directories(self, dir_path):
        """
        Remove empty directories starting from dir_path and working up the tree.
        Stops when it encounters a non-empty directory or reaches the watch directory.
        """
        try:
            # Don't remove the watch directory itself
            if dir_path == self.watch_directory:
                return
            
            # Check if directory is empty
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                if not os.listdir(dir_path):  # Directory is empty
                    logger.info(f"🗑️  Removing empty directory: {dir_path}")
                    os.rmdir(dir_path)
                    
                    # Recursively check parent directory
                    parent_dir = os.path.dirname(dir_path)
                    if parent_dir != dir_path:  # Avoid infinite recursion
                        self.cleanup_empty_directories(parent_dir)
                        
        except Exception as e:
            logger.warning(f"Could not remove directory {dir_path}: {str(e)}")
