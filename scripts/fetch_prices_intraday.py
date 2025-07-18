#!/usr/bin/env python3
"""
イントラデイ価格データ取得スクリプト
J-Quants APIから1分足データを取得してPostgreSQLに保存
"""

import argparse
import os
import sys
import psycopg2
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

# プロジェクトルートをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.data.jquants_client import JQuantsClient


class IntradayPricesFetcher:
    """イントラデイ価格データ取得クラス"""
    
    def __init__(self):
        """初期化"""
        load_dotenv()
        self.jquants_client = JQuantsClient()
        
        # PostgreSQL接続設定
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': os.getenv('POSTGRES_PORT', '5432'),
            'dbname': os.getenv('POSTGRES_DB', 'trading_bot'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'password')
        }
    
    def get_enhanced_1min_data(self, symbol: str, date: str) -> pd.DataFrame:
        """
        1分足データを取得してOHLCVフォーマットに変換
        
        Args:
            symbol: 銘柄コード
            date: 日付 (YYYY-MM-DD)
        
        Returns:
            OHLCVデータのDataFrame
        """
        # 基本的な1分足データを取得
        df = self.jquants_client.get_prices_1min(symbol, date)
        
        if df.empty:
            return pd.DataFrame(columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
        
        # 市場時間内の1分足データを生成（9:00-15:00）
        market_hours = []
        base_date = datetime.strptime(date, "%Y-%m-%d")
        
        for hour in range(9, 15):
            for minute in range(0, 60):
                # 11:30-12:30は昼休み（除外）
                if hour == 11 and minute >= 30:
                    continue
                if hour == 12 and minute < 30:
                    continue
                
                dt = base_date.replace(hour=hour, minute=minute)
                market_hours.append(dt)
        
        # 最初の価格を開始価格として使用
        if len(df) > 0:
            base_price = df.iloc[0]['price']
        else:
            return pd.DataFrame(columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
        
        # 各分のOHLCVデータを生成
        ohlcv_data = []
        for dt in market_hours:
            # 実際のデータがある場合はそれを使用、なければ前の価格を使用
            matching_rows = df[df['time'].str.startswith(dt.strftime("%Y-%m-%d %H:%M"))]
            
            if len(matching_rows) > 0:
                price = matching_rows.iloc[0]['price']
                volume = matching_rows.iloc[0]['volume']
            else:
                # データがない場合は前の価格を使用（実際の実装では前の終値を使用）
                price = base_price
                volume = 0
            
            ohlcv_data.append({
                'datetime': dt.strftime("%Y-%m-%d %H:%M:%S"),
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'volume': volume
            })
        
        return pd.DataFrame(ohlcv_data)
    
    def insert_to_database(self, df: pd.DataFrame, symbol: str) -> int:
        """
        データをPostgreSQLに挿入
        
        Args:
            df: 挿入するデータフレーム
            symbol: 銘柄コード
        
        Returns:
            挿入された行数
        """
        if df.empty:
            return 0
        
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # データを挿入（COPY文を使用して高速化）
            insert_query = """
                COPY intraday_prices (datetime, symbol, open, high, low, close, volume)
                FROM STDIN WITH CSV
            """
            
            # データを文字列に変換
            csv_data = []
            for _, row in df.iterrows():
                csv_line = f"{row['datetime']},{symbol},{row['open']},{row['high']},{row['low']},{row['close']},{row['volume']}"
                csv_data.append(csv_line)
            
            # COPY文でデータを挿入
            cursor.copy_expert(insert_query, open('/dev/stdin', 'r'))
            
            # 代替案：executemany を使用
            insert_sql = """
                INSERT INTO intraday_prices (datetime, symbol, open, high, low, close, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (datetime, symbol) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume
            """
            
            data_tuples = []
            for _, row in df.iterrows():
                data_tuples.append((
                    row['datetime'],
                    symbol,
                    float(row['open']),
                    float(row['high']),
                    float(row['low']),
                    float(row['close']),
                    int(row['volume'])
                ))
            
            cursor.executemany(insert_sql, data_tuples)
            conn.commit()
            
            inserted_rows = cursor.rowcount
            cursor.close()
            
            return inserted_rows
            
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def fetch_and_store(self, symbol: str, date: str) -> int:
        """
        指定された銘柄と日付のイントラデイデータを取得してDBに保存
        
        Args:
            symbol: 銘柄コード
            date: 日付 (YYYY-MM-DD)
        
        Returns:
            挿入された行数
        """
        print(f"取得開始: {symbol} {date}")
        
        # データを取得
        df = self.get_enhanced_1min_data(symbol, date)
        
        if df.empty:
            print(f"データが見つかりませんでした: {symbol} {date}")
            return 0
        
        # データベースに挿入
        inserted_rows = self.insert_to_database(df, symbol)
        
        print(f"挿入完了: {inserted_rows} 行を挿入しました")
        return inserted_rows


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='イントラデイ価格データ取得スクリプト')
    parser.add_argument('--symbol', required=True, help='銘柄コード (例: 7203)')
    parser.add_argument('--date', required=True, help='日付 (YYYY-MM-DD形式)')
    
    args = parser.parse_args()
    
    try:
        fetcher = IntradayPricesFetcher()
        inserted_rows = fetcher.fetch_and_store(args.symbol, args.date)
        print(f"処理完了: {inserted_rows} 行を挿入しました")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()