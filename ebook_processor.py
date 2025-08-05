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
            manga_metadata = self.extract_manga_metadata(file_path)
            if manga_metadata is None:
                logger.error(f"Could not extract metadata from manga file: {filename}")
                return
            series, title, authors, index, description, date = manga_metadata
            if kcc_process:
                file_path = self.process_with_kcc(file_path, title, authors)
                logger.info(f'KCC processed file: {file_path}')
            if manga_update_metadata:
                edit_epub_metadata(
                    file_path,
                    current_metadata=(None, None, None, None, None, None),
                    fetched_metadata=(series, title, authors, index, date, description),
                    update_mode='complete'
                )
        elif not self.is_manga:
            book_metadata = extract_epub_metadata(file_path) #self.extract_book_metadata(file_path)
            if book_metadata is None:
                logger.error(f"Could not extract metadata from book file: {filename}")
                return
            series, title, authors, index, date, description = book_metadata
            if book_update_metadata:
                fetched_series, fetched_title, fetched_authors, fetched_index, fetched_date, fetched_description = fetch_book_info(title, authors)
                if fetched_series is None:
                    logger.warning(f"No metadata found for book: {title}, skipping metadata update")
                else:
                    edit_epub_metadata(
                        file_path,
                        current_metadata=(series, title, authors, index, date, description),
                        fetched_metadata=(fetched_series, fetched_title, fetched_authors, fetched_index, fetched_date, fetched_description),
                        update_mode='complete'
                    )
                    # Use the fetched metadata for filename (cleaner, updated data)
                    title, authors, series = fetched_title, fetched_authors, fetched_series
        self.rename_and_move_file(file_path, title, series, authors)


    def extract_comicinfo_metadata(self, cbz_path):
        """Extract metadata from ComicInfo.xml inside a CBZ archive."""
        try:
            with zipfile.ZipFile(cbz_path, 'r') as z:
                if 'ComicInfo.xml' in z.namelist():
                    with z.open('ComicInfo.xml') as f:
                        tree = ET.parse(f)
                        root = tree.getroot()
                        def get(tag):
                            elem = root.find(tag)
                            return elem.text.strip() if elem is not None and elem.text else None
                        # Date handling
                        year = get('Year')
                        month = get('Month')
                        day = get('Day')
                        date = None
                        if year and month and day:
                            date = f"{year}-{int(month):02d}-{int(day):02d}"
                        elif year and month:
                            date = f"{year}-{int(month):02d}"
                        elif year:
                            date = year
                        # Authors
                        writers = get('Writer')
                        authors = [a.strip() for a in writers.split(',')] if writers else []
                        return {
                            'title': get('Title'),
                            'series': get('Series'),
                            'index': get('Number'),
                            'description': get('Summary'),
                            'authors': authors,
                            'date': date
                        }
        except Exception as e:
            logger.warning(f"Failed to extract ComicInfo.xml: {e}")
        return {}

    def extract_manga_metadata(self, file_path):
        file_name = os.path.basename(file_path)
        filename = file_name.replace('.cbz', '').strip()
        # Apply REMOVE_PREFIX if enabled
        if remove_prefix == 'true':
            underscore_pos = filename.find('_')
            if underscore_pos != -1:
                filename = filename[underscore_pos + 1:].strip()
                logger.info(f"Removed prefix, new filename: {filename}")
        # Extract series from directory name
        # Handle both mangas/series/chapter.cbz and mangas/source/series/chapter.cbz
        file_dir = os.path.dirname(file_path)
        parent_dir = os.path.dirname(file_dir)
        
        # If parent directory is "mangas", use the file's directory as series
        # If parent directory is not "mangas", use the file's directory as series (it's the series folder)
        series_dir = os.path.basename(file_dir)
        # 1. Try ComicInfo.xml first
        comicinfo = self.extract_comicinfo_metadata(file_path)
        # 2. Fallback to filename parsing
        # (existing filename parsing logic, but store results in fallback_*)
        volume_num = None
        chapter_num = None
        fallback_title = filename
        fallback_index = None
        vol_ch_match = re.search(r'(?:Vol(?:ume)?\.?\s*(\d+)),\s*(?:Ch(?:apter)?\.?\s*(\d+))', filename, re.IGNORECASE)
        if vol_ch_match:
            volume_num = vol_ch_match.group(1)
            chapter_num = vol_ch_match.group(2)
            fallback_index = chapter_num
            rest_of_title = filename[vol_ch_match.end():].strip()
            if rest_of_title.startswith('_'):
                rest_of_title = rest_of_title[1:].strip()
            if clean_title == 'true':
                fallback_title = f"Vol. {volume_num}"
                if rest_of_title:
                    fallback_title += f" - {rest_of_title}"
            else:
                fallback_title = f"Vol. {volume_num}, Ch. {chapter_num}"
                if rest_of_title:
                    fallback_title += f" - {rest_of_title}"
        else:
            vol_match = re.search(r'(?:Vol(?:ume)?\.?\s*(\d+))', filename, re.IGNORECASE)
            if vol_match:
                volume_num = vol_match.group(1)
                fallback_index = volume_num
                rest_of_title = filename[vol_match.end():].strip()
                if rest_of_title.startswith('_'):
                    rest_of_title = rest_of_title[1:].strip()
                if clean_title == 'true':
                    fallback_title = rest_of_title if rest_of_title else "Unknown Title"
                else:
                    fallback_title = f"Vol. {volume_num}"
                    if rest_of_title:
                        fallback_title += f" - {rest_of_title}"
            else:
                chapter_match = re.search(r'(?:Ch(?:apter)?\.?\s*(\d+))', filename, re.IGNORECASE)
                if chapter_match:
                    chapter_num = chapter_match.group(1)
                    fallback_index = chapter_num
                    rest_of_title = filename[chapter_match.end():].strip()
                    if rest_of_title.startswith('_'):
                        rest_of_title = rest_of_title[1:].strip()
                    if clean_title == 'true':
                        fallback_title = rest_of_title if rest_of_title else "Unknown Title"
                    else:
                        fallback_title = f"Ch. {chapter_num}"
                        if rest_of_title:
                            fallback_title += f" - {rest_of_title}"
                else:
                    fallback_title = filename
                    fallback_index = None
        # Authors from filename (if any)
        fallback_authors = []
        if ' - ' in filename:
            parts = [p.strip() for p in filename.split(' - ')]
            if len(parts) >= 3:
                fallback_authors = [parts[0]]
            elif len(parts) == 2:
                fallback_authors = [parts[0]]
        # Prefer ComicInfo fields, fallback to filename parsing
        title = comicinfo.get('title') or fallback_title
        series = comicinfo.get('series') or series_dir
        authors = comicinfo.get('authors') or fallback_authors
        index = comicinfo.get('index') or fallback_index
        description = comicinfo.get('description')
        date = comicinfo.get('date')
        logger.info(f"📚 MANGA METADATA EXTRACTED:")
        log_metadata_section(logger, "", {
            "title": title,
            "authors": authors,
            "series": series,
            "index": index,
            "description": description,
            "date": date,
        })
        return series, title, authors, index, description, date

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
        
        # Safety checks for None values
        if title is None:
            title = "Unknown Title"
        if series is None:
            series = ""
        if authors is None:
            authors = []
        
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
