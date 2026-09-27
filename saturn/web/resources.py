"""Serve registered immutable resources; request paths never select local files."""
import hashlib
import mimetypes
from pathlib import Path


class Resources:
    def __init__(self):
        self.files = {}

    def register(self, path):
        path = Path(path).resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        stat = path.stat()
        identifier = hashlib.sha256(f"{path}:{stat.st_mtime_ns}:{stat.st_size}".encode()).hexdigest()
        self.files[identifier] = path
        return identifier

    def response(self, identifier):
        from fastapi import HTTPException
        from fastapi.responses import FileResponse
        if identifier not in self.files:
            raise HTTPException(404, "Unknown resource")
        return FileResponse(self.files[identifier], media_type=mimetypes.guess_type(str(self.files[identifier]))[0],
                            headers={"Cache-Control": "public, max-age=31536000, immutable"})
