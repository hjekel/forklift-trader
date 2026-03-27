#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import json
import csv
import time
import random
import re
import logging
from pathlib import Path
from datetime import datetime
from config import HEADERS, MIN_DELAY, MAX_DELAY, TOYOTA_MODELS, MIN_PRICE, MAX_PRICE

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MascusScraperToyota:
    BASE_URL = 'https://www.mascus.nl'
    SEARCH_URL = 'https://www.mascus.nl/laden-en-lossen/heftrucks'
    SEARCH_PARAMS = {'brands': 'toyota'}
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.listings = []
        self.known_urls = set()
    
    def _delay(self):
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
    
    def _fetch(self, url):
        for attempt in range(3):
            try:
                response = self.session.get(url, timeout=30)
                if response.status_code == 200:
                    return BeautifulSoup(response.text, 'html.parser')
                elif response.status_code == 429:
                    logger.warning('Rate limited, waiting 60s...')
                    time.sleep(60)
                    continue
                else:
                    logger.warning(f'HTTP {response.status_code}: {url}')
            except Exception as e:
                logger.debug(f'Error: {e}')
                time.sleep(5 * (attempt + 1))
        return None
    
    def _extract_model(self, text):
        text_upper = text.upper()
        patterns = [
            r'\b(8F[A-Z]{1,4}\d{2,3}[A-Z]?)\b',
            r'\b(52-?8\s*F[A-Z]{2,4}\s*\d{2,3})\b',
            r'\b(FB[A-Z]{1,3}\d{2,3})\b',
            r'\b(FD\d{2,3}[A-Z]?)\b',
            r'\b(FG\d{2,3}[A-Z]?)\b',
            r'\b(RRE\d{2,3})\b',
            r'\b(OSE\d{2,3})\b',
            r'\b(BT\s*[A-Z]{2,4}\d{2,3})\b',
        ]
        for pattern in patterns:
            match = re.search(pattern, text_upper)
            if match:
                return match.group(1).replace(' ', '')
        return None
    
    def _extract_price(self, text):
        patterns = [
            r'([\d.]+)\s*EUR',
            r'€\s*([\d.,]+)',
            r'([\d.,]+)\s*€',
            r'EUR\s*([\d.,]+)',
        ]
        for pattern in patterns:
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
        if match:
            return int(match.group(1))
        return 2020
    
    def _extract_hours(self, text):
        patterns = [
            r'(\d+)\s*[hu](?:ur)?s?',
            r'(\d+)\s*hours?',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                hours = int(match.group(1))
                if 0 <= hours < 50000:
                    return hours
        return 0
    
    def scrape_search_results(self, max_pages=5, quick=False):
        if quick:
            max_pages = 1
            logger.info('Quick mode: first page only')
        
        page = 1
        while page <= max_pages:
            params = {**self.SEARCH_PARAMS, 'page': page}
            url = f'{self.SEARCH_URL}/toyota?page={page}'
            logger.info(f'Scraping page {page}...')

            soup = self._fetch(url)
            if not soup:
                break

            items = soup.find_all('div', class_=lambda c: c and 'searchResultItemWrapper' in c)
            if not items:
                logger.info('No more items')
                break

            for item in items:
                try:
                    title_elem = item.find('h2') or item.find('h3')
                    if not title_elem:
                        continue

                    title = title_elem.get_text().strip()

                    link_elem = item.find('a', href=True)
                    url_item = link_elem['href'] if link_elem else ''
                    if url_item in self.known_urls:
                        continue
                    self.known_urls.add(url_item)

                    item_text = item.get_text()
                    model = self._extract_model(title)
                    if not model:
                        continue

                    price = self._extract_price(item_text)
                    if price == 0:
                        continue

                    listing = {
                        'id': f'MASCUS-{len(self.listings)+1}',
                        'model': model,
                        'year': self._extract_year(item_text),
                        'hours': self._extract_hours(item_text),
                        'price': price,
                        'source': 'mascus',
                        'region': 'NL',
                    }

                    self.listings.append(listing)
                    logger.info(f'  + {model} {listing["year"]} - EUR{listing["price"]:,}')

                except Exception as e:
                    logger.debug(f'Parse error: {e}')
                    continue

            page += 1
            if quick:
                break
            self._delay()
        
        return self.listings
    
    def save_csv(self, filename='mascus_listings.csv'):
        output_dir = Path('../output')
        output_dir.mkdir(exist_ok=True)
        filepath = output_dir / filename
        
        if not self.listings:
            return None
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'model', 'year', 'hours', 'price', 'source', 'region'])
            writer.writeheader()
            writer.writerows(self.listings)
        
        logger.info(f'Saved CSV to {filepath}')
        return str(filepath)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Mascus Toyota Scraper')
    parser.add_argument('--quick', '-q', action='store_true', help='Quick test mode')
    parser.add_argument('--pages', '-p', type=int, default=5, help='Max pages')
    args = parser.parse_args()
    
    print('\n' + '='*60)
    print('MASCUS TOYOTA SCRAPER v0.1')
    print('='*60 + '\n')
    
    scraper = MascusScraperToyota()
    scraper.scrape_search_results(max_pages=args.pages, quick=args.quick)
    scraper.save_csv()
    
    print(f'\nFound {len(scraper.listings)} listings\n')

if __name__ == '__main__':
    main()
