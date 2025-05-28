# test_forward_email.py
import unittest
from unittest.mock import patch, MagicMock
import forward_email


class TestForwardEmail(unittest.TestCase):

    @patch('forward_email.run_GAM_Command')
    def test_is_real_email_valid(self, mock_run_gam):
        mock_run_gam.return_value = "User: test@shpbeds.org\nPrimary Email: test@shpbeds.org"
        env = {'SERVER_ENVIRONMENT': 'production'}
        result = forward_email.is_real_email('test@shpbeds.org', env)
        self.assertTrue(result)

    @patch('forward_email.run_GAM_Command')
    def test_is_real_email_invalid(self, mock_run_gam):
        mock_run_gam.return_value = "Error: User not found"
        env = {'SERVER_ENVIRONMENT': 'production'}
        result = forward_email.is_real_email('fake@shpbeds.org', env)
        self.assertFalse(result)

    def test_is_shpbeds_email_valid(self):
        result = forward_email.is_shpbeds_email('user@shpbeds.org')
        self.assertTrue(result)

    def test_is_shpbeds_email_invalid(self):
        result = forward_email.is_shpbeds_email('user@gmail.com')
        self.assertFalse(result)

    def test_extract_emails(self):
        text = "Forwarding Address: user@shpbeds.org"
        emails = forward_email.extract_emails(text)
        self.assertEqual(emails, ['user@shpbeds.org'])

