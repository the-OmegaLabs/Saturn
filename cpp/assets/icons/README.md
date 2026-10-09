# Demo icon bitmaps

Rasterized from `packages/saturn-icons-material` Material Symbols Filled
(Apache-2.0), white+alpha so `IconButton` can tint with theme tokens.

| File | Glyph | Codepoint |
|------|-------|-----------|
| favorite.png | Icons.FAVORITE | U+E87E |
| check.png | Icons.CHECK | U+E668 |
| add.png | Icons.ADD | U+E145 |

Source TTF is not bundled here (multi-MB); these 48×48 PNGs are the C++ demo
assets. Rebuild with Pillow + MaterialSymbolsFilled.ttf if glyphs change.
