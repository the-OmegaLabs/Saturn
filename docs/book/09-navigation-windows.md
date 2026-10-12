# Navigation and Native Subwindows

Saturn provides shared route strings and native Subpage windows. `route` is responsible for reporting the current navigation
state; Subpage creates a genuinely independent OS window.

## Handling the application route

~~~python
def route_changed(event: saturn.RouteChangeEvent):
    print("route:", event.route)
    if event.route == "/settings":
        show_settings()
    elif event.route == "/":
        show_home()


page.on_route_change = route_changed
page.go("/settings")
~~~

Both `route = value` and `go(value)` notify the Page registered with on_route_change. The main page and subpages in a single
application share the route. Saturn does not automatically create, destroy, or switch a set of
Flet Views; the callback needs to decide for itself how controls or windows change.

## Opening a settings window

~~~python
def settings(child: saturn.Subpage):
    child.window.width = 420
    child.window.height = 360
    child.add(
        saturn.Text("Preferences", size=24),
        saturn.Switch(label="Notifications", value=True),
        saturn.FilledButton("Close", on_click=lambda e: child.close()),
    )


def open_settings(event):
    page.open_subpage(settings, title="Preferences")
~~~

page.open_subpage() returns the Subpage immediately. The window is created asynchronously on the UI thread; the
settings(child) callback passed in runs after the native window is established. The returned Subpage is also a Page:
you can add controls, set the theme, handle events, and call update.

## Window lifecycle

- show() and hide() show or hide the same window without destroying controls;
- close() requests closing and respects prevent_close and window.on_event;
- destroy() forcibly closes and destroys descendant windows;
- child.closed checks whether the window has closed; a closed Subpage cannot be reopened;
- closing a parent window closes all of its child windows; closing a child window does not close the parent window.

You can keep child window references to avoid creating duplicates:

~~~python
children = {}


def open_settings(event):
    child = children.get("settings")
    if child is None or child.closed:
        child = page.open_subpage(settings, title="Preferences")
        children["settings"] = child
    else:
        child.show()
        child.to_front()
~~~

## Native window properties

Window sizes are set through page.window. width and height represent the outer frame size including the native border;
page.width and page.height represent the read-only content area. Position, minimum size, maximum size,
title bar, visibility, and close interception all belong to the Window API.

Child windows can be positioned relative to the parent via anchor, offset, and follow_parent. modal=True
prevents the parent window from accepting input. The exact available capabilities depend on the platform; currently this is validated mainly on Windows.

## Key points of this chapter

The route only notifies the application that state changed; the application decides what to show. A Subpage is a native subwindow with its own Page and
window configuration. See the [full subwindow guide](../subpages.md) and the
[Window API](../window.md) for platform differences.
