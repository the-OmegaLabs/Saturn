# Events and State

Saturn's interaction model is "event callbacks modify state, then update the control tree". Controls do not require you to use any particular
state management library; an Application object, closures, or ordinary data classes can all hold state.

## Handling clicks

~~~python
import saturn


class Application:
    def __init__(self):
        self.count = 0

    def main(self, page: saturn.Page):
        self.label = saturn.Text("0", size=32)
        page.add(
            self.label,
            saturn.FilledButton("Increment", on_click=self.increment),
        )

    def increment(self, event: saturn.ControlEvent):
        self.count += 1
        self.label.value = str(self.count)
        self.label.update()


app = Application()
saturn.run(app.main)
~~~

The on_click callback usually receives a ControlEvent. `event.control` is the button itself,
`event.page` is the Page, and `event.data` is usually None. The callback can also be defined as a zero-argument function:

~~~python
saturn.Button("Close", on_click=lambda: page.window.close())
~~~

Saturn decides whether to pass the event based on the function signature.

## Common event data

| Control | Event | event.data |
| --- | --- | --- |
| Button, Container | on_click | usually None |
| TextField | on_change, on_submit | current string |
| Checkbox, Switch, Radio | on_change | "true", "false"; Checkbox tristate may also be "null" |
| Slider | on_change | current numeric value |
| Dropdown | on_select | option key |
| ListView | on_scroll | current scroll offset |

Reading control properties is usually more intuitive than parsing event.data:

~~~python
def changed(event):
    print(field.value, checkbox.value, slider.value)
~~~

## Synchronous and asynchronous handlers

Event handlers can be synchronous functions, `async def`, or plain functions returning an awaitable. Asynchronous
handlers run in the application's async loop:

~~~python
import asyncio


async def save(event):
    await asyncio.sleep(0.2)
    status.value = "Saved"
    status.update()
~~~

Don't block the callback directly with time-consuming synchronous work. Use page.run_task to schedule work into the application context,
or use threads/processes yourself and then hand the results back to the page. Do not touch SDL or
GPU objects directly from background threads.

## A maintainable state boundary

Keep business state in the Application and store view controls as attributes; event methods do only three things:
read state, change state, and update the affected controls.

~~~python
class TodoApp:
    def __init__(self):
        self.tasks = []

    def main(self, page):
        self.input = saturn.TextField(label="New task")
        self.items = saturn.Column(spacing=4)
        page.add(self.input, saturn.FilledButton("Add", on_click=self.add), self.items)

    def add(self, event):
        text = self.input.value.strip()
        if not text:
            return
        self.tasks.append(text)
        self.input.value = ""
        self.items.controls.append(saturn.Text(text))
        self.items.update()
        self.input.update()
~~~

If a single event affects multiple areas, use page.update():

~~~python
self.summary.value = f"{len(self.tasks)} tasks"
self.items.controls = [saturn.Text(task) for task in self.tasks]
self.page.update()
~~~

## Page events

~~~python
def resized(event: saturn.PageResizeEvent):
    print(event.width, event.height, event.page.title)


def keyboard(event: saturn.KeyboardEvent):
    if event.ctrl and event.key == "S":
        save_document()


page.on_resize = resized
page.on_keyboard_event = keyboard
~~~

on_resize, on_keyboard_event, and on_platform_brightness_change receive event objects,
rather than a Page as passed directly in older versions. The handler can be a single callback or a list of callbacks.

## Key points of this chapter

Event objects tell you what happened, Application state tells you what the application currently is, and the control tree
is responsible for displaying the result. Once these three boundaries are clear, the application can grow without pushing business logic into layout code.
