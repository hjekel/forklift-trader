#!/bin/bash
# ForkFlip QA Check — draai VOOR elke push
# Blokkeert als data minder dan 100 listings bevat

PRICE_COUNT=$(grep -o '"price"' index.html | wc -l)

echo "=============================="
echo "ForkFlip QA Check"
echo "=============================="
echo "Listings in index.html: $PRICE_COUNT"

if [ "$PRICE_COUNT" -lt 100 ]; then
  echo ""
  echo "❌ FOUT: Slechts $PRICE_COUNT listings gevonden!"
  echo "   Data is waarschijnlijk kwijt."
  echo "   NIET PUSHEN."
  echo ""
  echo "   Fix: python3 -c \"import csv,json,re; ...\""
  echo "   Of: run embed script opnieuw"
  exit 1
fi

echo "✅ Data intact ($PRICE_COUNT listings). Veilig om te pushen."
echo ""

# Check for common JS errors
if grep -q "renderSavedSpecs" index.html; then
  echo "⚠️  WARNING: renderSavedSpecs() found — this function was removed!"
fi

echo "=============================="
