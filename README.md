# Movie Scraper (ssr1.scrape.center)

A compact Python scraper that collects movie information from ssr1.scrape.center (pages 1–10) and exports the results to `movie.csv`.

This project is intended for educational and small-scale data-collection tasks. It demonstrates a simple, polite approach to web scraping using standard libraries.

---

## Features

- Scrapes movie entries from page 1–10 of <https://ssr1.scrape.center/>
- Extracts: title, poster image URL, rating, genre(s), and detail page URL
- Saves results as a UTF-8 encoded CSV (`movie.csv`) for easy downstream use

---

## Requirements

- Python 3.8+ (3.11 recommended)
- Dependencies listed in `requirements.txt`:
  - requests
  - beautifulsoup4
  - lxml

---

## Quickstart

1. Create a virtual environment (recommended) and install dependencies:

    ```bash
    python -m venv .venv
    # Activate the virtual environment:
    # Linux / macOS: source .venv/bin/activate
    # Windows (Git Bash): source .venv/Scripts/activate
    pip install -r requirements.txt
    ```

2. Run the scraper:

    ```bash
    python scrape_movies.py
    ```

3. The script will produce `movie.csv` in the current working directory.

If anything fails, see the Troubleshooting section below.

---

## CSV Output Schema

The output CSV has the following columns (UTF-8 encoded):

- `name` — movie title (string)
- `image_url` — poster/cover image URL (string)
- `rating` — numeric score (string) when found (e.g. `9.5`) — empty if not available
- `genre` — one or more genres or categories; when multiple, they are comma-separated (e.g. `剧情, 爱情`)
- `detail_url` — link to the movie details page on the site

Example CSV header line:

```
name,image_url,rating,genre,detail_url
```

---

## Implementation Notes

- The scraper collects detail page URLs from each list page (pages `/page/1` to `/page/10`) and then parses each detail page to extract the required fields.
- For `genre` extraction, the script attempts the following, in order:
  1. Find elements on the detail page whose CSS class names indicate categories/genres (e.g., `categories`, `category`, `genre`, `genres`, `tags`, `types`) and collects text from `<a>` / `<span>` children.
  2. If the detail page contains no explicit category elements, the script falls back to parsing the page text near constructs like `分钟` / `上映` or the list page card text, extracts the left-hand portion before slash or metadata, and uses that as a genre placeholder.
  3. If both detail and list pages do not contain genres, the `genre` field is left empty.

Other useful behaviors:

- The script uses a polite `User-Agent`, retries for common server errors, and applies a brief sleep between requests to reduce load on the target server.

---

## Troubleshooting & Tips

- If you see many empty `genre` fields, re-run the script with network connectivity and check a few `detail_url` entries manually to see how the site renders genres (they may be rendered dynamically via JavaScript and not visible to a simple request — in that case, a headless browser is required).
- If you see HTTP errors, verify your network settings or try again later. The script includes automatic retries for 5xx responses.
- To debug a specific detail page, add logging or a short snippet to dump page contents:

```python
import requests
from bs4 import BeautifulSoup
r = requests.get('https://ssr1.scrape.center/detail/1')
print(BeautifulSoup(r.text, 'lxml').prettify()[:1000])
```
