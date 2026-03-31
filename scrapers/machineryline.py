#!/usr/bin/env python3
"""
Machineryline.nl scraper — Searches any equipment type, brand, model.
Covers: aerial lifts, telehandlers, forklifts, scissor lifts, cherry pickers, etc.

Usage:
  python machineryline.py --query "JLG Toucan 8E"
  python machineryline.py --query "Genie S-65"
  python machineryline.py --category hoogwerkers --brand JLG
"""
import requests
from bs4 import BeautifulSoup
import csv
import time
import random
import re
import logging
import argparse
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('machineryline')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'nl-NL,nl;q=0.9,en;q=0.8',
}

# Equipment category mappings for Machineryline URL structure
CATEGORIES = {
    'hoogwerkers': 'hoogwerkers',        # Aerial work platforms
    'schaarhoogwerkers': 'schaarhoogwerkers',  # Scissor lifts
    'heftrucks': 'heftrucks',            # Forklifts
    'telehandlers': 'verreikers',        # Telehandlers
    'kranen': 'kranen',                  # Cranes
    'bouwmachines': 'bouwmachines',      # Construction machines
}


class MachinerylineScraper:
    BASE_URL = 'https://machineryline.nl'
    SEARCH_URL = 'https://machineryline.nl/zoeken'

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.listings = []
        self.known_urls = set()

    def _delay(self):
        time.sleep(random.uniform(2, 4))

    def _fetch(self, url):
        for attempt in range(3):
            try:
                r = self.session.get(url, timeout=30)
                if r.status_code == 200:
                    return BeautifulSoup(r.text, 'html.parser')
                elif r.status_code == 429:
                    log.warning('Rate limited, waiting 60s...')
                    time.sleep(60)
                elif r.status_code == 403:
                    log.warning(f'Blocked (403): {url}')
                    return None
                else:
                    log.debug(f'HTTP {r.status_code}: {url}')
            except Exception as e:
                log.debug(f'Error: {e}')
                time.sleep(5 * (attempt + 1))
        return None

    def _extract_price(self, text):
        """Extract price from text, handles EUR and various formats."""
        patterns = [
            r'(\d[\d\s.]*)\s*EUR',
            r'EUR\s*(\d[\d\s.]*)',
            r'(\d[\d\s.]*)\s*\u20ac',
            r'\u20ac\s*(\d[\d\s.]*)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                price_str = match.group(1).replace('.', '').replace(' ', '').replace(',', '')
                try:
                    price = int(price_str)
                    if 500 < price < 200000:
                        return price
                except ValueError:
                    continue
        return 0

    def _extract_year(self, text):
        match = re.search(r'\b(20[0-2]\d|199\d)\b', text)
        return int(match.group(1)) if match else 0

    def _extract_hours(self, text):
        patterns = [r'(\d[\d.]*)\s*m/u', r'(\d[\d.]*)\s*[hu](?:our|ur)?s?', r'(\d[\d.]*)\s*Std']
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                h = int(match.group(1).replace('.', ''))
                if 0 <= h < 100000:
                    return h
        return 0

    def search(self, query, max_pages=3):
        """Search Machineryline with free-text query."""
        log.info(f'Searching Machineryline for: "{query}"')

        for page in range(1, max_pages + 1):
            url = f'{self.SEARCH_URL}?search={query.replace(" ", "+")}&page={page}'
            log.info(f'  Page {page}: {url}')

            soup = self._fetch(url)
            if not soup:
                break

            # Try multiple selectors for listings
            items = soup.find_all('div', class_=lambda c: c and 'listing' in str(c).lower())
            if not items:
                items = soup.find_all('a', class_=lambda c: c and 'listing' in str(c).lower())
            if not items:
                items = soup.find_all('div', class_=lambda c: c and 'offer' in str(c).lower())
            if not items:
                # Try the generic card structure
                items = soup.find_all('div', class_=lambda c: c and ('card' in str(c).lower() or 'item' in str(c).lower()))

            if not items:
                log.info(f'  No items found on page {page}')
                break

            page_count = 0
            for item in items:
                try:
                    text = item.get_text()
                    if len(text) < 20:
                        continue

                    # Extract link
                    link = item.find('a', href=True)
                    if not link:
                        if item.name == 'a':
                            link = item
                        else:
                            continue

                    href = link.get('href', '')
                    if href.startswith('/'):
                        href = self.BASE_URL + href
                    if href in self.known_urls or not href:
                        continue
                    self.known_urls.add(href)

                    # Extract title
                    title_el = item.find('h2') or item.find('h3') or item.find('strong')
                    title = title_el.get_text().strip() if title_el else text[:60].strip()

                    price = self._extract_price(text)
                    year = self._extract_year(text)
                    hours = self._extract_hours(text)

                    # Extract location
                    location = ''
                    loc_match = re.search(r'(Nederland|Germany|Belgium|France|UK|Deutschland|Belgien|Frankreich)[\s,]*([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)?', text)
                    if loc_match:
                        location = loc_match.group(0).strip()

                    # Extract image
                    img = item.find('img')
                    image = img.get('src', '') if img else ''
                    if image.startswith('//'):
                        image = 'https:' + image

                    # Extract seller
                    seller = ''
                    seller_el = item.find('span', class_=lambda c: c and 'seller' in str(c).lower())
                    if seller_el:
                        seller = seller_el.get_text().strip()

                    listing = {
                        'id': f'ML-{len(self.listings)+1}',
                        'title': title,
                        'brand': query.split()[0] if query else 'unknown',
                        'model': title,
                        'year': year,
                        'hours': hours,
                        'price': price,
                        'source': 'machineryline',
                        'region': 'NL',
                        'location': location,
                        'seller': seller,
                        'url': href,
                        'image': image,
                    }
                    self.listings.append(listing)
                    page_count += 1
                    log.info(f'  + {title[:40]} - EUR{price:,}' if price else f'  + {title[:40]}')

                except Exception as e:
                    log.debug(f'Parse error: {e}')
                    continue

            log.info(f'  Page {page}: {page_count} listings')
            if page_count == 0:
                break
            self._delay()

        return self.listings

    def search_category(self, category, brand, model='', max_pages=3):
        """Search by specific category and brand."""
        cat = CATEGORIES.get(category, category)
        url_path = f'/-/{cat}/{brand}'
        if model:
            url_path += f'/{model}'

        log.info(f'Searching category: {url_path}')

        for page in range(1, max_pages + 1):
            url = f'{self.BASE_URL}{url_path}?page={page}'
            log.info(f'  Page {page}: {url}')

            soup = self._fetch(url)
            if not soup:
                break

            items = soup.find_all('div', class_=lambda c: c and ('listing' in str(c).lower() or 'offer' in str(c).lower() or 'card' in str(c).lower()))
            if not items:
                log.info(f'  No items found on page {page}')
                break

            # Same extraction logic as search()
            page_count = 0
            for item in items:
                try:
                    text = item.get_text()
                    if len(text) < 20:
                        continue
                    link = item.find('a', href=True)
                    if not link and item.name == 'a':
                        link = item
                    if not link:
                        continue
                    href = link.get('href', '')
                    if href.startswith('/'):
                        href = self.BASE_URL + href
                    if href in self.known_urls or not href:
                        continue
                    self.known_urls.add(href)
                    title_el = item.find('h2') or item.find('h3') or item.find('strong')
                    title = title_el.get_text().strip() if title_el else text[:60].strip()
                    listing = {
                        'id': f'ML-{len(self.listings)+1}',
                        'title': title,
                        'brand': brand,
                        'model': title,
                        'year': self._extract_year(text),
                        'hours': self._extract_hours(text),
                        'price': self._extract_price(text),
                        'source': 'machineryline',
                        'region': 'NL',
                        'url': href,
                        'image': '',
                    }
                    self.listings.append(listing)
                    page_count += 1
                except Exception:
                    continue

            if page_count == 0:
                break
            self._delay()

        return self.listings

    def save_csv(self, filename='machineryline_listings.csv'):
        output_dir = Path(__file__).parent.parent / 'output'
        output_dir.mkdir(exist_ok=True)
        filepath = output_dir / filename
        if not self.listings:
            log.warning('No listings to save')
            return None
        fieldnames = ['id', 'title', 'brand', 'model', 'year', 'hours', 'price', 'source', 'region', 'location', 'seller', 'url', 'image']
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(self.listings)
        log.info(f'Saved {len(self.listings)} listings to {filepath}')
        return str(filepath)


def main():
    parser = argparse.ArgumentParser(description='Machineryline Universal Scraper')
    parser.add_argument('--query', '-q', type=str, help='Free-text search (e.g. "JLG Toucan 8E")')
    parser.add_argument('--category', '-c', type=str, help='Category (hoogwerkers, heftrucks, etc.)')
    parser.add_argument('--brand', '-b', type=str, help='Brand (JLG, Genie, Toyota, etc.)')
    parser.add_argument('--model', '-m', type=str, default='', help='Model (Toucan, S-65, etc.)')
    parser.add_argument('--pages', '-p', type=int, default=3, help='Max pages to scrape')
    args = parser.parse_args()

    scraper = MachinerylineScraper()

    if args.query:
        scraper.search(args.query, max_pages=args.pages)
    elif args.category and args.brand:
        scraper.search_category(args.category, args.brand, args.model, max_pages=args.pages)
    else:
        print('Usage: --query "JLG Toucan 8E" or --category hoogwerkers --brand JLG')
        return

    scraper.save_csv()
    print(f'\nFound {len(scraper.listings)} listings')


if __name__ == '__main__':
    main()
