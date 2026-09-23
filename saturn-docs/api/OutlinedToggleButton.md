# OutlinedToggleButton

Toggle button with an outlined style.

[← API index](./README.md)

Source: [`saturn/widgets/toggle_button.py`](../../saturn/widgets/toggle_button.py) (line 76).

## Preview

![OutlinedToggleButton control in the dark theme](../images/controls/OutlinedToggleButton.png)

## Example

Run this code from the repository root to display the control shown above.

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.OutlinedToggleButton("Filter", checked=True))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**Base class:** [ToggleButton](./ToggleButton.md)

## Constructor parameters

```python
saturn.OutlinedToggleButton(content=None, **kwargs)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `content` | `—` | `None` | Text or child control to display. |
| `**kwargs` | `—` | `additional keyword arguments` | Keyword arguments passed to the parent constructor. |
