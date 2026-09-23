# Saturn logo

[← Documentation home](./README.md) · [Screenshot gallery](./gallery.md)

The main README uses the classic black square Saturn logo. Demos use a transparent version of the same planet-and-ring design, which can be tinted for light or dark themes.

![Preview of the transparent logo on a purple background](../.static/logo-transparent-preview.png)

Transparent asset: [saturn-logo-transparent.png](../.static/saturn-logo-transparent.png). It is generated from the [classic SVG](../.static/saturn-logo.svg): the planet first occludes the rear ring, then black pixels become transparent. Regenerate it with `python tools/make_transparent_logo.py`.

All demo headers and their 960 × 800 window size are defined centrally in [`examples/demo_common.py`](../examples/demo_common.py).
