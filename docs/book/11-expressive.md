# Material 3 Expressive

Saturn.Compose gathers the Material 3 Expressive controls into one namespace. Standard controls
can still be imported from the saturn top level; new applications can use Compose to make the intent clearer.

## Using Compose

~~~python
import saturn


def main(page: saturn.Page):
    page.theme = saturn.Compose.Theme()
    page.add(
        saturn.Compose.Button("Expressive action"),
        saturn.Compose.LoadingIndicator(contained=True),
        saturn.Compose.WavyProgressIndicator(value=0.6),
    )


saturn.run(main, backend=saturn.Renderer.OPENGL)
~~~

Compose.Theme is MaterialExpressiveTheme. Compose.Button and
Compose.IconButton enable size, shape, and state variations; variants such as FilledButton,
OutlinedButton, and TextButton under Compose use the Expressive small size by default.

## Available controls

The Expressive group includes:

- Button, IconButton, SplitButton, and ButtonGroup;
- ToggleButton and its Elevated, FilledTonal, and Outlined variants;
- Small, Medium, Large, and Extended FloatingActionButton;
- ListItem, LoadingIndicator, and the linear/circular WavyProgressIndicator;
- FloatingToolbar and FloatingActionButtonMenu.

They still follow the ordinary Saturn control rules for tree, events, and update:

~~~python
menu = saturn.Compose.FloatingActionButtonMenu([
    saturn.Compose.FloatingActionButtonMenuItem(
        "Create",
        icon=saturn.Icons.ADD,
        on_click=lambda e: create_item(),
    ),
])
page.add(menu)
~~~

LoadingIndicator and the wavy progress controls request animation frames; invisible controls and the Software backend
do not run the full GPU fragment animations.

## Mixing with standard controls

Compose controls and ordinary Text, TextField, and ListView can live in the same tree:

~~~python
page.add(
    saturn.Text("Standard content"),
    saturn.Compose.FilledButton("Expressive action"),
)
~~~

The standard top-level Expressive aliases are kept for migrating old code. New code using
saturn.Compose.* makes it easier to distinguish the standard API from the extension API.

## Key points of this chapter

Compose is Saturn's namespace, not another runtime. Master the standard controls and page
updates first, then use Expressive to elevate state animations and Material visual expression. For more examples see the
[Expressive guide](../expressive.md).
