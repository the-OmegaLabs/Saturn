# FloatingActionButtonMenu

Menu of actions expanded from a floating button.

[← API index](./README.md)

Source: [`saturn/widgets/floating.py`](../../saturn/widgets/floating.py) (line 248).

## Preview

![FloatingActionButtonMenu control in the dark theme](../images/controls/FloatingActionButtonMenu.png)

## Example

Run this code from the repository root to display the control shown above.

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.FloatingActionButtonMenu([saturn.FloatingActionButtonMenuItem("New document", icon=saturn.Icons.ADD), saturn.FloatingActionButtonMenuItem("Upload", icon=saturn.Icons.UPLOAD)], expanded=True))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**Base class:** [Control](./Control.md)

## Public methods

| Method | Description |
| --- | --- |
| `toggle(self)` | Switches between expanded and collapsed states. |
| `close(self)` | Closes a window or expanded menu. |

## Constructor parameters

```python
saturn.FloatingActionButtonMenu(items=None, *, icon=<Icons.ADD: 57669>, expanded=False, on_select=None, **base)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `items` | `—` | `None` | Items passed to a layout, group, or menu. |
| `icon` | `—` | `<Icons.ADD: 57669>` | Icon to draw. |
| `expanded` | `—` | `False` | Whether the floating component or menu is expanded. |
| `on_select` | `—` | `None` | Callback called when a menu item or option is selected. |
| `**base` | `—` | `additional keyword arguments` | Keyword arguments passed to Control, such as width and height. |

`**base` accepts [common Control constructor parameters](./Control.md#constructor-parameters), such as `width`, `height`, and `visible`.
