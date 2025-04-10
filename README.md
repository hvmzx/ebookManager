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
  -e SCAN_INTERVAL='60' \
  -e KCC_OPTIONS= \
  ghcr.io/hvmzx/ebookmanager:latest
```

For docker-compose :

```bash
version: '3.8'

services:
  ebookmanager:
    container_name: ebookmanager
    image: ghcr.io/hvmzx/ebookmanager:dev
    environment:
      - MANGA_MONITORING=false #Set to false by default
      - BOOK_MONITORING=false #Set to false by default
      - SCAN_INTERVAL=60 #Set to 60s by default
      - KCC_OPTIONS= #KCC options as per https://github.com/ciromattia/kcc#standalone-kcc-c2epy-usage
    volumes:
      - /input/ebooks:/app/ebooks/ebooks_in
      - /output/ebooks:/app/ebooks/ebooks_out
```

## Requirements :

- ebooks need to be of the .epub format (.kepub.epub is also supported for Kobo's)
- /ebooks folder requires the presence of the mangas folder and/or the books folder
- Mangas need to be deposited in the /ebooks/mangas folder and of the format AUTHOR - SERIES - TITLE.epub (Chapter and Vol. are supported as well and automatically parsed)
- Books need to be deposited in the /ebooks/books folder and of the format AUTHOR - TITLE.epub

## Usage

The input folder will be monitored and for every new manga deposited, it will be processed by kcc and then moved to the output folder.
The /ebooks/books and /ebooks/mangas folders will be monitored and every .epub deposited will be processed and renamed/metadata updated.

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/)
