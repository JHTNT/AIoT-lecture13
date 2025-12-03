#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scrape movies from https://ssr1.scrape.center/ page 1-10 and save to movie.csv

Fields: name, image_url, rating, genre

Usage:
    python scrape_movies.py

Dependencies: requests, beautifulsoup4
"""

import csv
import logging
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

BASE_URL = "https://ssr1.scrape.center"


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def create_session():
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        }
    )
    # retry strategy
    retries = Retry(total=5, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    session.mount("http://", HTTPAdapter(max_retries=retries))
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session


def find_detail_links(soup):
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.match(r"^/detail/\d+$", href):
            # extract nearby genre info from list page (if present)
            genre_from_list = ""
            parent = a.parent
            try:
                full_text = parent.get_text(" ", strip=True)
                anchor_text = a.get_text(strip=True)
                rest = full_text.replace(anchor_text, "").strip()
                if rest:
                    parts = re.split(r"/|分钟|上映", rest)
                    if parts:
                        left = parts[0].strip()
                        if left:
                            genre_from_list = left.split()[0]
            except Exception:
                genre_from_list = ""
            links.append((urljoin(BASE_URL, href), a, genre_from_list))
    # deduplicate by url while maintaining order
    seen = set()
    unique = []
    for url, a, _ in links:
        if url in seen:
            continue
        seen.add(url)
        unique.append((url, a))
    return unique


def get_img_from_anchor(a_tag):
    # try to find image in the same card
    # check parent chain up to 3 levels
    tag = a_tag
    for _ in range(4):
        imgs = tag.find_all("img") if tag else []
        if imgs:
            # pick the first image with src
            for img in imgs:
                src = img.get("src") or img.get("data-src")
                if src:
                    return urljoin(BASE_URL, src)
        tag = tag.parent
    return None


def parse_detail_page(session, url):
    logging.debug("Fetching detail: %s" % url)
    resp = session.get(url, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    # NAME: find <h2> or <h1> with title text
    name = None
    for tagname in ("h2", "h1", "h3"):
        tag = soup.find(tagname)
        if tag and tag.get_text(strip=True):
            name = tag.get_text(strip=True)
            break

    if not name:
        # fallback to title from meta
        title_tag = soup.find("title")
        name = title_tag.get_text(strip=True) if title_tag else ""

    # RATING: find numeric score between 0 and 10, prefer elements with class 'score' or 'rating'
    rating = ""
    score_tags = soup.find_all(class_=re.compile(r"(score|rating)", re.I))
    if score_tags:
        # take first numeric text
        for t in score_tags:
            text = t.get_text(strip=True)
            m = re.search(r"\d+(?:\.\d+)?", text)
            if m:
                rating = m.group(0)
                break

    if not rating:
        # search for first occurrence of a number like 9.5 near the top of the page
        # search the soup's text and pick first 0-10 float after the name
        page_text = soup.get_text(separator=" ", strip=True)
        if name and name in page_text:
            idx = page_text.find(name)
            after = page_text[idx : idx + 300]
            m = re.search(r"\b(10(?:\.0+)?|[0-9](?:\.\d+)?)\b", after)
            if m:
                rating = m.group(0)
        if not rating:
            # fallback: first match in whole page
            m = re.search(r"\b(10(?:\.0+)?|[0-9](?:\.\d+)?)\b", page_text)
            if m:
                rating = m.group(0)

    # GENRE: try to locate categories element(s) - prefer explicit 'category'/'categories' class
    genre = ''
    cats = []
    # search for elements whose class contains category/categories/genres/tags
    candidates = soup.find_all(class_=re.compile(r'\b(category|categories|genre|genres|tags|types)\b', re.I))
    if candidates:
        for el in candidates:
            # collect any <a> or <span> or direct text entries inside
            items = []
            for a in el.find_all(['a', 'span']):
                txt = a.get_text(strip=True)
                if txt:
                    items.append(txt)
            # if no <a>/<span>, use element text and split by common separators
            if not items:
                raw = el.get_text(' ', strip=True)
                # split by comma、space、/、·
                for token in re.split(r'[、,/·|]+|\s{2,}', raw):
                    t = token.strip()
                    if t:
                        items.append(t)
            for it in items:
                if it and it not in cats:
                    cats.append(it)
        genre = ', '.join(cats)
    else:
        # fallback: try to locate the block containing minutes or "上映" and extract genre
        # this handles cases where the site renders the info as plain text like "剧情爱情 中国内地 ... / 171 分钟"
        for tag in soup.find_all(text=re.compile(r'分钟|上映|/')):
            text = tag.strip()
            if not text:
                continue
            # we expect a format like "剧情爱情 中国内地 / 171 分钟" => take left of / and split by spaces
            parts = text.split('/')
            if parts:
                # pick left-most part and remove country/region
                left = parts[0].strip()
                # remove date/time tokens if any
                left_clean = re.sub(r'\d{4}[-年]\d{1,2}[-月]\d{1,2}', '', left).strip()
                # split by whitespace to isolate genre tokens
                tokens = [t for t in left_clean.split() if t]
                if tokens:
                    # the genre is likely at the beginning (e.g., 剧情爱情)
                    # if the first token contains both genres in one word (no spaces), keep it
                    genre = tokens[0]
                    break

    # poster: choose first >img with 'movie' in src or the largest
    poster = ""
    imgs = soup.find_all("img")
    best = None
    for img in imgs:
        src = img.get("src") or img.get("data-src")
        if not src:
            continue
        if "movie" in src or "meituan" in src:
            poster = urljoin(BASE_URL, src)
            best = poster
            break
    if not poster and imgs:
        poster = urljoin(BASE_URL, imgs[0].get("src") or imgs[0].get("data-src") or "")

    return {
        "name": name.strip() if name else "",
        "rating": rating,
        "genre": genre.strip() if genre else "",
        "poster": poster,
    }


def main():
    session = create_session()

    detail_urls = []  # list of (detail_url, poster_from_list)
    for page in range(1, 11):
        page_url = f"{BASE_URL}/page/{page}"
        logging.info(f"Fetching page {page_url}")
        resp = session.get(page_url, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        pairs = find_detail_links(soup)
        logging.info(f"Found {len(pairs)} links on page {page}")
        for url, a, genre_from_list in pairs:
            poster = get_img_from_anchor(a)
            detail_urls.append((url, poster, genre_from_list))

        # be nice
        time.sleep(0.5)

    # deduplicate detail urls
    seen = set()
    unique = []
    for url, poster, genre_from_list in detail_urls:
        if url in seen:
            continue
        seen.add(url)
        unique.append((url, poster, genre_from_list))

    logging.info(f"Total unique detail pages: {len(unique)}")

    results = []
    for i, (url, poster_from_list, genre_from_list) in enumerate(unique, start=1):
        logging.info(f"Parsing detail {i}/{len(unique)}: {url}")
        try:
            details = parse_detail_page(session, url)
        except Exception as exc:
            logging.warning(f"Failed to parse {url}: {exc}")
            continue

        # prefer poster from list if available
        if poster_from_list:
            img_url = poster_from_list
        elif details.get("poster"):
            img_url = details.get("poster")
        else:
            img_url = ""
        # prefer genre from detail page, then list page
        gen = details.get("genre", "") or (genre_from_list or "")

        results.append(
            {
                "name": details.get("name", ""),
                "image_url": img_url,
                "rating": details.get("rating", ""),
                "genre": gen,
                "detail_url": url,
            }
        )

        # small sleep to be polite
        time.sleep(0.7)

    # write CSV
    csv_path = "movie.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["name", "image_url", "rating", "genre", "detail_url"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(r)

    logging.info(f"Wrote {len(results)} records to {csv_path}")


if __name__ == "__main__":
    main()
