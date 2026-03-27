# Forklift Trader — Toyota Heftruck Opportunity Scanner

Market intelligence tool for independent Toyota forklift traders. Spot opportunities, match supply with demand, close deals faster.

## What it does

**Opportunity Scanner** — Scan marketplaces (Mascus, TruckScout24, etc.) for undervalued Toyota forklifts
**Demand Matcher** — Find 'wanted' ads + match with available inventory
**Price Intelligence** — Real market data per model, year, hours, region
**Deal Dashboard** — Track opportunities, margins, and active deals

## Quick Start

### 1. Install dependencies
\\\powershell
cd scrapers
pip install -r requirements.txt
cd ..
\\\

### 2. Run scraper (test mode)
\\\powershell
python scrapers/mascus_toyota.py --quick
\\\

Expected output:
- Fetches 1 page from Mascus.nl
- Finds ~15-20 Toyota forklifts
- Saves to output/mascus_listings.csv
- Shows stats

### 3. View dashboard
- Open \index.html\ in browser
- Click 'Import CSV'
- Select \output/mascus_listings.csv\
- See real Mascus data in dashboard ?

## Project Structure

\\\
forklift-trader/
+-- README.md                    # This file
+-- index.html                   # Dashboard (open in browser)
+-- .gitignore                   # Git ignore rules
+-- data/
¦   +-- toyota_models.json       # Model reference database
+-- scrapers/
¦   +-- mascus_toyota.py         # Main Mascus scraper
¦   +-- config.py                # Shared config (headers, models, constants)
¦   +-- requirements.txt         # Python dependencies
+-- output/                      # Created on first scrape
    +-- mascus_listings.json
    +-- mascus_listings.csv
\\\

## Technology

- **Frontend**: HTML/JS (no framework)
- **Backend**: Python 3 (requests + BeautifulSoup)
- **Data**: JSON files (simple, git-friendly)
- **Storage**: CSV for import/export
- **VCS**: Git

## Toyota Models (Supported)

### Electric
8FBE15, 8FBE18, 8FBE20, 8FBMK16, 8FBMK20, 8FBMK25

### Diesel/LPG
8FD15, 8FD18, 8FD20, 8FD25, 8FD30, 8FG15, 8FG18, 8FG20, 8FG25, 8FG30

### Reach Truck
BT Reflex RRE140, RRE160, RRE200, RRE250

### Order Picker
BT Optio OSE100, OSE120, OSE250

## Data Sources

| Source | Region | Status |
|--------|--------|--------|
| Mascus.nl | NL/BE | ? Working |
| TruckScout24.de | DE | ?? Next |
| Marktplaats.nl | NL | ?? Future |
| eBay Kleinanzeigen | DE | ?? Future |

## User

**Marcel** — Independent Toyota forklift trader
**Goal**: Spot deals faster than competitors
**Profit model**: Information asymmetry + speed

## Philosophy

"Sales-first logic":

1. **PRIJS (Price)** ? What is it worth? (market data)
2. **OPPORTUNITIES** ? Where are the deals? (opportunity scan)
3. **POSITIE (Position)** ? What can I buy/sell? (deal dashboard)

## Next Phases

- Phase 1: Mascus Scraper ? DONE
- Phase 2: Basic Frontend ? DONE
- Phase 3: TruckScout24 Scraper ? NEXT
- Phase 4: Wanted Ad Scanner FUTURE
- Phase 5: Matching Engine FUTURE

## Git Workflow

After each task:

\\\powershell
git status                              # See changes
git add .                               # Stage all
git commit -m 'feat: description'       # Commit
\\\

Example commits:
\\\
git commit -m 'feat: mascus scraper working with real data'
git commit -m 'feat: dashboard CSV import/export'
git commit -m 'fix: price extraction for German listings'
\\\

## Troubleshooting

**Q: BeautifulSoup not found?**
\\\powershell
pip install -r scrapers/requirements.txt
\\\

**Q: Module 'config' not found?**
Make sure you're in scrapers/ folder or add it to Python path.

**Q: Mascus returns 403 Forbidden?**
Increase delays in config.py — site detected the scraper.

**Q: CSV import doesn't work?**
- Check CSV headers: \model,year,hours,price,source\
- Prices must be numeric (no € symbol)
- Open browser console (F12) for errors

## License

MIT

## Contact

Henk Jekel — hjekel@gmail.com

---

**Status**: v0.1 — Alpha (Mascus scraper + basic dashboard)
**Last updated**: March 27, 2026
