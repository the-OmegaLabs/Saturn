# Project scaffold: the first window

[← Handbook contents](./README.md) · [Next chapter: Page and the control tree](./book/03-page-control-tree.md)

This chapter builds a very small Saturn application. It uses a class to hold the interface objects, as the entry callback for saturn.run.

## 1. Create the project

Saturn is not currently published to PyPI. When creating a new project, install from the Saturn repository to avoid installing a different
same-named package after running `uv add saturn`
or `pip install saturn`.

Use uv to create a Python project and add the Saturn repository as a dependency:

~~~powershell
uv init hello
uv add "saturn @ git+https://github.com/the-OmegaLabs/Saturn.git"
~~~

The project directory can stay very simple:

~~~text
hello/
├── main.py
├── pyproject.toml
└── uv.lock
~~~

uv maintains the dependencies and the lock file. Committing uv.lock lets other developers install the same set of versions.
When developing Saturn itself, clone the repository and run `uv sync`; this installs the
dependencies needed by the repository examples.

## 2. Write the minimal application

Write the following in main.py:

~~~python
import saturn


class Application: # your application class
    def __init__(self):
        pass

    def create_window(self, page: saturn.Page):
        self.page = page # attach the page

        hello = saturn.Text(value="Hello, World!") # a text control

        self.page.add(hello) # add the control to the control tree


if __name__ == "__main__":
    saturn.run(main=Application().create_window) # run the Saturn application
~~~

Run it:

~~~powershell
uv run main.py
~~~

A window appears with "Hello, World!". These lines establish the basic structure of a Saturn application:

- `Application` is your own application object, where you can keep control references and application state.
- `.create_window` is the entry callback; after `saturn.run` starts, it passes the newly created `Page` to it.
- `Page` is the root control of the current window; use `page.add()` to add controls to the visible interface.
- `Text` is a control that displays text.

Note that `saturn.run(main=Application().create_window)` has no parentheses at the end.

With parentheses,
`.create_window` would be called immediately, but at that point there is no `Page` to pass in yet. The bound method keeps the
`Application` instance, so during the run you can access `self`, letting functions within the program share variables.

## 3. Add a button and mutable state

Now add click behavior to the text. Replace `Application` with:

~~~python
import saturn


class Application:
    def __init__(self):
        self.click_count = 0 # a variable shared within the class

    def create_window(self, page: saturn.Page):
        self.page = page

        self.page.title = "Hello Saturn" # set the window title
        self.page.padding = 24 # set the page padding

        # a text control, mounted on the class so other class functions can modify it.
        self.message = saturn.Text(value="Hello, World!", size=28)
        
        # a button, passing the function into on_click (called when the user clicks)
        button = saturn.Button("Click me", on_click=self.handle_click)

        # add the controls to the control tree
        page.add(self.message, button)

    def handle_click(self, event: saturn.ControlEvent):
        self.click_count += 1 # modify the variable

        self.message.value = f"Clicked {self.click_count} times" # modify the text control's content
        self.message.update() # manually update the control


if __name__ == "__main__":
    saturn.run(main=Application().create_window)
~~~

Controls are mutable objects. After an event handler modifies `message.value`, it can call
`message.update()` to request re-layout and redraw of that control. If a single operation modifies several controls,
you can call `page.update()` after the modifications are finished.

Page methods like `page.add()` and `page.remove()` request an update themselves; when directly modifying ordinary properties or
nested control lists, remember to call the owning control's `update()` or `page.update()`.

## 4. Common window settings

Inside the entry callback you can set the title, window size, theme, and page padding:

~~~python
def create_window(self, page: saturn.Page):
    page.title = "Task list"
    page.window.width = 960
    page.window.height = 720
    page.theme_mode = saturn.ThemeMode.DARK
    page.padding = 24
    page.add(saturn.Text("Tasks"))
~~~

Modifying `page.window.width` and `height` sets the size of the native window's outer frame;

`page.width` and `page.height` are the read-only content area sizes. For details see the [window chapter](./window.md).

## What's next

- Study [Page, the Control Tree, and Updates](./book/03-page-control-tree.md) to understand how controls belong to a page.
- Use [Row, Column, and Container](./book/04-layout.md) to arrange content.
- Extend interaction in [Events and State](./book/05-events-state.md).
- Consult the full APIs of [Text](./api/Text.md), [FilledButton](./api/FilledButton.md), and
  [Page](./api/Page.md).
- Run the [hello example](../examples/hello.py) and the
  [control gallery](./gallery.md) in the repository.
