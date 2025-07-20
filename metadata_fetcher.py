import requests
from rapidfuzz import fuzz
from collections import OrderedDict
from logger import *
from config import *  

logger = setup_logger("SCRAPER")

def author_match_score(hit_authors, author_list):
    """Compute the best fuzzy score between any hit author and your author list."""
    return max(
        fuzz.partial_ratio(hit.lower(), author.lower())
        for hit in hit_authors
        for author in author_list 
    ) if hit_authors else 0

def get_best_match_index(hits, author_list):
    """Return the index of the document with the highest author match score."""
    scores = [
        author_match_score(hit['document'].get('author_names', []), author_list)
        for hit in hits
    ]
    return scores.index(max(scores)) if scores else -1

def fetch_book_info(title, authors):
    if not hardcover_api_key:
      logger.critical("No Hardcover API KEY provided, please get it from here https://hardcover.app/account/api")
      raise SystemExit()
    query = f"""
    query SearchBook {{
      search(
        query: "{title}",
        query_type: "Book",
        per_page: 10,
        page: 1
      ) {{
        results
      }}
    }}
    """

    headers = {
        "Authorization": hardcover_api_key,
        "Content-Type": "application/json"
    }

    response = requests.post(api_url, json={"query": query}, headers=headers)
    data = response.json()
    if 'errors' in data or 'error' in data:
      logger.critical("Wrong Hardcover API KEY provided, please get it from here https://hardcover.app/account/api")
      raise SystemExit()
    
    hits = data['data']['search']['results']['hits']

    best_index = get_best_match_index(hits, authors)
    
    if best_index < 0:
        logger.error("No match from metadata provider")
        return None, title, authors, None, None, None
    
    document = data['data']['search']['results']['hits'][best_index]['document']

    logger.info(f"Best match: {document['title']} with id \"{document['id']}\"")

    book_info = {}
    series = None
    index = None
    authors = None
    date = None
    description = None  
    
    try:
      alternative_titles = document.get('alternative_titles', [])
      best_match = None
      highest_similarity = 0

      for alt_title in alternative_titles:
        if not alt_title: continue  # Skip empty titles
        similarity = fuzz.ratio(title.lower(), alt_title.lower())
        if similarity > highest_similarity:
            highest_similarity = similarity
            best_match = alt_title

      if document.get("featured_series") and document["featured_series"].get("series"):
        series = document["featured_series"]["series"].get("name")
        index = str(document["featured_series"].get("position"))
      authors = document.get("author_names", []) 
      date = document.get("release_date")
      description = document.get("description")

    except (KeyError, IndexError) as e:
      book_info["Error"] = f"Error parsing response: {e}"
      book_info["Response Text"] = response.text

    logger.info(f"🌐 ONLINE METADATA FETCHED:")
    log_metadata_section(logger, "", OrderedDict({
        "title": title,
        "authors": authors,
        "description": description,
        "date": date,
        "series": series,
        "index": index if index else None,  # Optional formatting
    }))

    return series, best_match, authors, index, date, description
