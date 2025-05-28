import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import json
import create_litmos_user  # Your script filename (without the .py extension)

class TestCreateLitmosUser(unittest.TestCase):

    @patch('create_litmos_user.mysql.connector.connect')
    @patch('create_litmos_user.litmos.User.create')
    @patch('create_litmos_user.litmos.User.search')
    @patch('create_litmos_user.os.getenv')
    @patch('create_litmos_user.sys.argv', new=['script_name', '1'])  # Mock command-line args
    def test_create_litmos_user_success(self, mock_getenv, mock_search, mock_create, mock_connect):
        # Mock environment variables
        mock_getenv.side_effect = lambda key: {
            'LITMOS_API_KEY': 'fake_api_key',
            'LITMOS_APP_NAME': 'fake_app_name',
            'LITMOS_URL': 'fake_url',
            'DATABASE_NAME': 'test_db',
            'DATABASE_USER_NAME': 'test_user',
            'DATABASE_USER_PASSWORD': 'test_password'
        }.get(key)

        # Mock MySQL connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock database response
        mock_cursor.fetchone.return_value = (1, 'John', 'Doe', 'john@example.com', 'Chapter A', 'Region 1')
        mock_cursor.description = [
            ('id',), ('first_name',), ('last_name',), ('email',), ('chapter',), ('chapter_region',)
        ]

        # Mock Litmos API response
        mock_create.return_value = MagicMock()
        mock_search.return_value = MagicMock()

        # Run the function
        user = create_litmos_user.getUserFromDatabase(1)
        self.assertEqual(user['email'], 'john@example.com')

        create_litmos_user.create_litmos_user(user)

        # Check that Litmos user creation and search were called
        mock_create.assert_called_once()
        mock_search.assert_called_once_with('john@example.com')

        # Check final output
        with patch('create_litmos_user.finalOutput') as mock_final_output:
            mock_final_output.assert_called_once_with('success')

    @patch('create_litmos_user.mysql.connector.connect')
    @patch('create_litmos_user.litmos.User.search')
    @patch('create_litmos_user.os.getenv')
    @patch('create_litmos_user.sys.argv', new=['script_name', '999'])  # Mock invalid user ID
    def test_getUserFromDatabase_not_found(self, mock_getenv, mock_search, mock_connect):
        # Mock environment variables
        mock_getenv.side_effect = lambda key: {
            'LITMOS_API_KEY': 'fake_api_key',
            'LITMOS_APP_NAME': 'fake_app_name',
            'LITMOS_URL': 'fake_url',
            'DATABASE_NAME': 'test_db',
            'DATABASE_USER_NAME': 'test_user',
            'DATABASE_USER_PASSWORD': 'test_password'
        }.get(key)

        # Mock MySQL connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock database response (no user found)
        mock_cursor.fetchone.return_value = None

        user = create_litmos_user.getUserFromDatabase(999)
        self.assertIsNone(user)

        # Check final output for not found
        with patch('create_litmos_user.finalOutput') as mock_final_output:
            mock_final_output.assert_called_once_with("Error", "database does not have a user with that id")

if __name__ == '__main__':
    unittest.main()
