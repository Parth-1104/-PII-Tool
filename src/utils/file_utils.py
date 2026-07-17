import os
import shutil
from pathlib import Path
from typing import Union
from .logger import get_logger

logger = get_logger("file_utils")


def validate_docx_path(file_path: Union[str, Path]) -> Path:
    """
    Validates that the input file path exists and has a .docx extension.
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Input document not found at: {path}")
    if not path.is_file():
        raise ValueError(f"Input path must be a regular file: {path}")
    if path.suffix.lower() != ".docx":
        raise ValueError(f"Input file must be a .docx document. Received: {path.suffix}")
    return path


def ensure_output_directory(output_path: Union[str, Path]) -> Path:
    """
    Ensures that the parent directory of the target output path exists.
    If it does not exist, creates all intermediate directories.
    """
    path = Path(output_path).resolve()
    if path.suffix.lower() != ".docx":
        raise ValueError(f"Output file path must end with .docx. Received: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def backup_file(file_path: Union[str, Path]) -> Path:
    """
    Creates a backup copy of a file before overwriting or modifying it.
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Cannot create backup; file does not exist: {path}")
    backup_path = path.with_suffix(f".bak{path.suffix}")
    shutil.copy2(path, backup_path)
    logger.debug(f"Created backup of {path.name} at {backup_path.name}")
    return backup_path
