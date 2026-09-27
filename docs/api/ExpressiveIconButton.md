# ExpressiveIconButton

Icon button with Expressive size and shape changes.

[← API index](./README.md)

Source: [`saturn/widgets/buttons.py`](../../saturn/widgets/buttons.py) (line 404).

## Preview

![ExpressiveIconButton control in the dark theme](../../.static/controls/ExpressiveIconButton.png)

## Example

Run this code from the repository root to display the control shown above.

```python
import saturn


def main(page: saturn.Page):
    page.window.width = 720
    page.window.height = 360
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.ExpressiveIconButton(saturn.Icons.EDIT, size="large"))
    page.update()


saturn.run(main, backend=saturn.Renderer.SOFTWARE)
```

**Base class:** [IconButton](./IconButton.md)

## Constructor parameters

```python
saturn.ExpressiveIconButton(icon, *, size='small', **kwargs)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `icon` | `—` | `required` | Icon to draw. |
| `size` | `—` | `'small'` | Size of the text, icon, or control. |
| `**kwargs` | `—` | `additional keyword arguments` | Keyword arguments passed to the parent constructor. |
