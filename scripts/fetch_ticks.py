#!/usr/bin/env python3
"""
Fetch tick data from J-Quants API and insert into PostgreSQL
"""
import argparse
import io
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from src.data.jquants_client import JQuantsClient


def main():
    parser = argparse.ArgumentParser(description='Fetch tick data from J-Quants API')
    parser.add_argument('--symbol', required=True, help='Stock symbol (e.g. 7203)')
    parser.add_argument('--date', required=True, help='Date in YYYY-MM-DD format')
    args = parser.parse_args()

    # Initialize J-Quants client
    client = JQuantsClient()
    
    # Fetch tick data
    ticks = client.get_tick(args.symbol, args.date)
    
    if not ticks:
        print("No tick data found")
        return
    
    # Connect to PostgreSQL
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='trading_bot',
        user='postgres',
        password='postgres'
    )
    
    try:
        cursor = conn.cursor()
        
        # Create table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ticks (
                symbol VARCHAR(10),
                date DATE,
                time TIME,
                price DECIMAL(10,2),
                volume INTEGER
            )
        """)
        
        # Prepare data for bulk insert
        data = io.StringIO()
        for tick in ticks:
            data.write(f"{args.symbol}\t{args.date}\t{tick['time']}\t{tick['price']}\t{tick['volume']}\n")
        data.seek(0)
        
        # Bulk insert using copy_from
        cursor.copy_from(
            data,
            'ticks',
            columns=('symbol', 'date', 'time', 'price', 'volume'),
            sep='\t'
        )
        
        conn.commit()
        print(f"inserted {len(ticks)} rows")
        
    finally:
        conn.close()


if __name__ == "__main__":
    main()