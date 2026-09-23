"""Render the classic Saturn mark without its black tile/background.

The old SVG uses black fills to hide the rear orbit. Rasterizing before
removing black preserves that intentional occlusion in a transparent PNG.
"""

from __future__ import annotations

import io
from pathlib import Path

import pygame


ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / ".static" / "saturn-logo.svg").read_text(encoding="utf-8")
source = source.replace('width="152"', 'width="608"', 1)
source = source.replace('height="152"', 'height="608"', 1)
# SDL_image's SVG path renderer skips <use>; inline both front-ring paths.
source = source.replace('<use href="#front-ring"',
                        '<path d="M49 98 A47 12.5 0 0 0 143 98"')
badge = pygame.image.load(io.BytesIO(source.encode("utf-8")), "saturn-logo.svg")
mark = pygame.Surface(badge.get_size(), pygame.SRCALPHA)
min_x, min_y = badge.get_width(), badge.get_height()
max_x = max_y = 0

for y in range(badge.get_height()):
    for x in range(badge.get_width()):
        pixel = badge.get_at((x, y))
        coverage = round(max(pixel.r, pixel.g, pixel.b) * pixel.a / 255)
        mark.set_at((x, y), (255, 255, 255, coverage))
        if coverage:
            min_x, min_y = min(min_x, x), min(min_y, y)
            max_x, max_y = max(max_x, x), max(max_y, y)

margin = 12
left, top = max(0, min_x - margin), max(0, min_y - margin)
right = min(mark.get_width(), max_x + margin + 1)
bottom = min(mark.get_height(), max_y + margin + 1)
mark = mark.subsurface((left, top, right - left, bottom - top)).copy()

destination = ROOT / ".static" / "saturn-logo-transparent.png"
pygame.image.save(mark, str(destination))
preview = pygame.Surface((640, 360))
preview.fill((85, 65, 145))
sample = pygame.transform.smoothscale(mark, (270, 200))
preview.blit(sample, ((640 - 270) // 2, (360 - 200) // 2))
preview_path = ROOT / ".static" / "logo-transparent-preview.png"
preview_path.parent.mkdir(parents=True, exist_ok=True)
pygame.image.save(preview, str(preview_path))
print(destination)
