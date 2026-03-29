#!/usr/bin/env python3
import csv
from pathlib import Path

output_dir = Path(__file__).parent.parent / "output"

listings = []

# Load Mascus
mascus_file = output_dir / "mascus_listings.csv"
if mascus_file.exists():
    with open(mascus_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        listings.extend(list(reader))
    print(f"✓ Loaded {len([l for l in listings if l.get('source') == 'mascus'])} from Mascus")

# Load Mascus DE
mascus_de_file = output_dir / "mascus_de_listings.csv"
if mascus_de_file.exists():
    with open(mascus_de_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        listings.extend(list(reader))
    print(f"+ Loaded {len([l for l in listings if l.get('region') == 'DE' and l.get('source') == 'mascus'])} from Mascus DE")

# Load TruckScout24
ts24_file = output_dir / "truckscout24_listings.csv"
if ts24_file.exists():
    with open(ts24_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        listings.extend(list(reader))
    print(f"✓ Loaded {len([l for l in listings if l.get('source') == 'truckscout24'])} from TruckScout24")

# Save merged
merged_file = output_dir / "all_listings.csv"
if listings:
    with open(merged_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=listings[0].keys())
        writer.writeheader()
        writer.writerows(listings)
    print(f"\n✅ Merged {len(listings)} listings to {merged_file}")
else:
    print("No listings found")
