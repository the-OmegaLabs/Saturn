# Icon

Displays a Material icon.

[← API index](./README.md)

Source: [`saturn/widgets/basic.py`](../../saturn/widgets/basic.py) (line 50).

## Preview

![Icon control in the dark theme](../images/controls/Icon.png)

## Example

Run this code from the repository root to display the control shown above.

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.Icon(saturn.Icons.FAVORITE, size=56, color=saturn.Colors.PRIMARY))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**Base class:** [Control](./Control.md)

## Constructor parameters

```python
saturn.Icon(icon, *, color=None, size: 'float' = 24, **base)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `icon` | `—` | `required` | Icon to draw. |
| `color` | `—` | `None` | Color of foreground content, text, or drawing. |
| `size` | `float` | `24` | Size of the text, icon, or control. |
| `**base` | `—` | `additional keyword arguments` | Keyword arguments passed to Control, such as width and height. |

`**base` accepts [common Control constructor parameters](./Control.md#constructor-parameters), such as `width`, `height`, and `visible`.
