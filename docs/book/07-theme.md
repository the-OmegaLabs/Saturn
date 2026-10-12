# Theme, Colors, and Fonts

The Page centrally manages the color scheme, light/dark mode, and font aliases. Start from the theme first, then override colors on the few
controls that need it, avoiding writing a duplicate set of parameters on every button.

## Light and dark themes

~~~python
page.theme_mode = saturn.ThemeMode.DARK
page.theme = saturn.Theme(font_family="Inter", color_scheme_seed="#6750A4")
page.dark_theme = saturn.Theme(font_family="Inter", color_scheme_seed="#6750A4")
~~~

ThemeMode has LIGHT, DARK, and SYSTEM. Explicitly specifying LIGHT or DARK makes it easier to get consistent results
across different computers; SYSTEM follows the platform's current app light/dark preference.

color_scheme_seed only selects among the color role schemes Saturn already supports; it is not a full Material
dynamic-color engine. Color tokens are available from saturn.Colors, for example PRIMARY,
ON_SURFACE, SURFACE_CONTAINER, and ERROR. Control-level parameters like `color` and `bgcolor`
can still override the theme.

## Local fonts

Register font files on the Page, then use them by alias:

~~~python
from pathlib import Path

font_path = Path(__file__).parent / "assets" / "Brand.woff2"
page.fonts = {"brand": str(font_path)}
page.theme = saturn.Theme(font_family="brand")
page.add(saturn.Text("Brand font", font_family="brand", size=24))
~~~

Local TTF, OTF, TTC, WOFF, and WOFF2 are supported. Relative paths are first resolved against the current working directory,
then against the assets directory; when shipping an app, it is recommended to build an explicit path from `__file__`.

HTTP(S) fonts load in the background. During loading the fallback font is shown first; once loaded, Saturn
re-measures the text and refreshes the layout. If the download fails, the fallback text is kept and a warning is logged. After modifying the page.fonts
dict, call page.update().

Saturn ships with Inter, and Chinese fonts can be installed via the optional CJK font package. Explicitly setting a
fallback list helps control the glyph source for mixed-language text.

## Colors and text styles

You can set colors directly on controls, or construct a TextStyle:

~~~python
heading = saturn.Text(
    "Build with Saturn",
    style=saturn.TextStyle(
        size=28,
        weight=saturn.FontWeight.BOLD,
        color=saturn.Colors.ON_SURFACE,
    ),
)
~~~

Text also supports common options such as size, weight, italic, text_align, max_lines, no_wrap, and
overflow. For full details see [Text](../api/Text.md) and
[TextStyle](../api/TextStyle.md).

## Theme changes

After modifying the Page theme or theme mode, call page.update() to apply the new styles:

~~~python
def toggle_theme(event):
    page.theme_mode = (
        saturn.ThemeMode.LIGHT
        if page.theme_mode is saturn.ThemeMode.DARK
        else saturn.ThemeMode.DARK
    )
    page.update()
~~~

Themes are isolated per Page. Native subwindows initially inherit the parent window's theme and fonts, but can be configured independently afterwards.

## Key points of this chapter

The theme controls application defaults, control parameters handle local exceptions, and font aliases decouple resource paths from styles.
For window and platform theme boundaries see the [Page guide](../page.md).
