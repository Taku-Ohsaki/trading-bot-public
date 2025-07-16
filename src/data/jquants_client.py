"""
J-Quantsからティックデータを取得するクライアント
"""
import os
from datetime import datetime
from dateutil import tz
from typing import List, Dict
import pandas as pd
import jquantsapi
from dotenv import load_dotenv


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
    
    def get_tick(self, symbol: str, date: str) -> List[Dict]:
        """
        指定された銘柄と日付のティックデータを取得
        
        Args:
            symbol: 銘柄コード（例: "7203"）
            date: 日付文字列（例: "2023-01-01"）
        
        Returns:
            ティックデータのリスト
            [{"time":"09:00:01","price":2001,"volume":100}, ...]
        """
        # 日付文字列をdatetimeオブジェクトに変換
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        date_obj = date_obj.replace(tzinfo=tz.gettz("Asia/Tokyo"))
        
        # 価格データを取得（全コードのデータを取得）
        df = self.client.get_price_range(
            start_dt=date_obj,
            end_dt=date_obj
        )
        
        # デバッグ用：DataFrameの構造を確認
        print(f"DataFrame columns: {df.columns.tolist()}")
        print(f"DataFrame shape: {df.shape}")
        if not df.empty:
            print(f"Sample data:\n{df.head()}")
        
        # 指定したシンボルのデータのみをフィルタリング
        symbol_5digit = str(symbol)+"0"
        
        # デバッグ用：利用可能なコードを表示
        print(f"Looking for symbol: '{symbol_5digit}'")
        print(f"Available codes: {sorted(df['Code'].unique())[:10]}")
        
        df = df[df['Code'] == symbol_5digit]
        
        print(f"Filtered DataFrame shape: {df.shape}")
        
        if df.empty:
            print("No tick data found")
            return []
        
        # DataFrameをティックデータのリストに変換
        ticks = []
        for _, row in df.iterrows():
            # DateTimeカラムがない場合はDateを使用
            time_str = "09:00:00"  # デフォルト時刻
            if 'DateTime' in row:
                time_str = row['DateTime'].strftime("%H:%M:%S") if pd.notna(row['DateTime']) else "09:00:00"
            elif 'Date' in row:
                # 日付のみの場合は市場開始時刻を使用
                time_str = "09:00:00"
            
            ticks.append({
                "time": time_str,
                "price": float(row.get("Close", 0)) if pd.notna(row.get("Close")) else 0,
                "volume": int(row.get("Volume", 0)) if pd.notna(row.get("Volume")) else 0
            })
        
        return ticks