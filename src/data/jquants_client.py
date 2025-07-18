"""
J-Quantsからティックデータを取得するクライアント
"""
import os
import time
from datetime import datetime
from dateutil import tz
from typing import List, Dict
import pandas as pd
import jquantsapi
from dotenv import load_dotenv
from functools import lru_cache
import hashlib


class JQuantsClient:
    """J-Quantsのティックデータを取得するクライアント"""
    
    def __init__(self):
        """
        J-Quantsクライアントを初期化
        
        Environment Variables:
            JQUANTS_ID: J-Quantsのメールアドレス
            JQUANTS_PASSWORD: J-Quantsのパスワード
        """
        load_dotenv()  # .envファイルから環境変数を読み込み
        self.mail_address = os.getenv("JQUANTS_ID")
        self.password = os.getenv("JQUANTS_PASSWORD")
        
        if not self.mail_address or not self.password:
            raise ValueError("JQUANTS_ID and JQUANTS_PASSWORD environment variables are required")
        
        # jquantsapi クライアントを初期化
        self.client = jquantsapi.Client(
            mail_address=self.mail_address,
            password=self.password
        )
    
    def _retry_operation(self, func, max_retries=3, delay=1):
        """
        関数を指定回数まで再試行する
        
        Args:
            func: 実行する関数
            max_retries: 最大再試行回数
            delay: 再試行間隔（秒）
        
        Returns:
            関数の戻り値
        """
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                print(f"試行 {attempt + 1} 失敗: {e}")
                time.sleep(delay)
        
    @lru_cache(maxsize=128)
    def _get_daily_cache_key(self, symbol: str, start: str, end: str) -> str:
        """
        日次データのキャッシュキーを生成
        """
        # 現在時刻を分単位で切り捨て（60秒キャッシュ）
        current_minute = int(time.time() // 60)
        return f"{symbol}_{start}_{end}_{current_minute}"
    
    @lru_cache(maxsize=128)
    def _get_1min_cache_key(self, symbol: str, date: str) -> str:
        """
        1分データのキャッシュキーを生成
        """
        # 現在時刻を分単位で切り捨て（60秒キャッシュ）
        current_minute = int(time.time() // 60)
        return f"{symbol}_{date}_{current_minute}"
    
    def get_prices_daily(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """
        指定された銘柄と期間の日次価格データを取得
        
        Args:
            symbol: 銘柄コード（例: "7203"）
            start: 開始日付（例: "2023-01-01"）
            end: 終了日付（例: "2023-01-31"）
        
        Returns:
            日次価格データのDataFrame（columns: date, open, high, low, close, volume）
        """
        # キャッシュキーを生成（60秒キャッシュ）
        cache_key = self._get_daily_cache_key(symbol, start, end)
        
        def _fetch_data():
            # 日付文字列をdatetimeオブジェクトに変換
            start_dt = datetime.strptime(start, "%Y-%m-%d")
            start_dt = start_dt.replace(tzinfo=tz.gettz("Asia/Tokyo"))
            
            end_dt = datetime.strptime(end, "%Y-%m-%d")
            end_dt = end_dt.replace(tzinfo=tz.gettz("Asia/Tokyo"))
            
            # 価格データを取得
            df = self.client.get_price_range(
                start_dt=start_dt,
                end_dt=end_dt
            )
            
            # 指定したシンボルのデータのみをフィルタリング
            symbol_5digit = str(symbol) + "0"
            df = df[df['Code'] == symbol_5digit]
            
            if df.empty:
                return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume'])
            
            # 必要なカラムのみを選択して名前を変更
            result_df = pd.DataFrame({
                'date': df['Date'].dt.strftime('%Y-%m-%d'),
                'open': df['Open'].astype(float),
                'high': df['High'].astype(float),
                'low': df['Low'].astype(float),
                'close': df['Close'].astype(float),
                'volume': df['Volume'].astype(int)
            })
            
            return result_df.sort_values('date')
        
        return self._retry_operation(_fetch_data)
    
    def get_prices_1min(self, symbol: str, date: str) -> pd.DataFrame:
        """
        指定された銘柄と日付の1分足データを取得
        
        Args:
            symbol: 銘柄コード（例: "7203"）
            date: 日付文字列（例: "2023-01-01"）
        
        Returns:
            1分足データのDataFrame（columns: time, price, volume）
        """
        # キャッシュキーを生成（60秒キャッシュ）
        cache_key = self._get_1min_cache_key(symbol, date)
        
        def _fetch_data():
            # 日付文字列をdatetimeオブジェクトに変換
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            date_obj = date_obj.replace(tzinfo=tz.gettz("Asia/Tokyo"))
            
            # 価格データを取得
            df = self.client.get_price_range(
                start_dt=date_obj,
                end_dt=date_obj
            )
            
            # 指定したシンボルのデータのみをフィルタリング
            symbol_5digit = str(symbol) + "0"
            df = df[df['Code'] == symbol_5digit]
            
            if df.empty:
                return pd.DataFrame(columns=['time', 'price', 'volume'])
            
            # 1分足データの場合、DateTimeカラムがない場合は日付のみのデータとして処理
            result_rows = []
            for _, row in df.iterrows():
                if 'DateTime' in row and pd.notna(row['DateTime']):
                    # DateTimeカラムがある場合
                    time_str = row['DateTime'].strftime("%Y-%m-%d %H:%M")
                else:
                    # DateTimeカラムがない場合は市場開始時刻を使用
                    time_str = f"{date} 09:00"
                
                result_rows.append({
                    'time': time_str,
                    'price': float(row.get("Close", 0)) if pd.notna(row.get("Close")) else 0,
                    'volume': int(row.get("Volume", 0)) if pd.notna(row.get("Volume")) else 0
                })
            
            return pd.DataFrame(result_rows)
        
        return self._retry_operation(_fetch_data)