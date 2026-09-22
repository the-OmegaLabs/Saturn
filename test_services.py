"""Self-check for desktop service compatibility."""
import asyncio
import tempfile
from pathlib import Path

import saturn as ft


async def check_file_picker():
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "hello.txt"
        source.write_bytes(b"hello")
        events = []
        picker = ft.FilePicker(on_result=events.append)
        picker._pick_paths = lambda *_: [str(source)]

        files = await picker.pick_files(
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["txt"], with_data=True)
        assert files == [ft.FilePickerFile(0, "hello.txt", 5,
                                           str(source), b"hello")]
        assert events[0].files is files

        target = Path(tmp) / "saved.bin"
        picker._save_path = lambda *_: str(target)
        assert await picker.save_file(src_bytes=b"saved") == str(target)
        assert target.read_bytes() == b"saved"

        picker._choose_directory = lambda *_: tmp
        assert await picker.get_directory_path() == tmp

        try:
            await picker.pick_files(compression_quality=101)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid compression quality accepted")


if __name__ == "__main__":
    asyncio.run(check_file_picker())
    print("ALL SERVICE TESTS PASS")
