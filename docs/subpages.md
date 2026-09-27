# Native child windows and routes

`Subpage` is an owned native window, comparable to `tkinter.Toplevel`. It has
its own controls, overlays, focus, HWND, renderer and window configuration.
It inherits `Page`, so ordinary `add()`, `remove()`, `clean()`, `update()` and
control events work the same way as in the main window.

## Create and operate a child

```python
import saturn as st

def settings(child: st.Subpage):
    child.window.width = 420
    child.window.height = 350
    child.add(st.Text("Preferences", size=24),
              st.Switch(label="Notifications", value=True),
              st.FilledButton("Close", on_click=lambda e: child.close()))
    print(child.window.hwnd)  # Native creation is complete in this callback.

def main(page: st.Page):
    windows = {}
    def open_settings(e):
        child = windows.get("settings")
        if child is None or child.closed:
            child = page.open_subpage(settings, title="Preferences")
            windows["settings"] = child
        else:
            child.show()
            child.to_front()
    page.add(st.FilledButton("Settings", on_click=open_settings))

st.run(main)
```

`page.open_subpage()` returns immediately. Native creation is queued on the
UI thread; properties and controls may be configured on the returned object
immediately. The optional sync/async `main(child)` callback runs after native
creation. `child.window.hwnd` is zero before creation, and `child.ready` then
becomes true. `child.creation_error` records native creation failures.

You can also create the same window with `st.Subpage(page, main=settings)`.
Create controls for their owning Page; one control instance cannot belong to
both windows. Application data can be shared normally through closures or an
application object.

| Operation | Behavior |
| --- | --- |
| `child.add(control)` | Add controls and request layout/redrawing |
| `control.update()` / `child.update()` | Refresh mutated controls |
| `child.window.width`, `.height`, `.left`, `.top` | Configure native outer dimensions and position |
| `child.show()` / `.hide()` | Show/hide the same window, preserving controls |
| `child.to_front()` | Request native focus |
| `child.close()` | Request closing; honor `window.prevent_close` and `window.on_event` |
| `child.destroy()` | Force closing the window and descendants |
| `child.closed` | Whether closing has been requested |
| `child.parent_page` | The Page that owns this window |
| `page.subpages` | Tuple of currently open direct children |
| `child.open_subpage(...)` | Create a grandchild owned by this child |
| `child.renderer.context` | Read the child's actual renderer |

Closing a child leaves the main window running. Closing its owner closes its
descendants. A closed child cannot be reopened; create another instance.
Hide/show is the way to retain the same window and controls.
Explicitly hidden windows stop consuming animation/render frames until shown.

## Position relative to the owner

```python
child = page.open_subpage(settings, title="Preferences", anchor="right",
                          offset=(12, 0), follow_parent=True)

# Reattach an existing window.
child.attach("center")
child.attach("right", offset=st.Offset(12, 0), follow_parent=True)
```

The default is centered inside the owner's outer window. `left`, `right`,
`top`, and `bottom` place the child outside the corresponding owner edge.
`top_left`, `top_right`, `bottom_left`, and `bottom_right` align inside its
corners. An `Alignment` value positions it proportionally inside the owner.
Offsets use logical pixels. `follow_parent=True` updates placement when the
owner moves or either window changes size; a manual child move is then
replaced by its attachment position on the next event-loop pass.

Attachment is window ownership and positioning, not embedding a drawable
region in the main Page. Placement does not clamp to monitor work areas.
Set `modal=True` to block the owner's input until the child closes. On Windows
the native owner is registered on the HWND and the modal owner is disabled.
Multiple windows are verified on Windows with Software, OpenGL and Vulkan;
equivalent owner/placement behavior on other platforms is not yet verified.

Themes, font aliases and renderer options initially inherit from the owner;
later changes belong to the child Page. Each window restores its theme and
font configuration before drawing. Using different font alias maps across
windows can invalidate the shared text caches when switching windows.
`backend=st.Renderer.VULKAN` can override the inherited backend. Native draws
share the application UI thread, so expensive shaders or synchronized
presentation in several animated windows can affect responsiveness.

## Shared application routing

All Pages belonging to the same root application observe one route string.
Either assignment or `go()` changes it and dispatches `RouteChangeEvent` to
the `on_route_change` callback on every open Page that has a handler:

```python
def on_route_change(e):
    print(e.route, e.page)
    if e.route == "/settings":
        open_settings(None)

page.on_route_change = on_route_change
page.route = ""           # Empty routes are valid.
page.go("/settings")
child.go("/settings/audio")  # page.route changes too.
```

Setting the same route again does not dispatch another event. Register the
handler before changing the route. Routing does not create or close windows
automatically: the handler decides which window or controls to show. Native
close also leaves the route unchanged. Handlers use the ordinary worker/async
dispatch and may overlap; keep shared application state consistent.

The earlier in-window `View`/stack experiment was removed. `views`,
`push_subpage()`, `pop_subpage()`, `register_subpage()` and `on_view_pop` are
not part of this API. Browser history and deep links are not implemented.

See [the native settings demo](../examples/subpage_settings.py),
[Window properties](./window.md), and [Shader demos](./effects-demos.md).
