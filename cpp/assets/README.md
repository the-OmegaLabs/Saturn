# Fonts / demo assets

- `Inter-Regular.ttf` — static instance of Inter (SIL OFL 1.1), wght=400 opsz=14,
  from the same Inter variable face Python Saturn ships under `saturn/assets/`.
- See `OFL.txt`. Do not rename the family for redistributed Modified Versions.
- Demo logo: copied at build from `../.static/saturn-logo-transparent.png`
  (white+alpha), tinted `PRIMARY` in the header (52×40 contain).

## Icons (`assets/icons/`)

White+alpha 48×48 PNGs rasterized from Material Symbols Filled
(`packages/saturn-icons-material`, Apache-2.0) for C++ demo / `IconButton`:

- `favorite.png` — Icons.FAVORITE (U+E87E) — used by `saturn_demo` IconButton
- `check.png` / `add.png` — available for Checkbox/Elevated later

Full MaterialSymbols TTF is not shipped under `cpp/assets` (multi-MB). Rebuild
bitmaps with Pillow if glyphs change. See `assets/icons/README.md`.

- `test_img.png` — copy of `examples/assets/test_img.png` for C++ demo Image row.
