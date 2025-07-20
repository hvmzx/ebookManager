# config.py
import os

book_monitoring = os.getenv('BOOK_MONITORING', 'false')
manga_monitoring = os.getenv('MANGA_MONITORING', 'false')
scan_schedule = os.getenv('SCAN_SCHEDULE', '* * * * *')
max_threads = int(os.getenv('MAX_THREADS', 4))
hardcover_api_key = os.getenv('HARDCOVER_API_KEY', '')
book_update_metadata = os.getenv('BOOK_UPDATE_METADATA', 'false')
manga_update_metadata = os.getenv('MANGA_UPDATE_METADATA', 'false')
kcc_process = os.getenv('KCC_PROCESS', 'false')
kcc_options = os.getenv('KCC_OPTIONS', '')
update_mode = os.getenv('UPDATE_MODE', 'PARTIAL')
remove_prefix = os.getenv('REMOVE_PREFIX', 'false')
clean_title = os.getenv('CLEAN_TITLE', 'false')

watch_directory = '/app/ebooks/ebooks_in'
output_directory = '/app/ebooks/ebooks_out'
kcc_path = '/usr/local/bin/kcc/'
stability_time = '10'
api_url = "https://api.hardcover.app/v1/graphql"