#!/usr/bin/env python3
"""Mascus.de scraper - German Toyota forklift listings."""
import sys
sys.path.insert(0, '.')
from mascus_toyota import MascusScraperToyota

class MascusScraperDE(MascusScraperToyota):
    BASE_URL = 'https://www.mascus.de'
    SEARCH_URL = 'https://www.mascus.de/laden-und-lossen/gabelstapler'

    def _make_listing(self, idx):
        """Override region to DE."""
        return 'DE'

    def scrape_search_results(self, max_pages=5, quick=False):
        """Same as parent but with DE region."""
        if quick:
            max_pages = 1
        page = 1
        while page <= max_pages:
            url = f'{self.SEARCH_URL}/toyota?page={page}'
            self._logger_info(f'Scraping Mascus.de page {page}...')
            soup = self._fetch(url)
            if not soup:
                break
            items = soup.find_all('div', class_=lambda c: c and 'searchResultItemWrapper' in c)
            if not items:
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
                        'id': f'MASCUS-DE-{len(self.listings)+1}',
                        'model': model,
                        'year': self._extract_year(item_text),
                        'hours': self._extract_hours(item_text),
                        'price': price,
                        'source': 'mascus',
                        'region': 'DE',
                    }
                    self.listings.append(listing)
                except Exception:
                    continue
            page += 1
            if quick:
                break
            self._delay()
        return self.listings

    def _logger_info(self, msg):
        import logging
        logging.getLogger(__name__).info(msg)

def main():
    import argparse, logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    parser = argparse.ArgumentParser(description='Mascus.de Toyota Scraper')
    parser.add_argument('--quick', '-q', action='store_true')
    parser.add_argument('--pages', '-p', type=int, default=5)
    args = parser.parse_args()

    print('\n' + '='*60)
    print('MASCUS.DE TOYOTA SCRAPER')
    print('='*60 + '\n')

    scraper = MascusScraperDE()
    scraper.scrape_search_results(max_pages=args.pages, quick=args.quick)
    scraper.save_csv('mascus_de_listings.csv')
    print(f'\nFound {len(scraper.listings)} DE listings\n')

if __name__ == '__main__':
    main()
