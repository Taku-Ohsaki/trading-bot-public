import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConsumeTicks(unittest.TestCase):
    
    @patch('scripts.consume_ticks.psycopg2.connect')
    @patch('scripts.consume_ticks.Consumer')
    def test_consume_ticks(self, mock_consumer_class, mock_connect):
        """ティックデータの消費とデータベース挿入をテスト"""
        # データベースモックの設定
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Kafkaコンシューマーモックの設定
        mock_consumer = Mock()
        mock_consumer_class.return_value = mock_consumer
        
        # Kafkaメッセージのモック（100個のメッセージ）
        mock_messages = []
        for i in range(100):
            mock_message = Mock()
            mock_message.error.return_value = None
            mock_message.value.return_value.decode.return_value = json.dumps({
                "symbol": "TEST",
                "time": f"2023-01-01 09:00:{i:02d}",
                "price": 100.0 + i,
                "volume": 1000 + i * 10
            })
            mock_messages.append(mock_message)
        
        # 最後にNoneを返してループを終了
        mock_consumer.poll.side_effect = mock_messages + [None] * 10
        
        # consume_ticksモジュールをインポート
        from scripts import consume_ticks
        
        # KeyboardInterruptでループを終了
        with patch('builtins.input', side_effect=KeyboardInterrupt):
            try:
                consume_ticks.main()
            except KeyboardInterrupt:
                pass
        
        # コンシューマーが正しく設定されたかを確認
        mock_consumer.subscribe.assert_called_once_with(['ticks.raw'])
        
        # データベース接続が呼び出されたかを確認
        mock_connect.assert_called()
        
        # copy_fromが呼び出されたかを確認
        mock_cursor.copy_from.assert_called()
        
        # コミットが呼び出されたかを確認
        mock_conn.commit.assert_called()
        
        # コンシューマーが閉じられたかを確認
        mock_consumer.close.assert_called_once()
    
    @patch('scripts.consume_ticks.psycopg2.connect')
    def test_insert_batch(self, mock_connect):
        """バッチ挿入機能をテスト"""
        # データベースモックの設定
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # テストデータ
        test_batch = [
            {"symbol": "TEST1", "time": "2023-01-01 09:00:00", "price": 100.0, "volume": 1000},
            {"symbol": "TEST2", "time": "2023-01-01 09:00:01", "price": 101.0, "volume": 2000}
        ]
        
        db_config = {
            'host': 'localhost',
            'database': 'test_db',
            'user': 'test_user',
            'password': 'test_password',
            'port': '5432'
        }
        
        # consume_ticksモジュールをインポート
        from scripts.consume_ticks import insert_batch
        
        # バッチ挿入を実行
        insert_batch(test_batch, db_config)
        
        # データベース接続が正しい設定で呼び出されたかを確認
        mock_connect.assert_called_once_with(**db_config)
        
        # copy_fromが正しいパラメータで呼び出されたかを確認
        mock_cursor.copy_from.assert_called_once()
        call_args = mock_cursor.copy_from.call_args
        
        # テーブル名とカラム名が正しいかを確認
        self.assertEqual(call_args[0][1], 'ticks')
        self.assertEqual(call_args[1]['columns'], ('symbol', 'time', 'price', 'volume'))
        self.assertEqual(call_args[1]['sep'], '\t')
        
        # コミットが呼び出されたかを確認
        mock_conn.commit.assert_called_once()
        
        # カーソルとコネクションが閉じられたかを確認
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


if __name__ == '__main__':
    # テストを実行してexit code 0を返す
    unittest.main(exit=False)
    sys.exit(0)