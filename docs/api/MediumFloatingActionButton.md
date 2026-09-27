# MediumFloatingActionButton

Medium floating action button.

[← API index](./README.md)

Source: [`saturn/widgets/fab.py`](../../saturn/widgets/fab.py) (line 159).

## Preview

![MediumFloatingActionButton control in the dark theme](../../.static/controls/MediumFloatingActionButton.png)

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
    page.add(saturn.MediumFloatingActionButton(saturn.Icons.ADD))
    page.update()


saturn.run(main, backend=saturn.Renderer.SOFTWARE)
```

**Base class:** [FloatingActionButton](./FloatingActionButton.md)

## Constructor parameters

```python
saturn.MediumFloatingActionButton(icon=None, **kwargs)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `icon` | `—` | `None` | Icon to draw. |
| `**kwargs` | `—` | `additional keyword arguments` | Keyword arguments passed to the parent constructor. |
