# Subpage

Owned native child window with Page controls, independent rendering and shared application routing; see the Subpage guide.

[← API index](./README.md)

Source: [`saturn/subpage.py`](../../saturn/subpage.py) (line 11).

**Base class:** [Page](./Page.md)

## Public methods

| Method | Description |
| --- | --- |
| `attach(self, anchor='center', *, offset=None, follow_parent=False)` | Place relative to the owner's outer window; optionally follow it. |
| `show(self)` | Show this existing native window, preserving its controls. |
| `hide(self)` | Hide this native window without destroying its Page. |
| `to_front(self)` | Request focus for this native window. |
| `close(self)` | Request closing, honoring window.prevent_close and on_event. |
| `destroy(self)` | Force closing this window and its descendants. |

## Constructor parameters

```python
saturn.Subpage(parent: 'Page', *, main=None, title='Settings', modal=False, anchor='center', offset=None, follow_parent=False, backend=None)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `parent` | `Page` | `required` | Page owning this native child window. |
| `main` | `—` | `None` | Application entry point that receives a Page. |
| `title` | `—` | `'Settings'` | Title of a dialog, notification, or window. |
| `modal` | `—` | `False` | Block the owning native window's input until this child closes. |
| `anchor` | `—` | `'center'` | Placement relative to the owner: center, sides, corners, or Alignment. |
| `offset` | `—` | `None` | Displacement applied beyond the layout position. |
| `follow_parent` | `—` | `False` | Keep the child at its relative attachment position when windows move or resize. |
| `backend` | `—` | `None` | Rendering backend to use. For saturn.run(), omission selects OpenGL unless SATURN_BACKEND overrides it. |
