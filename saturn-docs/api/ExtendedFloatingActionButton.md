# ExtendedFloatingActionButton

Floating action button with an icon and text.

[← API index](./README.md)

Source: [`saturn/widgets/fab.py`](../../saturn/widgets/fab.py) (line 160).

## Preview

![ExtendedFloatingActionButton control in the dark theme](../images/controls/ExtendedFloatingActionButton.png)

## Example

Run this code from the repository root to display the control shown above.

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.ExtendedFloatingActionButton("New document", icon=saturn.Icons.ADD))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**Base class:** [FloatingActionButton](./FloatingActionButton.md)

## Constructor parameters

```python
saturn.ExtendedFloatingActionButton(text: 'str', *, icon=None, size: 'str' = 'standard', **kwargs)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `text` | `str` | `required` | Text displayed on the control. |
| `icon` | `—` | `None` | Icon to draw. |
| `size` | `str` | `'standard'` | Size of the text, icon, or control. |
| `**kwargs` | `—` | `additional keyword arguments` | Keyword arguments passed to the parent constructor. |
