import unittest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src directory to Python path
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from models import MailMessage
from smtp_client import SMTPClient

class TestSMTPClient(unittest.TestCase):
    def setUp(self):
        self.message = MailMessage(
            id="mail-test-1",
            to="receiver@example.com",
            subject="Test Subject",
            body="Test Body",
            content_type="text/plain"
        )

    @patch("smtplib.SMTP")
    def test_send_plain_smtp(self, mock_smtp_class):
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server
        mock_server.has_extn.return_value = False

        client = SMTPClient(
            host="smtp.example.com",
            port=25,
            user=None,
            password=None,
            from_addr="sender@example.com"
        )
        
        client.send(self.message)
        
        mock_smtp_class.assert_called_once_with("smtp.example.com", 25, timeout=10)
        mock_server.sendmail.assert_called_once()
        mock_server.quit.assert_called_once()
        mock_server.starttls.assert_not_called()

    @patch("smtplib.SMTP")
    def test_send_smtp_starttls_and_login(self, mock_smtp_class):
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server
        # Return True for STARTTLS support
        mock_server.has_extn.side_effect = lambda ext: ext.lower() == "starttls"

        client = SMTPClient(
            host="smtp.example.com",
            port=587,
            user="user@example.com",
            password="secretpassword",
            from_addr="sender@example.com"
        )
        
        client.send(self.message)
        
        mock_smtp_class.assert_called_once_with("smtp.example.com", 587, timeout=10)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user@example.com", "secretpassword")
        mock_server.sendmail.assert_called_once()
        mock_server.quit.assert_called_once()

    @patch("smtplib.SMTP_SSL")
    def test_send_smtp_ssl(self, mock_smtp_ssl_class):
        mock_server = MagicMock()
        mock_smtp_ssl_class.return_value = mock_server

        client = SMTPClient(
            host="smtp.example.com",
            port=465,
            user="user@example.com",
            password="secretpassword",
            from_addr="sender@example.com"
        )
        
        client.send(self.message)
        
        mock_smtp_ssl_class.assert_called_once_with("smtp.example.com", 465, timeout=10)
        mock_server.login.assert_called_once_with("user@example.com", "secretpassword")
        mock_server.sendmail.assert_called_once()
        mock_server.quit.assert_called_once()

if __name__ == "__main__":
    unittest.main()
