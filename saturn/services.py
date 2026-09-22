"""Small desktop service subset compatible with Flet 1.0."""
from __future__ import annotations

import asyncio
import enum
import inspect
from dataclasses import dataclass
from pathlib import Path


class FilePickerFileType(enum.Enum):
    ANY = "any"
    MEDIA = "media"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    CUSTOM = "custom"


@dataclass
class FilePickerFile:
    id: int
    name: str
    size: int
    path: str | None = None
    bytes: bytes | None = None


@dataclass
class FilePickerUploadFile:
    upload_url: str
    method: str = "PUT"
    id: int | None = None
    name: str | None = None


@dataclass
class FilePickerResultEvent:
    name: str
    control: "FilePicker"
    files: list[FilePickerFile]
    data: object = None

    @property
    def page(self):
        return self.control.page


@dataclass
class FilePickerUploadEvent:
    name: str
    control: "FilePicker"
    file_name: str
    progress: float | None = None
    error: str | None = None
    data: object = None

    @property
    def page(self):
        return self.control.page


class FilePicker:
    """Desktop FilePicker backed by tkinter's native OS dialogs."""

    def __init__(self, on_result=None, on_upload=None, *, data=None,
                 key=None, ref=None):
        self.on_result = on_result
        self.on_upload = on_upload
        self.data = data
        self.key = key
        self.ref = ref
        self.page = None
        self._picked: list[FilePickerFile] = []

    async def pick_files(self, dialog_title=None, initial_directory=None,
                         file_type=FilePickerFileType.ANY,
                         allowed_extensions=None, allow_multiple=False,
                         with_data=False, compression_quality=0,
                         cancel_upload_on_window_blur=True):
        if not 0 <= compression_quality <= 100:
            raise ValueError("compression_quality must be between 0 and 100 inclusive")
        paths = await asyncio.to_thread(
            self._pick_paths, dialog_title, initial_directory,
            file_type, allowed_extensions, allow_multiple)
        self._picked = [self._file(i, path, with_data)
                        for i, path in enumerate(paths)]
        await _emit(self.on_result, FilePickerResultEvent(
            "result", self, self._picked, self.data))
        return self._picked

    async def get_directory_path(self, dialog_title=None,
                                 initial_directory=None):
        return await asyncio.to_thread(
            self._choose_directory, dialog_title, initial_directory)

    async def save_file(self, dialog_title=None, file_name=None,
                        initial_directory=None,
                        file_type=FilePickerFileType.ANY,
                        allowed_extensions=None, src_bytes=None):
        path = await asyncio.to_thread(
            self._save_path, dialog_title, file_name, initial_directory,
            file_type, allowed_extensions)
        if path and src_bytes is not None:
            await asyncio.to_thread(Path(path).write_bytes, src_bytes)
        return path or None

    async def upload(self, files: list[FilePickerUploadFile]):
        raise NotImplementedError("FilePicker.upload is not supported; upload picked paths directly")

    @staticmethod
    def _file(id_: int, path: str, with_data: bool) -> FilePickerFile:
        p = Path(path)
        return FilePickerFile(id_, p.name, p.stat().st_size, str(p),
                              p.read_bytes() if with_data else None)

    @staticmethod
    def _pick_paths(title, initial, file_type, extensions, multiple):
        from tkinter import Tk, filedialog

        root = Tk()
        root.withdraw()
        try:
            kwargs = _dialog_kwargs(title, initial, file_type, extensions)
            value = (filedialog.askopenfilenames(**kwargs) if multiple
                     else filedialog.askopenfilename(**kwargs))
            return list(value) if multiple else ([value] if value else [])
        finally:
            root.destroy()

    @staticmethod
    def _choose_directory(title, initial):
        from tkinter import Tk, filedialog

        root = Tk()
        root.withdraw()
        try:
            return filedialog.askdirectory(
                title=title or "FilePicker", initialdir=initial or None) or None
        finally:
            root.destroy()

    @staticmethod
    def _save_path(title, file_name, initial, file_type, extensions):
        from tkinter import Tk, filedialog

        root = Tk()
        root.withdraw()
        try:
            kwargs = _dialog_kwargs(title, initial, file_type, extensions)
            kwargs["initialfile"] = file_name or None
            return filedialog.asksaveasfilename(**kwargs) or None
        finally:
            root.destroy()


def _dialog_kwargs(title, initial, file_type, extensions):
    kind = (file_type if isinstance(file_type, FilePickerFileType)
            else FilePickerFileType(file_type))
    patterns = {
        FilePickerFileType.ANY: "*.*",
        FilePickerFileType.IMAGE: "*.png *.jpg *.jpeg *.gif *.bmp *.webp",
        FilePickerFileType.VIDEO: "*.mp4 *.mov *.avi *.mkv *.webm",
        FilePickerFileType.AUDIO: "*.mp3 *.wav *.ogg *.flac *.m4a",
        FilePickerFileType.MEDIA: "*.png *.jpg *.jpeg *.gif *.mp4 *.mov *.mp3 *.wav",
    }
    if kind is FilePickerFileType.CUSTOM:
        pattern = " ".join(f"*.{str(x).lstrip('*.')}" for x in (extensions or []))
        pattern = pattern or "*.*"
    else:
        pattern = patterns[kind]
    return {"title": title or "FilePicker", "initialdir": initial or None,
            "filetypes": [(kind.value.title(), pattern), ("All files", "*.*")]}


async def _emit(handler, event):
    if handler is None:
        return
    try:
        args = (event,) if len(inspect.signature(handler).parameters) else ()
    except (TypeError, ValueError):
        args = (event,)
    result = handler(*args)
    if inspect.isawaitable(result):
        await result
