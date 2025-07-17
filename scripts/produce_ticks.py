import os
import json
import argparse
from confluent_kafka import Producer
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.data.jquants_client import JQuantsClient


def main():
    """ティックデータをKafkaトピックに送信する"""
    parser = argparse.ArgumentParser(description='ティックデータをKafkaに送信')
    parser.add_argument('--symbol', required=True, help='株式銘柄コード')
    parser.add_argument('--date', required=True, help='日付 (YYYY-MM-DD形式)')
    args = parser.parse_args()

    # JQuantsクライアントを初期化
    client = JQuantsClient()
    
    # ティックデータを取得
    tick_data = client.get_tick(args.symbol, args.date)
    
    # Kafkaプロデューサーを初期化
    producer = Producer({'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')})
    
    # 送信カウンター
    sent_count = 0
    
    # 各ティックデータをKafkaに送信
    for tick in tick_data:
        # JSONフォーマットでメッセージを構築
        message = {
            "symbol": args.symbol,
            "time": tick.get('time', ''),
            "price": tick.get('price', 0),
            "volume": tick.get('volume', 0)
        }
        
        # Kafkaトピック "ticks.raw" に送信
        producer.produce(
            topic='ticks.raw',
            value=json.dumps(message)
        )
        sent_count += 1
    
    # 全てのメッセージが送信されるまで待機
    producer.flush()
    
    print(f"sent {sent_count} messages")


if __name__ == "__main__":
    main()