# Page, the Control Tree, and Updates

Saturn's UI is a tree. `Page` is the root node, `controls` are its direct children, and containers
like `Row`, `Column`, `Stack`, and `ListView` keep owning children of their own.

~~~python
import saturn


def main(page: saturn.Page):
    title = saturn.Text("Today")
    
    actions = saturn.Row(
        controls=[
            saturn.Button("Refresh"),
            saturn.Button("Settings"),
        ], 
        spacing=8
    )

    page.add(title, actions)


saturn.run(main)
~~~

The control tree built by this code looks like this:

~~~text
Page
├── Text("Today")
└── Row
    ├── Button("Refresh")
    └── Button("Settings")
~~~

## Adding and removing

Page methods operate on the top-level controls:

~~~python
page.add(saturn.Text("one"), saturn.Text("two"))
page.insert(0, saturn.Text("first"))
page.remove_at(1)
page.clean()
~~~

A container's `controls` list can also be changed directly, but afterwards you must update the control that owns it:

~~~python
items = saturn.Column()
items.controls.append(saturn.Text("new item"))
items.update()
~~~

A Control cannot appear in two places on the page at once. Putting the same instance into the tree repeatedly
raises a ValueError; to show content more than once, create multiple control instances.

## Modifying properties

Control properties are mutable:

~~~python
message = saturn.Text("Waiting")
page.add(message)

message.value = "Ready"
message.color = saturn.Colors.PRIMARY
message.update()
~~~

`update` re-reconciles control ownership and re-lays-out when needed. When only appearance changes that don't affect geometry,
`repaint()` can request a draw only; for ordinary applications, `update()` is simpler.

`page.auto_update` defaults to `True`. When set to `False`, implicit control updates, input
state changes, and animation frames do not automatically request new frames; the control tree and state are still synchronized in memory. You can manually call
`page.update()` or `page.repaint()` to force the latest state to be shown, and setting it back to `True`
also refreshes immediately once:

~~~python
page.auto_update = False
message.value = "Updated in memory"
page.update()
page.auto_update = True
~~~

A single event usually modifies several objects; perform a single unified update at the end:

~~~python
def reset(event):
    name.value = ""
    status.value = "Reset"
    page.update()
~~~

Event callbacks can receive zero arguments, or one event object. An event's `event.control`
is the control that triggered it, and `event.page` is the owning page.

## Dialogs and overlays

`AlertDialog` and `SnackBar` are not placed in ordinary `controls`; instead `page.show_dialog()`
puts them into the page's `overlay`:

~~~python
def save(event):
    page.show_dialog(saturn.SnackBar("Saved"))


def close_dialog(event):
    page.pop_dialog()
~~~

A visible `AlertDialog` restricts keyboard focus; `SnackBar` is a non-blocking notice. To control the
lifecycle yourself, keep a reference to the `dialog` and call `page.pop_dialog(dialog)`.

## Ownership and threads

Once a control is attached to a `Page`, `control.page` points to its page and `control.parent` points to its parent control.
Do not reuse an attached control across pages.

Page callbacks are scheduled by Saturn's worker threads or the application's async loop. After modifying controls in a callback, calling
`update` is safe;

**Directly touching SDL, window handles, or the GPU renderer must happen on the UI thread.**

When you need to schedule work into the application context, use `page.run_task(handler, ...)`.

## Key points of this chapter

Build the control tree first, modify state in events, then request an update. Next, use `Row`, `Column`,
`Container`, and `Stack` to arrange this tree into a readable interface.
