# ebookManager

ebookManager is made to fill metadata into epubs from the filename, and rename ebooks from the metadata if it's present. This allows one to correctly have their ebooks recognised by their e-readers and software like Komga/Kavita.

## Installation

For a simple docker run : 

```bash
docker run --name ebookmanager --restart unless-stopped \
  -v /input/ebooks:/app/ebooks/ebooks_in \
  -v /output/ebooks:/app/ebooks/ebooks_out \
  -e MANGA_MONITORING='false' \
  -e BOOK_MONITORING='false' \
  -e SCAN_SCHEDULE='0 0 * * *' \
  ghcr.io/hvmzx/ebookmanager:dev
```

For docker-compose :

```yaml
version: '3.8'

services:
  ebookmanager:
    container_name: ebookmanager
    image: ghcr.io/hvmzx/ebookmanager:dev
    environment:
      - MANGA_MONITORING=false
      - BOOK_MONITORING=false
      - SCAN_SCHEDULE=0 0 * * *
    volumes:
      - /input/ebooks:/app/ebooks/ebooks_in
      - /output/ebooks:/app/ebooks/ebooks_out
```


## Environment Variables

Add these to your `.env` file or `docker-compose.yml` as needed, the default value is as follows:

### Core Settings
```
MANGA_MONITORING=false    # Enable manga folder monitoring
BOOK_MONITORING=false     # Enable book folder monitoring  
SCAN_SCHEDULE=* * * * *   # Cron schedule for scanning
```

### Metadata Settings
```
HARDCOVER_API_KEY=        # API key for book metadata fetching
BOOK_UPDATE_METADATA=false    # Update book metadata
MANGA_UPDATE_METADATA=false   # Update manga metadata
UPDATE_MODE=PARTIAL       # PARTIAL | complete
REMOVE_PREFIX=false       # Remove prefix before underscore for manga files
CLEAN_TITLE=false         # Remove chapter/volume from manga titles
```

### KCC (Kindle Comic Converter) Settings
```
KCC_PROCESS=false         # Enable KCC processing for manga
KCC_OPTIONS=              # KCC options (eg: -p KoC -m -u)
```

## Configuration Tips

- **For Books Only**: Set `BOOK_MONITORING=true` and `MANGA_MONITORING=false`
- **For Manga Only**: Set `MANGA_MONITORING=true` and `BOOK_MONITORING=false`
- **Metadata Updates**: Requires `HARDCOVER_API_KEY` and set `BOOK_UPDATE_METADATA=true`
- **KCC Processing**: Set `KCC_PROCESS=true` and configure `KCC_OPTIONS` for your device
- **Scan Frequency**: Use cron format (e.g., `*/5 * * * *` for every 5 minutes)

## Requirements

### File Structure
```
/ebooks/ebooks_in/
├── books/          # Place .epub books here
└── mangas/         # Place .cbz manga here
    ├── One Piece/  # Option 1: Series folder
    │   └── Chapter 1139.cbz
    └── Oda - One Piece - Chapter 1140.cbz  # Option 2: Direct file
```

### Supported Formats
- **Books**: `.epub`, `.kepub.epub` (Kobo)
- **Manga**: `.cbz` (can be converted to any format using KCC processing)

### Naming Conventions
- **Books**: `Author - Title.epub` (preferably)
- **Manga**: 
  - `Author - Series - Title.cbz` (Chapter/Vol. auto-parsed)
  - `Flame Scans_Vol. 3, Ch. 200_ Side Story 21.cbz` (with REMOVE_PREFIX=true)
  - `Volume 5.cbz` (Volume only, index = 5)
  - `Chapter 150.cbz` (Chapter only, index = 150)
  - `Vol. 2, Chapter 75.cbz` (Both, index = 75)
  - Supports various formats: Vol./Volume, Ch./Chapter

## Usage

The input folder will be monitored and for every new manga deposited, it will be processed by kcc and then moved to the output folder.
The /ebooks/books and /ebooks/mangas folders will be monitored and every .epub deposited will be processed and renamed/metadata updated.

## Troubleshooting

### Common Issues
- **No files processed**: Check if monitoring is enabled (`BOOK_MONITORING`/`MANGA_MONITORING`)
- **Metadata not updated**: Verify `HARDCOVER_API_KEY` is set and valid
- **KCC errors**: Check `KCC_OPTIONS` syntax and device compatibility

### Logs
Check container logs for detailed processing information:
```bash
docker logs ebookmanager
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/)
