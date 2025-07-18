#!/usr/bin/env python3
"""
リアルタイムシグナル生成スクリプト
Kafkaから1分足データを受信し、LSTM予測を行い、取引シグナルを生成
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
import pandas_ta as ta
from dotenv import load_dotenv
import logging
from collections import deque
import time
import torch

# プロジェクトルートをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.models.lstm_intraday import LSTMIntradayModel


# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SignalProducer:
    """リアルタイムシグナル生成クラス"""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        初期化
        
        Args:
            model_path: 学習済みモデルのパス（Noneの場合は新規作成）
        """
        load_dotenv()
        
        # Kafka設定
        self.kafka_config = {
            'bootstrap_servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
            'value_deserializer': lambda m: json.loads(m.decode('utf-8')) if m else None,
            'value_serializer': lambda v: json.dumps(v).encode('utf-8')
        }
        
        # Kafkaトピック
        self.input_topic = 'prices.1min'
        self.output_topic = 'signals'
        
        # LSTMモデル
        self.lstm_model = LSTMIntradayModel()
        if model_path and os.path.exists(model_path):
            self.lstm_model.load_state_dict(torch.load(model_path))
            self.lstm_model.is_fitted = True
            logger.info(f"モデルを読み込みました: {model_path}")
        else:
            logger.warning("学習済みモデルが見つかりません。予測機能が無効になります。")
        
        # 価格データバッファ（銘柄ごとに最新30分のデータを保持）
        self.price_buffers = {}
        self.buffer_size = 30
        
        # テクニカル指標計算用の履歴サイズ
        self.history_size = 100
        
        # Kafkaクライアント
        self.consumer = None
        self.producer = None
        
    def connect_kafka(self):
        """Kafka接続を確立"""
        try:
            # コンシューマー作成
            self.consumer = KafkaConsumer(
                self.input_topic,
                bootstrap_servers=self.kafka_config['bootstrap_servers'],
                value_deserializer=self.kafka_config['value_deserializer'],
                group_id='signal_producer',
                enable_auto_commit=True,
                auto_offset_reset='latest'
            )
            
            # プロデューサー作成
            self.producer = KafkaProducer(
                bootstrap_servers=self.kafka_config['bootstrap_servers'],
                value_serializer=self.kafka_config['value_serializer']
            )
            
            logger.info("Kafka接続が完了しました")
            
        except KafkaError as e:
            logger.error(f"Kafka接続エラー: {e}")
            raise
    
    def disconnect_kafka(self):
        """Kafka接続を切断"""
        if self.consumer:
            self.consumer.close()
        if self.producer:
            self.producer.close()
        logger.info("Kafka接続を切断しました")
    
    def add_price_data(self, symbol: str, price_data: Dict):
        """
        価格データをバッファに追加
        
        Args:
            symbol: 銘柄コード
            price_data: 価格データ辞書
        """
        if symbol not in self.price_buffers:
            self.price_buffers[symbol] = deque(maxlen=self.history_size)
        
        # データフォーマットを統一
        formatted_data = {
            'datetime': price_data.get('datetime', datetime.now().isoformat()),
            'open': float(price_data.get('open', 0)),
            'high': float(price_data.get('high', 0)),
            'low': float(price_data.get('low', 0)),
            'close': float(price_data.get('close', 0)),
            'volume': int(price_data.get('volume', 0))
        }
        
        self.price_buffers[symbol].append(formatted_data)
    
    def get_price_dataframe(self, symbol: str, length: int = None) -> pd.DataFrame:
        """
        指定された銘柄の価格データをDataFrameとして取得
        
        Args:
            symbol: 銘柄コード
            length: 取得する行数（Noneの場合は全て）
        
        Returns:
            価格データのDataFrame
        """
        if symbol not in self.price_buffers:
            return pd.DataFrame()
        
        data = list(self.price_buffers[symbol])
        if length:
            data = data[-length:]
        
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        
        return df
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        テクニカル指標を計算
        
        Args:
            df: 価格データフレーム
        
        Returns:
            テクニカル指標辞書
        """
        if len(df) < 20:
            return {}
        
        try:
            # SMA5とSMA10
            sma5 = ta.sma(df['close'], length=5)
            sma10 = ta.sma(df['close'], length=10)
            
            # RSI14
            rsi14 = ta.rsi(df['close'], length=14)
            
            # 最新値を取得
            latest_close = df['close'].iloc[-1]
            latest_sma5 = sma5.iloc[-1] if not sma5.empty else latest_close
            latest_sma10 = sma10.iloc[-1] if not sma10.empty else latest_close
            latest_rsi14 = rsi14.iloc[-1] if not rsi14.empty else 50.0
            
            return {
                'sma5': float(latest_sma5),
                'sma10': float(latest_sma10),
                'rsi14': float(latest_rsi14),
                'price': float(latest_close)
            }
            
        except Exception as e:
            logger.error(f"テクニカル指標計算エラー: {e}")
            return {}
    
    def predict_price_movement(self, symbol: str) -> Optional[float]:
        """
        LSTM予測を実行
        
        Args:
            symbol: 銘柄コード
        
        Returns:
            予測されるΔP（None if 予測不可）
        """
        if not self.lstm_model.is_fitted:
            return None
        
        try:
            # 最新30分のデータを取得
            df = self.get_price_dataframe(symbol, length=self.buffer_size)
            
            if len(df) < self.buffer_size:
                return None
            
            # LSTM予測
            prediction = self.lstm_model.predict_next(df)
            return float(prediction)
            
        except Exception as e:
            logger.error(f"LSTM予測エラー: {e}")
            return None
    
    def generate_signal(self, symbol: str, price_data: Dict) -> Optional[Dict]:
        """
        取引シグナルを生成
        
        Args:
            symbol: 銘柄コード
            price_data: 価格データ
        
        Returns:
            シグナル辞書（None if シグナルなし）
        """
        try:
            # 価格データを追加
            self.add_price_data(symbol, price_data)
            
            # データフレームを取得
            df = self.get_price_dataframe(symbol)
            
            if len(df) < 20:
                return None
            
            # テクニカル指標を計算
            tech_indicators = self.calculate_technical_indicators(df)
            
            if not tech_indicators:
                return None
            
            # LSTM予測
            prediction = self.predict_price_movement(symbol)
            
            # シグナル生成ロジック
            signal_strength = 0.0
            signal_type = 'HOLD'
            
            # RSIベースのシグナル
            rsi = tech_indicators.get('rsi14', 50.0)
            if rsi < 30:
                signal_strength += 0.3  # 買いシグナル
            elif rsi > 70:
                signal_strength -= 0.3  # 売りシグナル
            
            # SMAクロスオーバーシグナル
            sma5 = tech_indicators.get('sma5', 0)
            sma10 = tech_indicators.get('sma10', 0)
            if sma5 > sma10 * 1.001:  # 0.1%以上の差
                signal_strength += 0.2
            elif sma5 < sma10 * 0.999:
                signal_strength -= 0.2
            
            # LSTM予測を確率に変換（シグモイド関数）
            if prediction is not None:
                prob = 1 / (1 + np.exp(-prediction))  # σ(ΔP)
                
                # 確率が0.5以上なら買い、0.5以下なら売り
                if prob > 0.55:
                    signal_strength += 0.5
                elif prob < 0.45:
                    signal_strength -= 0.5
            
            # 最終シグナル決定
            if signal_strength > 0.3:
                signal_type = 'BUY'
            elif signal_strength < -0.3:
                signal_type = 'SELL'
            
            # シグナル辞書を作成
            signal = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'signal_type': signal_type,
                'signal_strength': float(signal_strength),
                'price': tech_indicators.get('price', 0),
                'technical_indicators': tech_indicators,
                'lstm_prediction': prediction,
                'lstm_probability': float(1 / (1 + np.exp(-prediction))) if prediction is not None else None
            }
            
            return signal
            
        except Exception as e:
            logger.error(f"シグナル生成エラー: {e}")
            return None
    
    def send_signal(self, signal: Dict):
        """
        シグナルをKafkaに送信
        
        Args:
            signal: 送信するシグナル辞書
        """
        try:
            future = self.producer.send(self.output_topic, value=signal)
            future.get(timeout=10)  # 送信完了を待機
            
            logger.info(f"シグナル送信: {signal['symbol']} - {signal['signal_type']} "
                       f"(強度: {signal['signal_strength']:.3f})")
            
        except Exception as e:
            logger.error(f"シグナル送信エラー: {e}")
    
    def run(self):
        """メインループ実行"""
        logger.info("シグナル生成を開始します...")
        
        try:
            self.connect_kafka()
            
            for message in self.consumer:
                try:
                    # メッセージを解析
                    price_data = message.value
                    symbol = price_data.get('symbol')
                    
                    if not symbol:
                        continue
                    
                    # シグナルを生成
                    signal = self.generate_signal(symbol, price_data)
                    
                    if signal and signal['signal_type'] != 'HOLD':
                        self.send_signal(signal)
                    
                except Exception as e:
                    logger.error(f"メッセージ処理エラー: {e}")
                    continue
                    
        except KeyboardInterrupt:
            logger.info("シグナル生成を停止します...")
        finally:
            self.disconnect_kafka()


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='リアルタイムシグナル生成スクリプト')
    parser.add_argument('--model-path', help='学習済みモデルのパス')
    parser.add_argument('--log-level', default='INFO', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='ログレベル')
    
    args = parser.parse_args()
    
    # ログレベル設定
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    try:
        # シグナル生成器を作成・実行
        signal_producer = SignalProducer(model_path=args.model_path)
        signal_producer.run()
        
    except Exception as e:
        logger.error(f"アプリケーションエラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()