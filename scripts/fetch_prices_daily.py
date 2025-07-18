#!/usr/bin/env python3
"""
日次価格データをJ-Quantsから取得してPostgreSQLに保存するスクリプト
"""
import sys
import os
import argparse
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# src/data/jquants_client.pyをインポートするためのパス追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from data.jquants_client import JQuantsClient


def main():
    """
    メイン関数
    """
    # 引数解析
    parser = argparse.ArgumentParser(description='J-Quantsから日次価格データを取得してDBに保存')
    parser.add_argument('--symbol', required=True, help='銘柄コード（例: 7203）')
    parser.add_argument('--start', required=True, help='開始日付（例: 2024-01-01）')
    parser.add_argument('--end', required=True, help='終了日付（例: 2025-07-18）')
    
    args = parser.parse_args()
    
    # 環境変数を読み込み
    load_dotenv()
    
    try:
        # J-Quantsクライアントを初期化
        print(f"J-Quantsから価格データを取得中... (銘柄: {args.symbol}, 期間: {args.start} - {args.end})")
        client = JQuantsClient()
        
        # 日次価格データを取得
        df = client.get_prices_daily(args.symbol, args.start, args.end)
        
        if df.empty:
            print("取得できたデータがありません。")
            return
        
        print(f"取得したデータ件数: {len(df)}件")
        
        # PostgreSQLに接続
        conn = psycopg2.connect(
            host=os.getenv('PGHOST', 'localhost'),
            port=os.getenv('PGPORT', '5432'),
            user=os.getenv('PGUSER', 'postgres'),
            password=os.getenv('PGPASSWORD', 'postgres'),
            database=os.getenv('PGDATABASE', 'postgres')
        )
        
        cursor = conn.cursor()
        
        # pricesテーブルが存在しない場合は作成
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                date DATE,
                symbol VARCHAR(10),
                open DECIMAL(10,2),
                high DECIMAL(10,2),
                low DECIMAL(10,2),
                close DECIMAL(10,2),
                volume BIGINT,
                PRIMARY KEY (date, symbol)
            )
        """)
        
        # データを準備（DataFrameをタプルのリストに変換）
        data_tuples = []
        for _, row in df.iterrows():
            data_tuples.append((
                row['date'],
                args.symbol,
                row['open'],
                row['high'],
                row['low'],
                row['close'],
                row['volume']
            ))
        
        # データをバッチ挿入（重複時は更新）
        insert_query = """
            INSERT INTO prices (date, symbol, open, high, low, close, volume)
            VALUES %s
            ON CONFLICT (date, symbol)
            DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume
        """
        
        execute_values(cursor, insert_query, data_tuples)
        
        # 挿入された行数を取得
        inserted_count = cursor.rowcount
        
        # コミット
        conn.commit()
        
        print(f"データベースに挿入/更新された行数: {inserted_count}件")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        if 'conn' in locals():
            conn.rollback()
        sys.exit(1)
    
    finally:
        # クリーンアップ
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()


if __name__ == '__main__':
    main()