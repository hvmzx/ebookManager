import os
import zipfile
import xml.etree.ElementTree as ET
import shutil
from collections import OrderedDict
from logger import *

logger = setup_logger("UPDATER")

def edit_epub_metadata(epub_path, current_metadata, fetched_metadata, update_mode):
    """
    Edit EPUB metadata by directly modifying the OPF file.
    
    Args:
        epub_path (str): Path to the EPUB file
        current_metadata (tuple): Current metadata in the format (series, title, authors, index, date, description)
        fetched_metadata (tuple): Fetched metadata in the format (series, title, authors, index, date, description)
        update_mode (str): Either 'partial' or 'complete'
            - partial: Only update metadata that is not present
            - complete: Replace all metadata with fetched values
    """
    try:
        # Log fetched metadata before making changes
        fetched_series, fetched_title, fetched_authors, fetched_index, fetched_date, fetched_desc = fetched_metadata
        
        # Create a temporary directory to work with the EPUB contents
        temp_dir = "temp_epub"
        os.makedirs(temp_dir, exist_ok=True)
        
        # Extract the EPUB
        with zipfile.ZipFile(epub_path, 'r') as epub_zip:
            epub_zip.extractall(temp_dir)
        
        # Find the OPF file
        container_path = os.path.join(temp_dir, 'META-INF', 'container.xml')
        container_tree = ET.parse(container_path)
        container_root = container_tree.getroot()
        
        # Get the path to the OPF file
        opf_path = None
        for rootfile in container_root.findall('.//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile'):
            opf_path = os.path.join(temp_dir, rootfile.get('full-path'))
            break
        
        if not opf_path:
            raise Exception("Could not find OPF file in container.xml")
        
        # Parse the OPF file
        opf_tree = ET.parse(opf_path)
        opf_root = opf_tree.getroot()
        
        # Define namespaces
        namespaces = {
            'opf': 'http://www.idpf.org/2007/opf',
            'dc': 'http://purl.org/dc/elements/1.1/'
        }
        
        # Update metadata
        metadata_elem = opf_root.find('.//opf:metadata', namespaces)
        if metadata_elem is None:
            raise Exception("Could not find metadata section in OPF file")
        
        # Unpack metadata
        curr_series, curr_title, curr_authors, curr_index, curr_date, curr_desc = current_metadata
        fetched_series, fetched_title, fetched_authors, fetched_index, fetched_date, fetched_desc = fetched_metadata
        
        # Track which metadata was updated
        updated_metadata = {}
        
        # Update title
        if update_mode == 'complete' and curr_title != fetched_title:
            title_elem = metadata_elem.find('.//dc:title', namespaces)
            if title_elem is not None:
                title_elem.text = fetched_title
            else:
                title_elem = ET.SubElement(metadata_elem, '{http://purl.org/dc/elements/1.1/}title')
                title_elem.text = fetched_title
            updated_metadata['title'] = fetched_title
        elif update_mode == 'partial' and not curr_title:
            title_elem = metadata_elem.find('.//dc:title', namespaces)
            if title_elem is not None:
                title_elem.text = fetched_title
            else:
                title_elem = ET.SubElement(metadata_elem, '{http://purl.org/dc/elements/1.1/}title')
                title_elem.text = fetched_title
            updated_metadata['title'] = fetched_title
        
        # Update authors
        if update_mode == 'complete' and curr_authors != fetched_authors:
            # Remove existing authors
            for creator in metadata_elem.findall('.//dc:creator', namespaces):
                metadata_elem.remove(creator)
            # Add new authors
            for author in fetched_authors:
                creator_elem = ET.SubElement(metadata_elem, '{http://purl.org/dc/elements/1.1/}creator')
                creator_elem.text = author
            updated_metadata['authors'] = fetched_authors
        elif update_mode == 'partial' and not curr_authors:
            # Remove existing authors
            for creator in metadata_elem.findall('.//dc:creator', namespaces):
                metadata_elem.remove(creator)
            # Add new authors
            for author in fetched_authors:
                creator_elem = ET.SubElement(metadata_elem, '{http://purl.org/dc/elements/1.1/}creator')
                creator_elem.text = author
            updated_metadata['authors'] = fetched_authors
        
        # Update description
        if update_mode == 'complete' and curr_desc != fetched_desc:
            desc_elem = metadata_elem.find('.//dc:description', namespaces)
            if desc_elem is not None:
                desc_elem.text = fetched_desc
            else:
                desc_elem = ET.SubElement(metadata_elem, '{http://purl.org/dc/elements/1.1/}description')
                desc_elem.text = fetched_desc
            updated_metadata['description'] = fetched_desc
        elif update_mode == 'partial' and not curr_desc:
            desc_elem = metadata_elem.find('.//dc:description', namespaces)
            if desc_elem is not None:
                desc_elem.text = fetched_desc
            else:
                desc_elem = ET.SubElement(metadata_elem, '{http://purl.org/dc/elements/1.1/}description')
                desc_elem.text = fetched_desc
            updated_metadata['description'] = fetched_desc
        
        # Update series information
        if update_mode == 'complete' and curr_series != fetched_series:
            # Remove existing series metadata
            for meta in metadata_elem.findall('.//opf:meta[@name="calibre:series"]', namespaces):
                metadata_elem.remove(meta)
            for meta in metadata_elem.findall('.//opf:meta[@name="series"]', namespaces):
                metadata_elem.remove(meta)
            
            if fetched_series:
                # Add series metadata
                series_elem = ET.SubElement(metadata_elem, '{http://www.idpf.org/2007/opf}meta')
                series_elem.set('name', 'calibre:series')
                series_elem.set('content', fetched_series)
                updated_metadata['series'] = fetched_series
        elif update_mode == 'partial' and not curr_series:
            # Remove existing series metadata
            for meta in metadata_elem.findall('.//opf:meta[@name="calibre:series"]', namespaces):
                metadata_elem.remove(meta)
            for meta in metadata_elem.findall('.//opf:meta[@name="series"]', namespaces):
                metadata_elem.remove(meta)
            
            if fetched_series:
                # Add series metadata
                series_elem = ET.SubElement(metadata_elem, '{http://www.idpf.org/2007/opf}meta')
                series_elem.set('name', 'calibre:series')
                series_elem.set('content', fetched_series)
                updated_metadata['series'] = fetched_series
        
        # Update series index separately
        if update_mode == 'complete' and curr_index != fetched_index:
            # Remove existing series index metadata
            for meta in metadata_elem.findall('.//opf:meta[@name="calibre:series_index"]', namespaces):
                metadata_elem.remove(meta)
            for meta in metadata_elem.findall('.//opf:meta[@name="series_index"]', namespaces):
                metadata_elem.remove(meta)
            
            if fetched_index:
                index_elem = ET.SubElement(metadata_elem, '{http://www.idpf.org/2007/opf}meta')
                index_elem.set('name', 'calibre:series_index')
                index_elem.set('content', str(fetched_index))
                updated_metadata['index'] = fetched_index
        elif update_mode == 'partial' and not curr_index:
            # Remove existing series index metadata
            for meta in metadata_elem.findall('.//opf:meta[@name="calibre:series_index"]', namespaces):
                metadata_elem.remove(meta)
            for meta in metadata_elem.findall('.//opf:meta[@name="series_index"]', namespaces):
                metadata_elem.remove(meta)
            
            if fetched_index:
                index_elem = ET.SubElement(metadata_elem, '{http://www.idpf.org/2007/opf}meta')
                index_elem.set('name', 'calibre:series_index')
                index_elem.set('content', str(fetched_index))
                updated_metadata['index'] = fetched_index
        
        # Update date
        if update_mode == 'complete' and curr_date != fetched_date:
            date_elem = metadata_elem.find('.//dc:date', namespaces)
            if date_elem is not None:
                date_elem.text = fetched_date
            else:
                date_elem = ET.SubElement(metadata_elem, '{http://purl.org/dc/elements/1.1/}date')
                date_elem.text = fetched_date
            updated_metadata['date'] = fetched_date
        elif update_mode == 'partial' and not curr_date:
            date_elem = metadata_elem.find('.//dc:date', namespaces)
            if date_elem is not None:
                date_elem.text = fetched_date
            else:
                date_elem = ET.SubElement(metadata_elem, '{http://purl.org/dc/elements/1.1/}date')
                date_elem.text = fetched_date
            updated_metadata['date'] = fetched_date
        
        # Save the modified OPF file
        opf_tree.write(opf_path, encoding='utf-8', xml_declaration=True)
        
        # Create a new EPUB with the modified contents
        with zipfile.ZipFile(epub_path, 'w') as new_epub:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    new_epub.write(file_path, arcname)
        
        # Clean up
        shutil.rmtree(temp_dir)
        
        # Log only the updated metadata using the same format as fetched metadata
        updated_fields = OrderedDict({key: value for key, value in {
            "title": updated_metadata.get('title'),
            "authors": updated_metadata.get('authors'),
            "description": updated_metadata.get('description'),
            "date": updated_metadata.get('date'),
            "series": updated_metadata.get('series'),
            "index": updated_metadata.get('index')
        }.items() if value is not None})
        
        if updated_fields:
            # Log which fields were updated
            updated_field_names = list(updated_fields.keys())
            logger.info(f"✅ METADATA UPDATE COMPLETED:")
            logger.info(f"Updated Fields: {updated_field_names}")
            log_metadata_section(logger, "", updated_fields)
        else:
            logger.info(f"ℹ️  METADATA STATUS:")
            logger.info("Updated Fields: []")
            log_metadata_section(logger, "", {"message": "No metadata was updated"})
        
    except Exception as e:
        logger.error(f"Error updating EPUB metadata: {str(e)}")
        # Clean up on error
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir) 

def extract_epub_metadata(epub_path):
    """
    Extract metadata from an EPUB file using XML parsing.
    
    Args:
        epub_path (str): Path to the EPUB file
        
    Returns:
        tuple: (series, title, authors, index, date, description)
    """
    try:
        # Create a temporary directory to work with the EPUB contents
        temp_dir = "temp_epub"
        os.makedirs(temp_dir, exist_ok=True)
        
        # Extract the EPUB
        with zipfile.ZipFile(epub_path, 'r') as epub_zip:
            epub_zip.extractall(temp_dir)
        
        # Find the OPF file
        container_path = os.path.join(temp_dir, 'META-INF', 'container.xml')
        container_tree = ET.parse(container_path)
        container_root = container_tree.getroot()
        
        # Get the path to the OPF file
        opf_path = None
        for rootfile in container_root.findall('.//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile'):
            opf_path = os.path.join(temp_dir, rootfile.get('full-path'))
            break
        
        if not opf_path:
            raise Exception("Could not find OPF file in container.xml")
        
        # Parse the OPF file
        opf_tree = ET.parse(opf_path)
        opf_root = opf_tree.getroot()
        
        # Define namespaces
        namespaces = {
            'opf': 'http://www.idpf.org/2007/opf',
            'dc': 'http://purl.org/dc/elements/1.1/'
        }
        
        # Get metadata
        metadata_elem = opf_root.find('.//opf:metadata', namespaces)
        if metadata_elem is None:
            raise Exception("Could not find metadata section in OPF file")
        
        # Extract title
        title_elem = metadata_elem.find('.//dc:title', namespaces)
        title = title_elem.text if title_elem is not None else None
        
        # Extract authors
        authors = []
        for creator in metadata_elem.findall('.//dc:creator', namespaces):
            if creator.text:
                authors.append(creator.text)
        
        # Extract description
        desc_elem = metadata_elem.find('.//dc:description', namespaces)
        description = desc_elem.text if desc_elem is not None else None
        
        # Extract date
        date_elem = metadata_elem.find('.//dc:date', namespaces)
        date = date_elem.text if date_elem is not None else None
        
        # Extract series
        series = None
        series_elem = metadata_elem.find('.//opf:meta[@name="calibre:series"]', namespaces)
        if series_elem is None:
            series_elem = metadata_elem.find('.//opf:meta[@name="series"]', namespaces)
        if series_elem is not None:
            series = series_elem.get('content')
        
        # Extract series index
        index = None
        index_elem = metadata_elem.find('.//opf:meta[@name="calibre:series_index"]', namespaces)
        if index_elem is None:
            index_elem = metadata_elem.find('.//opf:meta[@name="series_index"]', namespaces)
        if index_elem is not None:
            index = index_elem.get('content')
        
        # Clean up
        shutil.rmtree(temp_dir)
        
        # Log the extracted metadata (same order as fetched metadata)
        logger.info(f"📖 CURRENT EPUB METADATA:")
        log_metadata_section(logger, "", OrderedDict({
            "title": title,
            "authors": authors,
            "description": description,
            "date": date,
            "series": series,
            "index": index if index else None
        }))
        
        return series, title, authors, index, date, description
        
    except Exception as e:
        logger.error(f"Error extracting EPUB metadata: {str(e)}")
        # Clean up on error
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return None, None, [], None, None, None 