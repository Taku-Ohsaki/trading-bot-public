"""
J-Quantsからティックデータを取得するクライアント
"""
import os
import time
import json
from datetime import datetime, timedelta
from dateutil import tz
import pandas as pd
import jquantsapi
from dotenv import load_dotenv
from functools import lru_cache


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
        
        # トークンファイルのパス
        self.token_file = os.path.join(os.path.dirname(__file__), "..", "..", "data", "jquants_token.json")
        
        # jquantsapi クライアントを初期化
        self.client = jquantsapi.Client(
            mail_address=self.mail_address,
            password=self.password
        )
        
        # 保存されたトークンを読み込み
        self._load_token()
    
    def _load_token(self):
        """
        保存されたトークンを読み込む
        """
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, 'r') as f:
                    token_data = json.load(f)
                    
                # トークンの有効期限をチェック
                if token_data.get('expires_at'):
                    expires_at = datetime.fromisoformat(token_data['expires_at'])
                    if datetime.now() < expires_at:
                        # トークンがまだ有効な場合、クライアントに設定
                        if token_data.get('refresh_token'):
                            self.client.set_refresh_token(token_data['refresh_token'])
                        print(f"既存のトークンを読み込みました（有効期限: {expires_at}）")
                        return
                    else:
                        print("保存されたトークンの有効期限が切れています")
                        
        except Exception as e:
            print(f"トークンの読み込みに失敗しました: {e}")
        
        # トークンが無効または存在しない場合、新しいトークンを取得
        self._refresh_token()
    
    def _save_token(self, refresh_token: str):
        """
        トークンを保存する
        
        Args:
            refresh_token: リフレッシュトークン
        """
        try:
            # dataディレクトリを作成
            os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
            
            token_data = {
                'refresh_token': refresh_token,
                'expires_at': (datetime.now() + timedelta(hours=23)).isoformat(),  # 23時間後に期限切れ
                'created_at': datetime.now().isoformat()
            }
            
            with open(self.token_file, 'w') as f:
                json.dump(token_data, f, indent=2)
            
            print(f"トークンを保存しました: {self.token_file}")
            
        except Exception as e:
            print(f"トークンの保存に失敗しました: {e}")
    
    def _refresh_token(self):
        """
        リフレッシュトークンを取得して保存する
        """
        try:
            # 新しいリフレッシュトークンを取得
            refresh_token = self.client.get_refresh_token()
            
            if refresh_token:
                # トークンを保存
                self._save_token(refresh_token)
                print("リフレッシュトークンを更新しました")
            else:
                print("リフレッシュトークンの取得に失敗しました")
                
        except Exception as e:
            print(f"リフレッシュトークンの更新に失敗しました: {e}")
    
    def ensure_token_valid(self):
        """
        トークンの有効性を確認し、必要に応じて更新する
        """
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, 'r') as f:
                    token_data = json.load(f)
                    
                if token_data.get('expires_at'):
                    expires_at = datetime.fromisoformat(token_data['expires_at'])
                    # 有効期限の1時間前にトークンを更新
                    if datetime.now() >= expires_at - timedelta(hours=1):
                        print("トークンの有効期限が近づいています。更新します...")
                        self._refresh_token()
                        
        except Exception as e:
            print(f"トークンの有効性確認に失敗しました: {e}")
    
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
        def _fetch_data():
            # トークンの有効性を確認
            self.ensure_token_valid()
            
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
        def _fetch_data():
            # トークンの有効性を確認
            self.ensure_token_valid()
            
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