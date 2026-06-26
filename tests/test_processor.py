import unittest
import sys
import json
import time
from pathlib import Path
import tempfile
from unittest.mock import MagicMock

# Add src directory to Python path
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from models import MailMessage
from processor import MailProcessor

class MockConfig:
    """Mock config mapping directories to temp paths."""
    def __init__(self, temp_dir):
        self.shared_dir = Path(temp_dir)
        self.pending_dir = self.shared_dir / "pending"
        self.processing_dir = self.shared_dir / "processing"
        self.failed_dir = self.shared_dir / "failed"
        
        self.pending_dir.mkdir()
        self.processing_dir.mkdir()
        self.failed_dir.mkdir()
        
        self.mail_max_retries = 3
        self.mail_backoff_base = 2.0

class TestMailProcessor(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config = MockConfig(self.temp_dir.name)
        self.mock_smtp = MagicMock()
        self.processor = MailProcessor(config=self.config, smtp_client=self.mock_smtp)

        self.valid_mail_data = {
            "id": "mail-12345",
            "to": "test@example.com",
            "subject": "Hello",
            "body": "World",
            "content_type": "text/plain"
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_processing_success(self):
        # Create a file in processing
        file_path = self.config.processing_dir / "mail-12345.msg.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.valid_mail_data, f)

        self.processor.process_file(file_path)

        # SMTP client should be called
        self.mock_smtp.send.assert_called_once()
        # File should be deleted
        self.assertFalse(file_path.exists())

    def test_processing_validation_failure(self):
        invalid_data = self.valid_mail_data.copy()
        del invalid_data["to"]  # Missing required field

        file_path = self.config.processing_dir / "mail-invalid.msg.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(invalid_data, f)

        self.processor.process_file(file_path)

        # SMTP client should not be called
        self.mock_smtp.send.assert_not_called()
        # Original file should be moved/removed
        self.assertFalse(file_path.exists())
        # File should be in failed_dir
        failed_file = self.config.failed_dir / "mail-invalid.msg.json"
        self.assertTrue(failed_file.exists())

    def test_processing_corrupted_json(self):
        file_path = self.config.processing_dir / "mail-corrupted.msg.json"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("{invalid-json}")

        self.processor.process_file(file_path)

        self.mock_smtp.send.assert_not_called()
        self.assertFalse(file_path.exists())
        failed_file = self.config.failed_dir / "mail-corrupted.msg.json"
        self.assertTrue(failed_file.exists())

    def test_processing_retry_schedule_skips(self):
        # Set next_retry_at to future
        retry_data = self.valid_mail_data.copy()
        retry_data["attempts"] = 1
        retry_data["next_retry_at"] = time.time() + 100

        file_path = self.config.processing_dir / "mail-retry.msg.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(retry_data, f)

        self.processor.process_file(file_path)

        # SMTP should not be called since scheduled in future
        self.mock_smtp.send.assert_not_called()
        self.assertTrue(file_path.exists())

    def test_processing_retry_backoff_handling(self):
        # SMTP fails
        self.mock_smtp.send.side_effect = Exception("SMTP server down")

        file_path = self.config.processing_dir / "mail-fail.msg.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.valid_mail_data, f)

        # 1st attempt
        self.processor.process_file(file_path)

        # SMTP called once
        self.mock_smtp.send.assert_called_once()
        # File still exists
        self.assertTrue(file_path.exists())
        # Check attempts and next_retry_at in file
        with open(file_path, "r", encoding="utf-8") as f:
            updated = json.load(f)
            self.assertEqual(updated["attempts"], 1)
            self.assertIsNotNone(updated["next_retry_at"])
            # Delay for attempt 1 is base ** 0 = 1.0s
            self.assertAlmostEqual(updated["next_retry_at"], time.time() + 1.0, delta=0.5)

    def test_processing_max_retries_exceeded(self):
        # SMTP fails
        self.mock_smtp.send.side_effect = Exception("SMTP server down")

        # Set attempts to 2 (max_retries = 3, so next call is 3rd attempt, which will trigger failure)
        retry_data = self.valid_mail_data.copy()
        retry_data["attempts"] = 2

        file_path = self.config.processing_dir / "mail-max.msg.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(retry_data, f)

        self.processor.process_file(file_path)

        # File should be removed from processing and moved to failed
        self.assertFalse(file_path.exists())
        failed_file = self.config.failed_dir / "mail-12345.json"
        self.assertTrue(failed_file.exists())

if __name__ == "__main__":
    unittest.main()
