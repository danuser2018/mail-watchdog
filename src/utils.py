import json
import shutil
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def move_file_atomically(src_path: Path, dest_path: Path):
    """
    Moves a file to a new path. Since moving can sometimes cross file systems,
    we use shutil.move which is robust, followed by standard error logging.
    """
    try:
        # Create parents of dest_path if they do not exist
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_path), str(dest_path))
        logger.debug(f"Atomically moved file from '{src_path}' to '{dest_path}'")
    except Exception as e:
        logger.error(f"Failed to move file from '{src_path}' to '{dest_path}': {e}")
        raise

def load_json(file_path: Path) -> dict:
    """Reads a file and returns its parsed JSON dictionary."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data: dict, file_path: Path):
    """Writes a dictionary as a JSON file, formatted with indentations."""
    # Write to a temporary file in the same directory first, then rename for atomicity
    temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp_path.replace(file_path)
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        logger.error(f"Failed to save JSON to '{file_path}': {e}")
        raise
