import os
import json
import psycopg2
from confluent_kafka import Consumer, KafkaError
import io


def main():
    """Kafkaからティックデータを消費してPostgreSQLに保存"""
    # PostgreSQL接続設定（環境変数から取得）
    db_config = {
        'host': os.getenv('PGHOST', 'localhost'),
        'database': os.getenv('PGDATABASE', 'trading_db'),
        'user': os.getenv('PGUSER', 'postgres'),
        'password': os.getenv('PGPASSWORD', 'password'),
        'port': os.getenv('PGPORT', '5432')
    }
    
    # Kafkaコンシューマー設定
    consumer_config = {
        'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
        'group.id': 'ticks_consumer_group',
        'auto.offset.reset': 'earliest'
    }
    
    consumer = Consumer(consumer_config)
    consumer.subscribe(['ticks.raw'])
    
    try:
        batch = []
        
        while True:
            # メッセージを取得
            message = consumer.poll(timeout=1.0)
            
            if message is None:
                continue
                
            if message.error():
                if message.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    print(f"エラー: {message.error()}")
                    continue
            
            try:
                # JSONメッセージをパース
                tick_data = json.loads(message.value().decode('utf-8'))
                batch.append(tick_data)
                
                # バッチサイズが100に達したらデータベースに保存
                if len(batch) >= 100:
                    insert_batch(batch, db_config)
                    batch = []
                    
            except Exception as e:
                print(f"メッセージ処理エラー: {e}")
                continue
                
    except KeyboardInterrupt:
        print("コンシューマーを停止しています...")
        # 残りのバッチを処理
        if batch:
            insert_batch(batch, db_config)
    finally:
        consumer.close()


def insert_batch(batch, db_config):
    """バッチデータをPostgreSQLに挿入"""
    conn = psycopg2.connect(**db_config)
    try:
        cursor = conn.cursor()
        
        # COPYのためのデータ準備
        data_io = io.StringIO()
        for tick in batch:
            row = f"{tick['symbol']}\t{tick['time']}\t{tick['price']}\t{tick['volume']}\n"
            data_io.write(row)
        data_io.seek(0)
        
        # COPYを使用してバルクインサート
        cursor.copy_from(
            data_io,
            'ticks',
            columns=('symbol', 'time', 'price', 'volume'),
            sep='\t'
        )
        
        conn.commit()
        print(f"inserted {len(batch)} rows")
        
    except Exception as e:
        conn.rollback()
        print(f"データベースエラー: {e}")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()