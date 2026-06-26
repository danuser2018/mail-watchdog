import time
import logging
from pathlib import Path
from pydantic import ValidationError
from models import MailMessage
from smtp_client import SMTPClient
from retry import get_backoff_delay
from utils import load_json, save_json, move_file_atomically

logger = logging.getLogger(__name__)

class MailProcessor:
    """
    MailProcessor orchestrates the processing lifecycle of a single mail message.
    It reads, validates, updates attempts, invokes SMTP, and manages file placement
    (deletion on success, moving to failed directory on absolute failure).
    """
    def __init__(self, config, smtp_client: SMTPClient):
        self.config = config
        self.smtp_client = smtp_client

    def process_file(self, filepath: Path):
        """
        Processes an individual mail JSON file.
        """
        logger.info(f"Processing mail {filepath.stem}")
        
        # 1. Read and parse JSON content
        try:
            data = load_json(filepath)
        except Exception as e:
            logger.error(f"Failed to read/parse JSON from file '{filepath.name}': {e}")
            self._move_to_failed(filepath, suffix_id=None)
            return

        # 2. Validate fields using Pydantic model
        try:
            message = MailMessage(**data)
        except ValidationError as val_err:
            logger.error(f"JSON validation failed for file '{filepath.name}': {val_err}")
            self._move_to_failed(filepath, suffix_id=None)
            return

        # 3. Check retry schedule
        now = time.time()
        if message.next_retry_at is not None and now < message.next_retry_at:
            logger.debug(f"Skipping {message.id} - scheduled for retry in {message.next_retry_at - now:.1f}s")
            return

        # 4. Increment attempt counter and serialize state to prevent loss on crash
        message.attempts += 1
        try:
            save_json(message.model_dump(), filepath)
        except Exception as save_err:
            logger.error(f"Failed to save attempt progress for email ID {message.id}: {save_err}")
            # Continue dispatching regardless of state save failure

        # 5. Attempt SMTP dispatch
        try:
            logger.info(f"Sending to {message.to}")
            self.smtp_client.send(message)
            
            # Dispatch success: remove file from processing directory
            try:
                filepath.unlink()
                logger.info(f"Successfully processed and deleted file: {filepath.name}")
            except Exception as unlink_err:
                logger.error(f"Failed to delete processed file {filepath.name}: {unlink_err}")

        except Exception as smtp_err:
            logger.warning(f"SMTP retry {message.attempts}/{self.config.mail_max_retries} failed for ID {message.id}: {smtp_err}")
            
            # 6. Check if max retry limit is exceeded
            if message.attempts >= self.config.mail_max_retries:
                logger.error(f"Mail failed after retries")
                self._move_to_failed(filepath, suffix_id=message.id)
            else:
                # 7. Schedule next attempt with exponential backoff
                delay = get_backoff_delay(message.attempts, self.config.mail_backoff_base)
                message.next_retry_at = time.time() + delay
                try:
                    save_json(message.model_dump(), filepath)
                    logger.debug(f"Scheduled retry for email ID {message.id} in {delay}s")
                except Exception as save_err:
                    logger.error(f"Failed to save retry timestamp for email ID {message.id}: {save_err}")

    def _move_to_failed(self, filepath: Path, suffix_id: str = None):
        """Moves the target file to the failed/ directory."""
        dest_filename = f"{suffix_id}.json" if suffix_id else filepath.name
        dest_path = self.config.failed_dir / dest_filename
        try:
            move_file_atomically(filepath, dest_path)
            logger.info(f"Moved to {dest_path}")
        except Exception as e:
            logger.critical(f"Failed to move file '{filepath.name}' to failed directory: {e}")
