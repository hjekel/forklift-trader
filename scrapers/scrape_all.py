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
    # Heftrucks — kern
    'toyota':       { 'slug_nl': 'toyota', 'slug_de': 'toyota', 'slug_uk': 'toyota', 'slug_fr': 'toyota', 'slug_be': 'toyota', 'slug_ts24': 'toyota' },
    'linde':        { 'slug_nl': 'linde', 'slug_de': 'linde', 'slug_uk': 'linde', 'slug_fr': 'linde', 'slug_be': 'linde', 'slug_ts24': 'linde' },
    'still':        { 'slug_nl': 'still', 'slug_de': 'still', 'slug_uk': 'still', 'slug_fr': 'still', 'slug_be': 'still', 'slug_ts24': 'still' },
    'jungheinrich': { 'slug_nl': 'jungheinrich', 'slug_de': 'jungheinrich', 'slug_uk': 'jungheinrich', 'slug_fr': 'jungheinrich', 'slug_be': 'jungheinrich', 'slug_ts24': 'jungheinrich' },
    'manitou':      { 'slug_nl': 'manitou', 'slug_de': 'manitou', 'slug_uk': 'manitou', 'slug_fr': 'manitou', 'slug_be': 'manitou', 'slug_ts24': 'manitou' },
    # Heftrucks — uitbreiding
    'hyster':       { 'slug_nl': 'hyster', 'slug_de': 'hyster', 'slug_uk': 'hyster', 'slug_fr': 'hyster', 'slug_be': 'hyster', 'slug_ts24': 'hyster' },
    'yale':         { 'slug_nl': 'yale', 'slug_de': 'yale', 'slug_uk': 'yale', 'slug_fr': 'yale', 'slug_be': 'yale', 'slug_ts24': 'yale' },
    'crown':        { 'slug_nl': 'crown', 'slug_de': 'crown', 'slug_uk': 'crown', 'slug_fr': 'crown', 'slug_be': 'crown', 'slug_ts24': 'crown' },
    'caterpillar':  { 'slug_nl': 'caterpillar--cat-', 'slug_de': 'caterpillar--cat-', 'slug_uk': 'caterpillar--cat-', 'slug_fr': 'caterpillar--cat-', 'slug_be': 'caterpillar--cat-', 'slug_ts24': 'caterpillar' },
    'komatsu':      { 'slug_nl': 'komatsu', 'slug_de': 'komatsu', 'slug_uk': 'komatsu', 'slug_fr': 'komatsu', 'slug_be': 'komatsu', 'slug_ts24': 'komatsu' },
    'nissan':       { 'slug_nl': 'nissan', 'slug_de': 'nissan', 'slug_uk': 'nissan', 'slug_fr': 'nissan', 'slug_be': 'nissan', 'slug_ts24': 'nissan' },
    'mitsubishi':   { 'slug_nl': 'mitsubishi', 'slug_de': 'mitsubishi', 'slug_uk': 'mitsubishi', 'slug_fr': 'mitsubishi', 'slug_be': 'mitsubishi', 'slug_ts24': 'mitsubishi' },
    # Hoogwerkers/verreikers
    'jlg':          { 'slug_nl': 'jlg', 'slug_de': 'jlg', 'slug_uk': 'jlg', 'slug_fr': 'jlg', 'slug_be': 'jlg', 'slug_ts24': 'jlg' },
    'genie':        { 'slug_nl': 'genie', 'slug_de': 'genie', 'slug_uk': 'genie', 'slug_fr': 'genie', 'slug_be': 'genie', 'slug_ts24': 'genie' },
    'haulotte':     { 'slug_nl': 'haulotte', 'slug_de': 'haulotte', 'slug_uk': 'haulotte', 'slug_fr': 'haulotte', 'slug_be': 'haulotte', 'slug_ts24': 'haulotte' },
    'jcb':          { 'slug_nl': 'jcb', 'slug_de': 'jcb', 'slug_uk': 'jcb', 'slug_fr': 'jcb', 'slug_be': 'jcb', 'slug_ts24': 'jcb' },
    'merlo':        { 'slug_nl': 'merlo', 'slug_de': 'merlo', 'slug_uk': 'merlo', 'slug_fr': 'merlo', 'slug_be': 'merlo', 'slug_ts24': 'merlo' },
    'bobcat':       { 'slug_nl': 'bobcat', 'slug_de': 'bobcat', 'slug_uk': 'bobcat', 'slug_fr': 'bobcat', 'slug_be': 'bobcat', 'slug_ts24': 'bobcat' },
}

SOURCES = {
    # Mascus — verified URLs via browser inspection 2026-03-31
    'mascus_nl': {
        'base': 'https://www.mascus.nl/laden-en-lossen/heftrucks/{brand}?page={page}',
        'region': 'NL',
        'source': 'mascus',
    },
    'mascus_de': {
        'base': 'https://www.mascus.de/flurforderzeuge/gabelstapler/{brand}?page={page}',
        'region': 'DE',
        'source': 'mascus',
    },
    'mascus_uk': {
        'base': 'https://www.mascus.co.uk/material-handling/forklift-trucks/{brand}?page={page}',
        'region': 'UK',
        'source': 'mascus',
    },
    'mascus_fr': {
        'base': 'https://www.mascus.fr/manutention/chariot-elevateur/{brand}?page={page}',
        'region': 'FR',
        'source': 'mascus',
    },
    'mascus_be': {
        'base': 'https://www.mascus.be/laden-en-lossen/heftrucks/{brand}?page={page}',
        'region': 'BE',
        'source': 'mascus',
    },
    # TruckScout24 — JS-rendered site, uses category-ids + fulltext search
    'truckscout24_de': {
        'base': 'https://www.truckscout24.de/main/search/index?category-ids=42&fulltext={brand}&page={page}',
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
                if result in ('EUR', 'GBP', 'NL', 'DE', 'UK', 'FR', 'BTW', 'INC', 'VAT', 'PDF', 'MWS', 'NET', 'VHB'):
                    continue
                return result
        return None

    def _extract_price(self, text):
        for pattern in [r'([\d.]+)\s*EUR', r'EUR\s*([\d.,]+)', r'([\d.,]+)\s*\xe2\x82\xac', r'\xe2\x82\xac\s*([\d.,]+)', r'([\d.,]+)\s*GBP', r'GBP\s*([\d.,]+)', r'\xc2\xa3\s*([\d.,]+)', r'([\d.,]+)\s*\xc2\xa3']:
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
        # First try specific patterns like "Bouwjaar: 2015" or "2015 •"
        for pattern in [r'(?:Bouwjaar|Baujahr|Year)[:\s]*(\d{4})', r'(\d{4})\s*[•·]']:
            match = re.search(pattern, text)
            if match:
                y = int(match.group(1))
                if 1990 <= y <= 2026:
                    return y
        # Fallback: any 4-digit year
        match = re.search(r'\b(20[0-2]\d|199\d)\b', text)
        if match:
            y = int(match.group(1))
            if 1990 <= y <= 2026:
                return y
        return 0

    def _extract_hours(self, text):
        # Specific patterns first
        for pattern in [
            r'(\d[\d.]*)\s*h\b',           # "690 h" or "690h"
            r'(\d[\d.]*)\s*uur',            # Dutch
            r'(\d[\d.]*)\s*Std',            # German
            r'(\d[\d.]*)\s*hours?',         # English
            r'(?:Betriebsstunden|uren|hours?)[:\s]*(\d[\d.]*)',  # Labeled
        ]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                h = int(match.group(1).replace('.', ''))
                if 0 <= h < 50000:
                    return h
        return 0

    def scrape_mascus(self, brand, source_key, max_pages=5):
        """Scrape Mascus (NL or DE) for a given brand."""
        src = SOURCES[source_key]
        # Pick correct slug for this source
        slug_key = 'slug_nl'
        if '_de' in source_key: slug_key = 'slug_de'
        elif '_uk' in source_key: slug_key = 'slug_uk'
        elif '_fr' in source_key: slug_key = 'slug_fr'
        elif '_be' in source_key: slug_key = 'slug_be'
        brand_slug = BRANDS[brand].get(slug_key, brand)
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
                    # Use full title as model, strip brand name
                    model_full = title.strip()
                    # Remove brand prefix if present (case-insensitive)
                    for b in [brand, brand.upper(), brand.capitalize()]:
                        if model_full.startswith(b + ' '):
                            model_full = model_full[len(b)+1:].strip()
                            break
                    # Also try regex extraction as fallback
                    model = model_full if len(model_full) >= 2 else self._extract_model(title)
                    if not model:
                        continue

                    price = self._extract_price(text)
                    if price == 0:
                        continue

                    # Extract image URL
                    img_el = item.find('img')
                    image_url = ''
                    if img_el:
                        image_url = img_el.get('src', '') or img_el.get('data-src', '') or ''
                        if image_url.startswith('//'):
                            image_url = 'https:' + image_url

                    # Make URL absolute
                    listing_url = href
                    if listing_url and listing_url.startswith('/'):
                        listing_url = src['base'].split('/')[0] + '//' + src['base'].split('/')[2] + listing_url

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
                        'url': listing_url,
                        'image_url': image_url,
                    }
                    self.all_listings.append(listing)
                    page_count += 1
                    log.info(f'  + [{brand}] {model} {listing["year"]} EUR{price:,}')
                except Exception:
                    continue

            log.info(f'[{prefix}] Page {page}: {page_count} listings')
            self._delay()

    def scrape_truckscout24(self, brand, source_key='truckscout24_de', max_pages=3):
        """Scrape TruckScout24 (DE or NL) for a given brand."""
        src = SOURCES[source_key]
        brand_slug = BRANDS[brand].get('slug_ts24', brand)
        region = src['region']
        prefix = f'{brand.upper()}-TS24-{region}'

        for page in range(1, max_pages + 1):
            url = src['base'].format(brand=brand_slug, page=page)
            log.info(f'[{prefix}] Page {page}: {url}')

            soup = self._fetch(url)
            if not soup:
                break

            # TruckScout24 uses section.grid-card with data-listing-id
            items = soup.find_all('section', attrs={'data-listing-id': True})
            if not items:
                # Fallback: try grid-card class
                items = soup.find_all('section', class_=lambda c: c and 'grid-card' in str(c))
            if not items:
                items = soup.find_all('div', class_=lambda c: c and ('ls-elem' in str(c) or 'listing' in str(c).lower()))
            if not items:
                log.info(f'[{prefix}] No items found on page {page} (site may be JS-rendered)')
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
                        'region': region,
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
        self.scrape_mascus(brand, 'mascus_uk', max_pages=pages_mascus)
        self.scrape_mascus(brand, 'mascus_fr', max_pages=pages_mascus)
        self.scrape_mascus(brand, 'mascus_be', max_pages=pages_mascus)
        self.scrape_truckscout24(brand, 'truckscout24_de', max_pages=pages_ts24)

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

        fieldnames = ['id', 'model', 'brand', 'year', 'hours', 'price', 'source', 'region', 'url', 'image_url']
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
