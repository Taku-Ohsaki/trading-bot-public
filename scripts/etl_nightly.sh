#!/usr/bin/env bash
python scripts/fetch_prices_daily.py --symbol universe.csv --start $(date -d '1 day ago' +%F) --end $(date +%F)