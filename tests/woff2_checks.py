"""Generate real WOFF2 fixtures and exercise loading, rendering, and weights."""
import io
import os
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fontTools.ttLib import TTFont

import saturn as ft
from saturn import text


def compress(source: Path, target: Path):
    font = TTFont(source)
    try:
        font.flavor = 'woff2'
        font.save(target)
    finally:
        font.close()
    assert target.read_bytes()[:4] == b'wOF2'


def check():
    assets = Path(text.__file__).parent / 'assets'
    with TemporaryDirectory() as temp:
        directory = Path(temp)
        cache_root = Path(__file__).resolve().parents[1] / '.build-probe' / 'woff2-checks'
        cache_root.mkdir(parents=True, exist_ok=True)
        static = directory / 'static.woff2'
        variable = directory / 'variable.woff2'
        compress(assets / 'Inter-Bold.ttf', static)
        compress(assets / 'Inter-VariableFont_opsz,wght.ttf', variable)

        with patch('saturn.text.Path.home', return_value=cache_root):
            source = text._font_source(str(static))
            assert Path(source).read_bytes()[:4] == b'\x00\x01\x00\x00'
            assert text._font_source(str(static)) == source
            assert text.get_font(18, family=str(static)).size('Saturn')[0] > 0
            assert text._primary_link(str(static), 400, False)[1] == source
            assert text.render_line('Saturn', 18, family=str(static)).get_width() > 0

            class App:
                size = (300, 200)
                def post(self, _call): pass
                def mark_dirty(self): pass
            page = ft.Page(App())
            page.fonts = {'web': str(static)}
            page.theme = ft.Theme(font_family='web')
            assert text.get_font(18).size('Saturn')[0] > 0
            assert text._primary_link('web', 400, False)[1] == source

            invalid = directory / 'invalid.woff2'
            invalid.write_bytes(b'not a font')
            try:
                text._font_source(str(invalid))
            except ValueError:
                pass
            else:
                raise AssertionError('invalid WOFF2 data was accepted')

            original_ns = static.stat().st_mtime_ns
            os.utime(static, ns=(original_ns + 2_000_000, original_ns + 2_000_000))
            assert text._font_source(str(static)) != source

        blocker = directory / 'not-a-directory'
        blocker.write_text('blocked')
        with patch('saturn.text.Path.home', return_value=blocker), \
             patch('saturn.text.tempfile.gettempdir', return_value=str(blocker)):
            memory = text._font_source(str(variable))
            assert isinstance(memory, io.BytesIO)
            text.register_fonts({'web-variable': str(variable)})
            assert text._primary_link('web-variable', 400, False)[1] is memory
            assert text.get_font(18, family='web-variable').size('Saturn')[0] > 0
            text.get_font(18, family='web-variable', weight=600)
            slot = (memory, 600)
            deadline = time.monotonic() + 8
            while slot in text._pending_inst and time.monotonic() < deadline:
                time.sleep(.02)
            assert slot not in text._pending_inst
            generated = text._mem_instances[slot].getvalue()
            weighted = TTFont(io.BytesIO(generated))
            try:
                assert weighted['OS/2'].usWeightClass == 600
            finally:
                weighted.close()
            assert text.get_font(18, family='web-variable', weight=600).size('Saturn')[0] > 0

    text.default_family = None
    text.register_fonts({})


if __name__ == '__main__':
    check()
    print('WOFF2 FONT CHECKS PASS')
