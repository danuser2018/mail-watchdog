import os
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class Config:
    """
    Configuration class to load, validate, and store application settings
    for the mail-watchdog service from environment variables and local .env files.
    """
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()

        # 1. SMTP Server configuration
        self.smtp_host = os.getenv("SMTP_HOST", "localhost")
        try:
            self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        except ValueError:
            logger.warning("Invalid SMTP_PORT specified. Defaulting to 587.")
            self.smtp_port = 587

        self.smtp_user = os.getenv("SMTP_USER") or None
        self.smtp_password = os.getenv("SMTP_PASSWORD") or None

        # Determine default SMTP_FROM address
        default_from = f"Nova <{self.smtp_user}>" if self.smtp_user else "Nova <nova@localhost>"
        self.smtp_from = os.getenv("SMTP_FROM", default_from)

        # 2. Watchdog Behavior Configuration
        try:
            self.mail_poll_interval = float(os.getenv("MAIL_POLL_INTERVAL", "2.0"))
        except ValueError:
            logger.warning("Invalid MAIL_POLL_INTERVAL. Defaulting to 2.0 seconds.")
            self.mail_poll_interval = 2.0

        try:
            self.mail_max_retries = int(os.getenv("MAIL_MAX_RETRIES", "3"))
        except ValueError:
            logger.warning("Invalid MAIL_MAX_RETRIES. Defaulting to 3.")
            self.mail_max_retries = 3

        try:
            self.mail_backoff_base = float(os.getenv("MAIL_BACKOFF_BASE", "2.0"))
        except ValueError:
            logger.warning("Invalid MAIL_BACKOFF_BASE. Defaulting to 2.0.")
            self.mail_backoff_base = 2.0

        # 3. Log level configuration
        log_level_env = os.getenv("LOG_LEVEL", "INFO").upper()
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        self.log_level = level_map.get(log_level_env, logging.INFO)

        # 4. Shared Directory Configuration
        shared_dir_env = os.getenv("MAIL_SHARED_DIR", "/shared/mail")
        self.shared_dir = Path(shared_dir_env).resolve()

        # Define subdirectories
        self.pending_dir = self.shared_dir / "pending"
        self.processing_dir = self.shared_dir / "processing"
        self.failed_dir = self.shared_dir / "failed"

        # Initialize folders (best-effort, fall back if /shared/mail is not writable)
        self.init_directories()

    def init_directories(self):
        """Attempts to create the pending, processing, and failed directories."""
        try:
            self.pending_dir.mkdir(parents=True, exist_ok=True)
            self.processing_dir.mkdir(parents=True, exist_ok=True)
            self.failed_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Initialized mail watchdog directories under: {self.shared_dir}")
        except Exception as e:
            # Fallback to local workspace shared directory for ease of development / testing
            logger.warning(
                f"Could not create directories at '{self.shared_dir}' ({e}). "
                "Falling back to local workspace './shared/mail'..."
            )
            local_fallback = Path(__file__).resolve().parent.parent / "shared" / "mail"
            self.shared_dir = local_fallback.resolve()
            self.pending_dir = self.shared_dir / "pending"
            self.processing_dir = self.shared_dir / "processing"
            self.failed_dir = self.shared_dir / "failed"
            
            self.pending_dir.mkdir(parents=True, exist_ok=True)
            self.processing_dir.mkdir(parents=True, exist_ok=True)
            self.failed_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Fallback mail watchdog directories initialized under: {self.shared_dir}")

    def __repr__(self):
        # Crucial security rule: DO NOT log credentials (smtp_password)
        return (
            f"Config(smtp_host='{self.smtp_host}', "
            f"smtp_port={self.smtp_port}, "
            f"smtp_user='{self.smtp_user}', "
            f"smtp_from='{self.smtp_from}', "
            f"mail_poll_interval={self.mail_poll_interval}, "
            f"mail_max_retries={self.mail_max_retries}, "
            f"mail_backoff_base={self.mail_backoff_base}, "
            f"log_level={logging.getLevelName(self.log_level)}, "
            f"shared_dir={self.shared_dir})"
        )
