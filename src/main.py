import sys
import time
import signal
import logging
from pathlib import Path

# Add the 'src' directory to the Python path to support all execution formats
src_dir = Path(__file__).resolve().parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from config import Config
from smtp_client import SMTPClient
from processor import MailProcessor
from watcher import MailWatcher

def main():
    # 1. Load configuration
    try:
        config = Config()
    except Exception as e:
        logging.basicConfig(level=logging.ERROR)
        logging.critical(f"Failed to load service configuration: {e}")
        sys.exit(1)

    # 2. Configure system-wide logging outputs to stdout for container log capture
    logging.basicConfig(
        level=config.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    logger = logging.getLogger("mail-watchdog")
    logger.info("Initializing mail-watchdog service...")
    logger.info(f"Loaded Configuration: {config}")

    # 3. Initialize components
    smtp_client = SMTPClient(
        host=config.smtp_host,
        port=config.smtp_port,
        user=config.smtp_user,
        password=config.smtp_password,
        from_addr=config.smtp_from
    )

    processor = MailProcessor(config=config, smtp_client=smtp_client)
    watcher = MailWatcher(config=config, processor=processor)

    # 4. Graceful Shutdown Signal Handlers
    running = True

    def signal_handler(signum, frame):
        nonlocal running
        sig_name = signal.Signals(signum).name
        logger.info(f"Received signal {sig_name} ({signum}). Initiating graceful shutdown...")
        running = False

    # Register standard shutdown signals
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Service is up and running. Starting filesystem polling...")

    # 5. Continuous Polling Loop
    try:
        while running:
            watcher.scan_and_process()
            # Sleep in sub-intervals to remain responsive to termination signals
            remaining_sleep = config.mail_poll_interval
            while remaining_sleep > 0 and running:
                sleep_chunk = min(0.2, remaining_sleep)
                time.sleep(sleep_chunk)
                remaining_sleep -= sleep_chunk
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt detected. Initiating graceful shutdown...")
    finally:
        logger.info("Service shutdown procedure completed successfully. Exiting.")

if __name__ == "__main__":
    main()
