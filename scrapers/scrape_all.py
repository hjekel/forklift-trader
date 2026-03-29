#!/usr/bin/env python3
"""
ForkFlip Universal Scraper — All brands, all countries, one script.
Usage:
  python scrape_all.py                  # All brands, all sources
  python scrape_all.py --brand toyota   # Toyota only
  python scrape_all.py --quick          # 1 page per source (test)
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
log = logging.getLogger('forkflip')

# ══════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'nl-NL,nl;q=0.9,en;q=0.8,de;q=0.7',
}

MIN_PRICE = 2000
MAX_PRICE = 60000
MIN_DELAY = 2
MAX_DELAY = 5

BRANDS = {
    'toyota':       { 'slug_nl': 'toyota', 'slug_de': 'toyota', 'slug_ts24': 'toyota' },
    'linde':        { 'slug_nl': 'linde', 'slug_de': 'linde', 'slug_ts24': 'linde' },
    'still':        { 'slug_nl': 'still', 'slug_de': 'still', 'slug_ts24': 'still' },
    'jungheinrich': { 'slug_nl': 'jungheinrich', 'slug_de': 'jungheinrich', 'slug_ts24': 'jungheinrich' },
    'manitou':      { 'slug_nl': 'manitou', 'slug_de': 'manitou', 'slug_ts24': 'manitou' },
}

SOURCES = {
    'mascus_nl': {
        'base': 'https://www.mascus.nl/laden-en-lossen/heftrucks/{brand}?page={page}',
        'region': 'NL',
        'source': 'mascus',
    },
    'mascus_de': {
        'base': 'https://www.mascus.de/laden-und-lossen/gabelstapler/{brand}?page={page}',
        'region': 'DE',
        'source': 'mascus',
    },
    'truckscout24': {
        'base': 'https://www.truckscout24.de/gebraucht/gabelstapler/{brand}?currentpage={page}',
        'region': 'DE',
        'source': 'truckscout24',
    },
}

# Model extraction patterns — works for all brands
MODEL_PATTERNS = [
    # Toyota
    r'\b(8F[A-Z]{1,4}\d{2,3}[A-Z]?)\b',
    r'\b(52-?8\s*F[A-Z]{2,4}\s*\d{2,3})\b',
    r'\b(FB[A-Z]{1,3}\d{2,3})\b',
    r'\b(FD\d{2,3}[A-Z]?)\b',
    r'\b(FG\d{2,3}[A-Z]?)\b',
    r'\b(RRE\d{2,3})\b',
    r'\b(BT[A-Z]{1,4}\d{2,3})\b',
    # Linde
    r'\b(H\d{2,3}[A-Z]?(?:-\d{2})?)\b',
    r'\b(E\d{2,3}[A-Z]?(?:-\d{2})?)\b',
    r'\b(R\d{2,3}[A-Z]?(?:-\d{2})?)\b',
    r'\b(L\d{2,3}[A-Z]?)\b',
    r'\b(T\d{2,3}[A-Z]?)\b',
    # Still
    r'\b(RX\s?\d{2}(?:-\d{2})?)\b',
    r'\b(FM-?X\s?\d{2,3})\b',
    r'\b(EXU\s?\d{2})\b',
    r'\b(ECU\s?\d{2})\b',
    # Jungheinrich
    r'\b(EFG\s?\d{3}[a-z]?)\b',
    r'\b(ERE\s?\d{3})\b',
    r'\b(ETV\s?\d{3})\b',
    r'\b(EJE\s?\d{3})\b',
    r'\b(DFG\s?\d{3}[a-z]?)\b',
    r'\b(TFG\s?\d{3}[a-z]?)\b',
    # Manitou
    r'\b(M[SIECTX]\d{2,4}[A-Z]*)\b',
    r'\b(MC\s?\d{2,3})\b',
    r'\b(ME\s?\d{3})\b',
    r'\b(MT\s?\d{3,4})\b',
    # Generic fallback — any alphanumeric model-like string
    r'\b([A-Z]{1,4}\d{2,4}[A-Z]{0,3})\b',
]

# ══════════════════════════════════════
# SCRAPER
# ══════════════════════════════════════

class ForkFlipScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.all_listings = []
        self.known_urls = set()
        self.counter = 0

    def _delay(self):
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    def _fetch(self, url):
        for attempt in range(3):
            try:
                r = self.session.get(url, timeout=30)
                if r.status_code == 200:
                    return BeautifulSoup(r.text, 'html.parser')
                elif r.status_code == 429:
                    log.warning(f'Rate limited on {url}, waiting 60s...')
                    time.sleep(60)
                elif r.status_code == 403:
                    log.warning(f'Blocked (403) on {url}')
                    return None
                else:
                    log.debug(f'HTTP {r.status_code}: {url}')
            except Exception as e:
                log.debug(f'Fetch error: {e}')
                time.sleep(5 * (attempt + 1))
        return None

    def _extract_model(self, text):
        text_upper = text.upper()
        for pattern in MODEL_PATTERNS:
            match = re.search(pattern, text_upper)
            if match:
                result = match.group(1).replace(' ', '')
                # Filter out garbage (too short, just numbers, common words)
                if len(result) < 3 or result.isdigit():
                    continue
                if result in ('EUR', 'NL', 'DE', 'BTW', 'INC', 'VAT', 'PDF'):
                    continue
                return result
        return None

    def _extract_price(self, text):
        for pattern in [r'([\d.]+)\s*EUR', r'EUR\s*([\d.,]+)', r'([\d.,]+)\s*\xe2\x82\xac', r'\xe2\x82\xac\s*([\d.,]+)']:
            match = re.search(pattern, text)
            if match:
                price_str = match.group(1).replace('.', '').replace(',', '')
                try:
                    price = int(price_str)
                    if MIN_PRICE < price < MAX_PRICE:
                        return price
                except ValueError:
                    continue
        return 0

    def _extract_year(self, text):
        match = re.search(r'\b(20[0-2]\d|199\d)\b', text)
        return int(match.group(1)) if match else 0

    def _extract_hours(self, text):
        for pattern in [r'(\d[\d.]*)\s*[hu](?:our|uur|r)?s?', r'(\d[\d.]*)\s*Std']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                h = int(match.group(1).replace('.', ''))
                if 0 <= h < 50000:
                    return h
        return 0

    def scrape_mascus(self, brand, source_key, max_pages=5):
        """Scrape Mascus (NL or DE) for a given brand."""
        src = SOURCES[source_key]
        brand_slug = BRANDS[brand].get('slug_nl' if 'nl' in source_key else 'slug_de', brand)
        region = src['region']
        prefix = f'{brand.upper()}-{region}'

        for page in range(1, max_pages + 1):
            url = src['base'].format(brand=brand_slug, page=page)
            log.info(f'[{prefix}] Page {page}: {url}')

            soup = self._fetch(url)
            if not soup:
                break

            items = soup.find_all('div', class_=lambda c: c and 'searchResultItemWrapper' in c)
            if not items:
                log.info(f'[{prefix}] No more items on page {page}')
                break

            page_count = 0
            for item in items:
                try:
                    title_el = item.find('h2') or item.find('h3')
                    if not title_el:
                        continue
                    title = title_el.get_text().strip()

                    link_el = item.find('a', href=True)
                    href = link_el['href'] if link_el else ''
                    if href in self.known_urls:
                        continue
                    self.known_urls.add(href)

                    text = item.get_text()
                    model = self._extract_model(title)
                    if not model:
                        continue

                    price = self._extract_price(text)
                    if price == 0:
                        continue

                    self.counter += 1
                    listing = {
                        'id': f'{prefix}-{self.counter}',
                        'model': model,
                        'brand': brand,
                        'year': self._extract_year(text),
                        'hours': self._extract_hours(text),
                        'price': price,
                        'source': src['source'],
                        'region': region,
                    }
                    self.all_listings.append(listing)
                    page_count += 1
                    log.info(f'  + [{brand}] {model} {listing["year"]} EUR{price:,}')
                except Exception:
                    continue

            log.info(f'[{prefix}] Page {page}: {page_count} listings')
            self._delay()

    def scrape_truckscout24(self, brand, max_pages=3):
        """Scrape TruckScout24 for a given brand."""
        brand_slug = BRANDS[brand].get('slug_ts24', brand)
        prefix = f'{brand.upper()}-TS24'

        for page in range(1, max_pages + 1):
            url = SOURCES['truckscout24']['base'].format(brand=brand_slug, page=page)
            log.info(f'[{prefix}] Page {page}: {url}')

            soup = self._fetch(url)
            if not soup:
                break

            # TruckScout24 uses different HTML structure
            items = soup.find_all('div', class_=lambda c: c and ('ls-elem' in str(c) or 'data-item' in str(c)))
            if not items:
                # Try alternative selectors
                items = soup.find_all('a', class_=lambda c: c and 'ls-elem' in str(c))
            if not items:
                items = soup.find_all('div', class_=lambda c: c and 'listing' in str(c).lower())
            if not items:
                log.info(f'[{prefix}] No items found on page {page}')
                break

            page_count = 0
            for item in items:
                try:
                    text = item.get_text()
                    model = self._extract_model(text)
                    if not model:
                        continue

                    price = self._extract_price(text)
                    if price == 0:
                        continue

                    href = ''
                    link = item.find('a', href=True) if item.name != 'a' else item
                    if link and link.get('href'):
                        href = link['href']
                    if href in self.known_urls:
                        continue
                    self.known_urls.add(href or f'ts24-{self.counter}')

                    self.counter += 1
                    listing = {
                        'id': f'{prefix}-{self.counter}',
                        'model': model,
                        'brand': brand,
                        'year': self._extract_year(text),
                        'hours': self._extract_hours(text),
                        'price': price,
                        'source': 'truckscout24',
                        'region': 'DE',
                    }
                    self.all_listings.append(listing)
                    page_count += 1
                    log.info(f'  + [{brand}] {model} {listing["year"]} EUR{price:,}')
                except Exception:
                    continue

            log.info(f'[{prefix}] Page {page}: {page_count} listings')
            self._delay()

    def scrape_brand(self, brand, pages_mascus=5, pages_ts24=3):
        """Scrape all sources for a single brand."""
        log.info(f'\n{"="*50}')
        log.info(f'SCRAPING: {brand.upper()}')
        log.info(f'{"="*50}')

        self.scrape_mascus(brand, 'mascus_nl', max_pages=pages_mascus)
        self.scrape_mascus(brand, 'mascus_de', max_pages=pages_mascus)
        self.scrape_truckscout24(brand, max_pages=pages_ts24)

    def scrape_all(self, brands=None, pages_mascus=5, pages_ts24=3):
        """Scrape all brands across all sources."""
        brands = brands or list(BRANDS.keys())
        for brand in brands:
            if brand in BRANDS:
                self.scrape_brand(brand, pages_mascus, pages_ts24)
            else:
                log.warning(f'Unknown brand: {brand}')
        return self.all_listings

    def save_csv(self, filename='all_listings.csv'):
        output_dir = Path(__file__).parent.parent / 'output'
        output_dir.mkdir(exist_ok=True)
        filepath = output_dir / filename

        if not self.all_listings:
            log.warning('No listings to save')
            return None

        fieldnames = ['id', 'model', 'brand', 'year', 'hours', 'price', 'source', 'region']
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.all_listings)

        log.info(f'Saved {len(self.all_listings)} listings to {filepath}')
        return str(filepath)

    def summary(self):
        """Print summary of results."""
        brands = {}
        sources = {}
        for l in self.all_listings:
            brands[l['brand']] = brands.get(l['brand'], 0) + 1
            key = f"{l['source']} ({l['region']})"
            sources[key] = sources.get(key, 0) + 1

        print(f'\n{"="*50}')
        print(f'FORKFLIP SCRAPE SUMMARY')
        print(f'{"="*50}')
        print(f'Total listings: {len(self.all_listings)}')
        print(f'\nBy brand:')
        for b, c in sorted(brands.items(), key=lambda x: -x[1]):
            print(f'  {b:20s} {c:4d}')
        print(f'\nBy source:')
        for s, c in sorted(sources.items(), key=lambda x: -x[1]):
            print(f'  {s:25s} {c:4d}')
        print()


def main():
    parser = argparse.ArgumentParser(description='ForkFlip Universal Scraper')
    parser.add_argument('--brand', '-b', type=str, help='Single brand (toyota/linde/still/jungheinrich/manitou)')
    parser.add_argument('--pages', '-p', type=int, default=5, help='Max pages per source')
    parser.add_argument('--quick', '-q', action='store_true', help='Quick mode (1 page)')
    args = parser.parse_args()

    pages = 1 if args.quick else args.pages

    scraper = ForkFlipScraper()

    if args.brand:
        scraper.scrape_all(brands=[args.brand], pages_mascus=pages, pages_ts24=max(1, pages//2))
    else:
        scraper.scrape_all(pages_mascus=pages, pages_ts24=max(1, pages//2))

    scraper.save_csv()
    scraper.summary()


if __name__ == '__main__':
    main()
