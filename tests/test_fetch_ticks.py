#!/usr/bin/env python3
"""
Test fetch_ticks.py script with mocked API and database
"""
import unittest
from unittest.mock import Mock, patch
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.fetch_ticks import main


class TestFetchTicks(unittest.TestCase):
    
    @patch('scripts.fetch_ticks.psycopg2.connect')
    @patch('scripts.fetch_ticks.JQuantsClient')
    @patch('sys.argv', ['fetch_ticks.py', '--symbol', '7203', '--date', '2023-01-01'])
    def test_fetch_ticks_success(self, mock_client_class, mock_connect):
        # Mock J-Quants client
        mock_client = Mock()
        mock_client.get_tick.return_value = [
            {"time": "09:00:01", "price": 2001, "volume": 100},
            {"time": "09:00:02", "price": 2002, "volume": 200},
        ]
        mock_client_class.return_value = mock_client
        
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Mock print to capture output
        with patch('builtins.print') as mock_print:
            main()
        
        # Assertions
        mock_client.get_tick.assert_called_once_with('7203', '2023-01-01')
        mock_cursor.execute.assert_called()
        mock_cursor.copy_from.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()
        mock_print.assert_called_with("inserted 2 rows")
    
    @patch('scripts.fetch_ticks.psycopg2.connect')
    @patch('scripts.fetch_ticks.JQuantsClient')
    @patch('sys.argv', ['fetch_ticks.py', '--symbol', '7203', '--date', '2023-01-01'])
    def test_fetch_ticks_no_data(self, mock_client_class, mock_connect):
        # Mock J-Quants client with no data
        mock_client = Mock()
        mock_client.get_tick.return_value = []
        mock_client_class.return_value = mock_client
        
        # Mock print to capture output
        with patch('builtins.print') as mock_print:
            main()
        
        # Assertions
        mock_client.get_tick.assert_called_once_with('7203', '2023-01-01')
        mock_connect.assert_not_called()  # Should not connect to DB if no data
        mock_print.assert_called_with("No tick data found")
    
    @patch('scripts.fetch_ticks.psycopg2.connect')
    @patch('scripts.fetch_ticks.JQuantsClient')
    @patch('sys.argv', ['fetch_ticks.py', '--symbol', '7203', '--date', '2023-01-01'])
    def test_copy_from_called_with_correct_data(self, mock_client_class, mock_connect):
        # Mock J-Quants client
        mock_client = Mock()
        mock_client.get_tick.return_value = [
            {"time": "09:00:01", "price": 2001, "volume": 100},
        ]
        mock_client_class.return_value = mock_client
        
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        main()
        
        # Verify copy_from was called with correct parameters
        mock_cursor.copy_from.assert_called_once()
        call_args = mock_cursor.copy_from.call_args
        
        # Check that copy_from was called with expected arguments
        self.assertEqual(call_args[1]['sep'], '\t')
        self.assertEqual(call_args[1]['columns'], ('symbol', 'date', 'time', 'price', 'volume'))
        self.assertEqual(call_args[0][1], 'ticks')  # table name


if __name__ == '__main__':
    unittest.main()
