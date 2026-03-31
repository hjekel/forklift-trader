#!/usr/bin/env python3
"""
Machineseeker.nl scraper — Pre-scrapes specialist equipment categories.
Same architecture as Mascus scraper: GitHub Actions → CSV → embed in HTML.

Usage:
  python machineseeker.py                    # All configured categories
  python machineseeker.py --query "JLG Toucan 8E"  # Custom search
  python machineseeker.py --quick            # 1 page per category (test)
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
log = logging.getLogger('machineseeker')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'nl-NL,nl;q=0.9,en;q=0.8',
}

# Pre-configured searches to run daily
DAILY_SEARCHES = [
    # Aerial lifts / Hoogwerkers
    {'name': 'JLG Toucan', 'query': 'JLG Toucan', 'category': 133, 'brand': 'JLG', 'equipment': 'aerial_lift'},
    {'name': 'JLG Boom', 'query': 'JLG boom lift', 'category': 133, 'brand': 'JLG', 'equipment': 'aerial_lift'},
    {'name': 'Genie Hoogwerker', 'query': 'Genie hoogwerker', 'category': 133, 'brand': 'Genie', 'equipment': 'aerial_lift'},
    {'name': 'Haulotte Hoogwerker', 'query': 'Haulotte hoogwerker', 'category': 133, 'brand': 'Haulotte', 'equipment': 'aerial_lift'},
    {'name': 'Niftylift', 'query': 'Niftylift', 'category': 133, 'brand': 'Niftylift', 'equipment': 'aerial_lift'},
    # Scissor lifts
    {'name': 'JLG Schaarlift', 'query': 'JLG schaarhoogwerker', 'category': 133, 'brand': 'JLG', 'equipment': 'scissor_lift'},
    {'name': 'Genie Schaarlift', 'query': 'Genie schaarhoogwerker', 'category': 133, 'brand': 'Genie', 'equipment': 'scissor_lift'},
    # Telehandlers
    {'name': 'Manitou Telehandler', 'query': 'Manitou verreiker', 'category': 133, 'brand': 'Manitou', 'equipment': 'telehandler'},
    {'name': 'JCB Telehandler', 'query': 'JCB telehandler', 'category': 133, 'brand': 'JCB', 'equipment': 'telehandler'},
    {'name': 'Merlo Telehandler', 'query': 'Merlo verreiker', 'category': 133, 'brand': 'Merlo', 'equipment': 'telehandler'},
    # Extra forklifts
    {'name': 'Toyota Forklift', 'query': 'Toyota forklift', 'category': 133, 'brand': 'Toyota', 'equipment': 'forklift'},
    {'name': 'Linde Forklift', 'query': 'Linde forklift', 'category': 133, 'brand': 'Linde', 'equipment': 'forklift'},
    {'name': 'Still Forklift', 'query': 'Still forklift', 'category': 133, 'brand': 'Still', 'equipment': 'forklift'},
    {'name': 'Hyster Forklift', 'query': 'Hyster forklift', 'category': 133, 'brand': 'Hyster', 'equipment': 'forklift'},
    {'name': 'Yale Forklift', 'query': 'Yale forklift', 'category': 133, 'brand': 'Yale', 'equipment': 'forklift'},
    # Extra aerial
    {'name': 'Skyjack', 'query': 'Skyjack hoogwerker', 'category': 133, 'brand': 'Skyjack', 'equipment': 'aerial_lift'},
    {'name': 'Dingli', 'query': 'Dingli hoogwerker', 'category': 133, 'brand': 'Dingli', 'equipment': 'aerial_lift'},
    # Extra telehandler
    {'name': 'Bobcat Telehandler', 'query': 'Bobcat telehandler', 'category': 133, 'brand': 'Bobcat', 'equipment': 'telehandler'},
]

MIN_PRICE = 500
MAX_PRICE = 200000


class MachineseekerScraper:
    BASE_URL = 'https://www.machineseeker.nl'
    SEARCH_URL = 'https://www.machineseeker.nl/main/search/index'

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.listings = []
        self.known_ids = set()
        self.counter = 0

    def _delay(self):
        time.sleep(random.uniform(2, 5))

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
        patterns = [
            r'(\d[\d\s.]*)\s*EUR',
            r'EUR\s*(\d[\d\s.]*)',
            r'(\d[\d\s.]*)\s*\u20ac',
            r'\u20ac\s*(\d[\d\s.]*)',
            r'(\d[\d\s.,]+)\s*,-',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                price_str = match.group(1).replace('.', '').replace(' ', '').replace(',', '')
                try:
                    price = int(price_str)
                    if MIN_PRICE < price < MAX_PRICE:
                        return price
                except ValueError:
                    continue
        return 0

    def _extract_year(self, text):
        match = re.search(r'(?:Bouwjaar|Baujahr|Year)[:\s]*(\d{4})', text)
        if match:
            return int(match.group(1))
        match = re.search(r'\b(20[0-2]\d|199\d)\b', text)
        return int(match.group(1)) if match else 0

    def _extract_hours(self, text):
        patterns = [
            r'(\d[\d.]*)\s*(?:m/u|Bst|uur|hours?|Std)',
            r'(?:Bedrijfsuren|Betriebsstunden|Hours)[:\s]*(\d[\d.]*)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                h = int(match.group(1).replace('.', ''))
                if 0 <= h < 100000:
                    return h
        return 0

    def _extract_location(self, text):
        # Look for country + city patterns
        patterns = [
            r'(Nederland|Germany|Belgium|France|Deutschland|Belgien|Frankreich|UK|Duitsland|Belgi\u00eb|Frankrijk)[,\s]+([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)',
            r'([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)[,\s]+(NL|DE|BE|FR|UK|AT|CH)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0).strip()
        return ''

    def search(self, query, category_id=133, brand='', equipment_type='', max_pages=5):
        """Search Machineseeker with a query string."""
        search_word = query.replace(' ', '+')
        prefix = f'MS-{brand or query.split()[0]}'

        for page in range(1, max_pages + 1):
            url = f'{self.SEARCH_URL}?search-word={search_word}&category-ids={category_id}&page={page}'
            log.info(f'[{prefix}] Page {page}: {url}')

            soup = self._fetch(url)
            if not soup:
                break

            # Machineseeker uses <article> tags for listings
            items = soup.find_all('article')
            if not items:
                # Fallback selectors
                items = soup.find_all('div', class_=lambda c: c and ('listing' in str(c).lower() or 'advert' in str(c).lower()))
            if not items:
                items = soup.find_all('section', class_=lambda c: c and 'grid-card' in str(c))

            if not items:
                log.info(f'[{prefix}] No items found on page {page}')
                break

            page_count = 0
            for item in items:
                try:
                    text = item.get_text(separator=' ')
                    if len(text) < 30:
                        continue

                    # Skip non-listing articles (ads, navigation, etc.)
                    if 'Gecertificeerde' in text and len(text) < 100:
                        continue

                    # Extract title
                    title_el = item.find('h2') or item.find('h3') or item.find('strong')
                    if not title_el:
                        continue
                    title = title_el.get_text().strip()
                    if not title or len(title) < 3:
                        continue

                    # Extract link
                    link = item.find('a', href=True)
                    href = ''
                    if link:
                        href = link.get('href', '')
                        if href.startswith('/'):
                            href = self.BASE_URL + href

                    # Dedup by title+price combo
                    price = self._extract_price(text)
                    dedup_key = f'{title}_{price}'
                    if dedup_key in self.known_ids:
                        continue
                    self.known_ids.add(dedup_key)

                    # Extract image
                    img = item.find('img')
                    image = ''
                    if img:
                        image = img.get('src', '') or img.get('data-src', '')
                        if image.startswith('//'):
                            image = 'https:' + image

                    self.counter += 1
                    listing = {
                        'id': f'{prefix}-{self.counter}',
                        'model': title[:60],
                        'brand': brand or query.split()[0],
                        'year': self._extract_year(text),
                        'hours': self._extract_hours(text),
                        'price': price,
                        'source': 'machineseeker',
                        'region': 'EU',
                        'location': self._extract_location(text),
                        'equipment_type': equipment_type,
                        'url': href,
                        'image': image,
                    }
                    self.listings.append(listing)
                    page_count += 1
                    log.info(f'  + {title[:40]} - EUR{price:,}' if price else f'  + {title[:40]}')

                except Exception as e:
                    log.debug(f'Parse error: {e}')
                    continue

            log.info(f'[{prefix}] Page {page}: {page_count} listings')
            if page_count == 0:
                break
            self._delay()

        return self.listings

    def run_daily(self, max_pages=3):
        """Run all pre-configured daily searches."""
        log.info(f'\n{"="*60}')
        log.info(f'MACHINESEEKER DAILY SCRAPE — {len(DAILY_SEARCHES)} categories')
        log.info(f'{"="*60}')

        for config in DAILY_SEARCHES:
            log.info(f'\n--- {config["name"]} ---')
            self.search(
                query=config['query'],
                category_id=config['category'],
                brand=config['brand'],
                equipment_type=config['equipment'],
                max_pages=max_pages
            )
            self._delay()

        log.info(f'\nTotal: {len(self.listings)} specialist listings')
        return self.listings

    def save_csv(self, filename='machineseeker_listings.csv'):
        output_dir = Path(__file__).parent.parent / 'output'
        output_dir.mkdir(exist_ok=True)
        filepath = output_dir / filename

        if not self.listings:
            log.warning('No listings to save')
            return None

        fieldnames = ['id', 'model', 'brand', 'year', 'hours', 'price', 'source', 'region']
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(self.listings)

        log.info(f'Saved {len(self.listings)} listings to {filepath}')
        return str(filepath)

    def summary(self):
        brands = {}
        types = {}
        for l in self.listings:
            brands[l['brand']] = brands.get(l['brand'], 0) + 1
            types[l.get('equipment_type', '?')] = types.get(l.get('equipment_type', '?'), 0) + 1

        print(f'\n{"="*50}')
        print(f'MACHINESEEKER SCRAPE SUMMARY')
        print(f'{"="*50}')
        print(f'Total: {len(self.listings)} specialist listings')
        print(f'\nBy brand:')
        for b, c in sorted(brands.items(), key=lambda x: -x[1]):
            print(f'  {b:20s} {c:4d}')
        print(f'\nBy type:')
        for t, c in sorted(types.items(), key=lambda x: -x[1]):
            print(f'  {t:20s} {c:4d}')


def main():
    parser = argparse.ArgumentParser(description='Machineseeker Specialist Scraper')
    parser.add_argument('--query', '-q', type=str, help='Custom search query')
    parser.add_argument('--pages', '-p', type=int, default=3, help='Max pages per search')
    parser.add_argument('--quick', action='store_true', help='Quick mode (1 page)')
    args = parser.parse_args()

    pages = 1 if args.quick else args.pages

    scraper = MachineseekerScraper()

    if args.query:
        scraper.search(args.query, max_pages=pages)
    else:
        scraper.run_daily(max_pages=pages)

    scraper.save_csv()
    scraper.summary()


if __name__ == '__main__':
    main()
