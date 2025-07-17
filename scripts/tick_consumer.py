import json
import psycopg2
from confluent_kafka import Consumer, KafkaError
import io
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    # Database connection
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'database': os.getenv('DB_NAME', 'trading_db'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'password'),
        'port': os.getenv('DB_PORT', '5432')
    }
    
    # Kafka consumer configuration
    consumer_config = {
        'bootstrap.servers': 'localhost:9092',
        'group.id': 'tick_consumer_group',
        'auto.offset.reset': 'earliest'
    }
    
    consumer = Consumer(consumer_config)
    consumer.subscribe(['trading_ticks'])
    
    try:
        while True:
            # Batch consume up to 10,000 messages or 3 seconds timeout
            messages = consumer.consume(num_messages=10000, timeout=3.0)
            
            if not messages:
                continue
                
            # Process messages
            rows = []
            for message in messages:
                if message.error():
                    if message.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        print(f"Error: {message.error()}")
                        continue
                
                try:
                    tick_data = json.loads(message.value().decode('utf-8'))
                    symbol = message.key().decode('utf-8')
                    
                    # Format row for COPY
                    row = f"{symbol}\t{tick_data['ts']}\t{tick_data['price']}\t{tick_data['vol']}\n"
                    rows.append(row)
                    
                except Exception as e:
                    print(f"Error processing message: {e}")
                    continue
            
            if rows:
                # Bulk insert using COPY
                conn = psycopg2.connect(**db_config)
                try:
                    cursor = conn.cursor()
                    
                    # Create StringIO object for COPY
                    data_io = io.StringIO()
                    data_io.writelines(rows)
                    data_io.seek(0)
                    
                    # Use COPY with ON CONFLICT DO NOTHING for safe re-runs
                    cursor.copy_expert(
                        "COPY ticks (symbol, ts, price, vol) FROM STDIN WITH (FORMAT TEXT, DELIMITER E'\\t') ON CONFLICT DO NOTHING",
                        data_io
                    )
                    
                    conn.commit()
                    print(f"wrote {len(rows)} rows")
                    
                except Exception as e:
                    conn.rollback()
                    print(f"Database error: {e}")
                finally:
                    cursor.close()
                    conn.close()
                    
    except KeyboardInterrupt:
        print("Shutting down consumer...")
    finally:
        consumer.close()


if __name__ == "__main__":
    main()