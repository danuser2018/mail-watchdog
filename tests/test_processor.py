import unittest
import sys
import json
import time
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch

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
        self.identity_service_base_url = "http://identity-service:8000"

class TestMailProcessor(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config = MockConfig(self.temp_dir.name)
        self.mock_smtp = MagicMock()
        self.processor = MailProcessor(config=self.config, smtp_client=self.mock_smtp)

        self.valid_mail_data = {
            "id": "mail-12345",
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

        with patch.object(self.processor, "_resolve_recipient", return_value="testuser@example.com"):
            self.processor.process_file(file_path)

        # SMTP client should be called with resolved recipient
        self.mock_smtp.send.assert_called_once()
        call_args = self.mock_smtp.send.call_args
        self.assertEqual(call_args[0][1], "testuser@example.com")
        # File should be deleted
        self.assertFalse(file_path.exists())

    def test_processing_validation_failure(self):
        # id is required, subject must have min_length=1
        invalid_data = {"id": "", "subject": "Hello", "body": "World"}

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

        with patch.object(self.processor, "_resolve_recipient", return_value="testuser@example.com"):
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

        with patch.object(self.processor, "_resolve_recipient", return_value="testuser@example.com"):
            self.processor.process_file(file_path)

        # File should be removed from processing and moved to failed
        self.assertFalse(file_path.exists())
        failed_file = self.config.failed_dir / "mail-12345.json"
        self.assertTrue(failed_file.exists())

    def test_identity_service_failure_triggers_retry(self):
        """When identity-service is unreachable, the file must remain and schedule a retry."""
        file_path = self.config.processing_dir / "mail-idretry.msg.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.valid_mail_data, f)

        with patch.object(
            self.processor, "_resolve_recipient",
            side_effect=RuntimeError("Network error contacting identity-service")
        ):
            self.processor.process_file(file_path)

        # SMTP must not be called
        self.mock_smtp.send.assert_not_called()
        # File should still exist with retry scheduled
        self.assertTrue(file_path.exists())
        with open(file_path, "r", encoding="utf-8") as f:
            updated = json.load(f)
            self.assertEqual(updated["attempts"], 1)
            self.assertIsNotNone(updated["next_retry_at"])

    def test_identity_service_failure_max_retries_exceeded(self):
        """When identity-service keeps failing and max retries are exceeded, move to failed/."""
        retry_data = self.valid_mail_data.copy()
        retry_data["attempts"] = 2  # next attempt will be 3rd → exceeds max_retries=3

        file_path = self.config.processing_dir / "mail-idmax.msg.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(retry_data, f)

        with patch.object(
            self.processor, "_resolve_recipient",
            side_effect=RuntimeError("Network error contacting identity-service")
        ):
            self.processor.process_file(file_path)

        # SMTP must not be called
        self.mock_smtp.send.assert_not_called()
        self.assertFalse(file_path.exists())
        failed_file = self.config.failed_dir / "mail-12345.json"
        self.assertTrue(failed_file.exists())

    def test_identity_service_empty_email_triggers_retry(self):
        """When identity-service returns an empty email, treat as temporary failure."""
        file_path = self.config.processing_dir / "mail-emptyemail.msg.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.valid_mail_data, f)

        with patch.object(
            self.processor, "_resolve_recipient",
            side_effect=RuntimeError("identity-service returned an empty or missing email field")
        ):
            self.processor.process_file(file_path)

        self.mock_smtp.send.assert_not_called()
        self.assertTrue(file_path.exists())

    def test_processing_ignores_extra_to_field_in_json(self):
        """A JSON file that still contains a legacy 'to' field must be processed normally (field ignored by Pydantic)."""
        data_with_to = self.valid_mail_data.copy()
        data_with_to["to"] = "legacy@example.com"

        file_path = self.config.processing_dir / "mail-legacy.msg.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data_with_to, f)

        with patch.object(self.processor, "_resolve_recipient", return_value="resolved@example.com"):
            self.processor.process_file(file_path)

        # SMTP must be called with the dynamically resolved recipient, not the legacy one
        self.mock_smtp.send.assert_called_once()
        call_args = self.mock_smtp.send.call_args
        self.assertEqual(call_args[0][1], "resolved@example.com")
        self.assertFalse(file_path.exists())

if __name__ == "__main__":
    unittest.main()
