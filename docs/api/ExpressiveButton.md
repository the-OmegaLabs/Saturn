# ExpressiveButton

Material Expressive button with changing size and shape.

[← API index](./README.md)

Source: [`saturn/widgets/buttons.py`](../../saturn/widgets/buttons.py) (line 280).

## Preview

![ExpressiveButton control in the dark theme](../../.static/controls/ExpressiveButton.png)

## Example

Run this code from the repository root to display the control shown above.

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.ExpressiveButton("Create", size="medium", icon=saturn.Icons.ADD))
    page.update()


saturn.run(main, backend=saturn.Renderer.SOFTWARE, width=720, height=360)
```

**Base class:** [Button](./Button.md)

## Constructor parameters

```python
saturn.ExpressiveButton(content=None, *, size='small', shape='round', **kwargs)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `content` | `—` | `None` | Text or child control to display. |
| `size` | `—` | `'small'` | Size of the text, icon, or control. |
| `shape` | `—` | `'round'` | Base shape of the button. |
| `**kwargs` | `—` | `additional keyword arguments` | Keyword arguments passed to the parent constructor. |
