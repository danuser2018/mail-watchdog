import logging
from pathlib import Path
from processor import MailProcessor
from utils import move_file_atomically

logger = logging.getLogger(__name__)

class MailWatcher:
    """
    MailWatcher continuously polls the pending/ directory for incoming .json files,
    transitions them atomically to processing/, and triggers the processing workflow.
    """
    def __init__(self, config, processor: MailProcessor):
        self.config = config
        self.processor = processor

    def scan_and_process(self):
        """
        Scans pending/ directory for new mail items and transfers them to processing/
        before processing all items currently located in processing/.
        """
        # 1. Promote new messages from pending/ to processing/
        try:
            # Match any files ending with .json (e.g. .msg.json or standard .json)
            for pending_file in self.config.pending_dir.glob("*.json"):
                if not pending_file.is_file():
                    continue
                
                dest_file = self.config.processing_dir / pending_file.name
                logger.debug(f"Detected new mail file: {pending_file.name}. Promoting to processing.")
                try:
                    move_file_atomically(pending_file, dest_file)
                except Exception as move_err:
                    logger.error(f"Failed to move file {pending_file.name} to processing: {move_err}")
        except Exception as scan_err:
            logger.error(f"Failed to scan pending directory: {scan_err}")

        # 2. Process all pending items residing in processing/
        try:
            for processing_file in self.config.processing_dir.glob("*.json"):
                if not processing_file.is_file():
                    continue
                
                try:
                    self.processor.process_file(processing_file)
                except Exception as proc_err:
                    logger.critical(f"Unhandled exception while processing file {processing_file.name}: {proc_err}")
        except Exception as scan_err:
            logger.error(f"Failed to scan processing directory: {scan_err}")
