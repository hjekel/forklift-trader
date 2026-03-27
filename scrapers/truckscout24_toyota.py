#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import csv, logging, re, time, random
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class TruckScout24Scraper:
    SEARCH_URL = "https://www.truckscout24.de/main/search/index?search-word=Gabelstapler&manufacturers%5B%5D=Toyota&manufacturer-filter=Toyota"
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    def __init__(self):
        self.output_dir = Path(__file__).parent.parent / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.listings = []
    
    def _fetch(self, page=1):
        url = f"{self.SEARCH_URL}&pageNumber={page}"
        logger.info(f"Page {page}...")
        try:
            r = self.session.get(url, timeout=30)
            return BeautifulSoup(r.text, 'html.parser') if r.status_code == 200 else None
        except Exception as e:
            logger.error(f"Error: {e}")
            return None
    
    def scrape(self, max_pages=1, quick=False):
        for page in range(1, max_pages + 1):
            soup = self._fetch(page)
            if not soup:
                break
            
            # Find listing cards by looking for price + year + hours pattern
            # Real listings have: "Zustand: ... Baujahr: YYYY Betriebsstunden: XXX h"
            
            pattern = r'Zustand:.*?Baujahr:\s*(\d{4}).*?Betriebsstunden:\s*([\d.]+)\s*h'
            
            # Find all text blocks matching this pattern
            all_divs = soup.find_all(['div', 'section', 'article'])
            found = 0
            
            for div in all_divs:
                text = div.get_text()
                
                # Must have the listing detail pattern
                if not re.search(pattern, text):
                    continue
                
                # Must have price
                price_match = re.search(r'([\d.]+)\s*€', text)
                if not price_match:
                    continue
                
                # Exclude sidebar (has "Filter entfernen", "Modell:", etc without actual listings)
                if 'Filter entfernen' in text or 'field-models' in str(div.get('class', '')):
                    continue
                
                # Extract model: find "Toyota" then next word(s) until newline/km/Apeldoorn
                model_match = re.search(r'Toyota\s+([A-Z0-9\s/\-]+?)(?:\n|Apeldoorn|km|\d{2,})', text)
                if not model_match:
                    continue
                
                model = model_match.group(1).strip()
                if len(model) > 30 or len(model) < 2:
                    continue
                
                # Extract data
                year_match = re.search(r'Baujahr:\s*(\d{4})', text)
                year = int(year_match.group(1)) if year_match else 0
                
                hours_match = re.search(r'Betriebsstunden:\s*([\d.]+)\s*h', text)
                hours = int(hours_match.group(1).replace('.', '')) if hours_match else 0
                
                price_str = price_match.group(1).replace('.', '')
                try:
                    price = int(price_str)
                except:
                    continue
                
                listing = {
                    'id': f"TS24-{len(self.listings)+1}",
                    'model': model,
                    'year': year,
                    'hours': hours,
                    'price': price,
                    'source': 'truckscout24',
                    'region': 'DE',
                }
                
                self.listings.append(listing)
                found += 1
                logger.info(f"✓ {model} - €{price:,} ({year}, {hours}h)")
            
            logger.info(f"Found {found} listings")
            if quick or found == 0:
                break
            time.sleep(random.uniform(2, 4))
    
    def save_csv(self):
        filepath = self.output_dir / "truckscout24_listings.csv"
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'model', 'year', 'hours', 'price', 'source', 'region'])
            for l in self.listings:
                writer.writerow([l['id'], l['model'], l['year'], l['hours'], l['price'], l['source'], l['region']])
        logger.info(f"Saved {len(self.listings)} listings")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--quick', '-q', action='store_true')
    parser.add_argument('--pages', '-p', type=int, default=1)
    args = parser.parse_args()
    
    scraper = TruckScout24Scraper()
    scraper.scrape(max_pages=args.pages, quick=args.quick)
    scraper.save_csv()
    print(f"\n✅ {len(scraper.listings)} listings\n")
