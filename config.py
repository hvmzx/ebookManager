# config.py
import os

BOOK_MONITORING = os.getenv('BOOK_MONITORING', 'false')
MANGA_MONITORING = os.getenv('MANGA_MONITORING', 'false')
MONITORING_INTERVAL = int(os.getenv('MONITORING_INTERVAL', 60))
MAX_THREADS = int(os.getenv('MAX_THREADS', 4))
HARDCOVER_API_KEY=os.getenv('HARDCOVER_API_KEY', '')
UPDATE_METADATA=os.getenv('UPDATE_METADATA', 'false')
KCC_PROCESS=os.getenv('KCC_PROCESS', 'false')
KCC_OPTIONS = os.getenv('KCC_OPTIONS', '')

watch_directory =  '/app/ebooks/ebooks_in'
output_directory = '/app/ebooks/ebooks_out'
kcc_path = '/usr/local/bin/kcc/'
stability_time='10'
url = "https://api.hardcover.app/v1/graphql"