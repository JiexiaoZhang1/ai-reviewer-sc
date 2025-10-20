"""Temporary storage helpers for handling uploaded archives."""

from __future__ import annotations

import contextlib
import io
import shutil
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator

from fastapi import UploadFile

EXCLUDE_DIRS = {
    "__pycache__",
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "node_modules",
    "vendor",
    "dist",
    "build",
}


@contextlib.contextmanager
def unpack_zip_file(upload: UploadFile) -> Iterator[Path]:
    """Extract the uploaded zip file into a temporary directory."""

    buffer = io.BytesIO(read_upload_to_bytes(upload))
    with TemporaryDirectory(prefix="ai-reviewer-") as temp_dir:
        target = Path(temp_dir)
        with zipfile.ZipFile(buffer) as archive:
            archive.extractall(target)
        _cleanup_unwanted_dirs(target)
        yield target


def read_upload_to_bytes(upload: UploadFile) -> bytes:
    """Read the entire upload payload, supporting sync and async reads."""

    if hasattr(upload.file, "seek"):
        upload.file.seek(0)
    data = upload.file.read()  # type: ignore[assignment]
    if isinstance(data, memoryview):
        return data.tobytes()
    if isinstance(data, bytes):
        return data
    raise TypeError("Unsupported upload object; expected bytes-like payload.")


def _cleanup_unwanted_dirs(root: Path) -> None:
    """Remove directories that are not useful for static analysis."""

    for path in root.glob("**/*"):
        if path.is_dir() and path.name in EXCLUDE_DIRS:
            shutil.rmtree(path, ignore_errors=True)
