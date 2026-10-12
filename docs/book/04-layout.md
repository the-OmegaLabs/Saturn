# Layout: Row, Column, Stack, and Container

Saturn's layout controls separate "what to show" from "where to put it". `Text`, `Button`, and
`TextField` provide content; `Row`, `Column`, `Stack`, and `Container` decide position, spacing, and decoration.

## Column and Row

`Column` arranges children top to bottom, `Row` left to right. Both accept a `controls`
list or positional arguments, and use `spacing`, alignment, and `expand` to control space.

~~~python
import saturn


def main(page: saturn.Page):
    page.add(
        saturn.Column(
            controls=[
                saturn.Text("Account", size=24),
                saturn.Row(
                    controls=[
                        saturn.TextField(label="Name", expand=True),
                        saturn.Button("Save"),
                    ], 
                    spacing=12, 
                    vertical_alignment=saturn.CrossAxisAlignment.CENTER
                ),
            ], 
            spacing=16
        ),
    )


saturn.run(main)
~~~

A `Column`'s `vertical_alignment` and a `Row`'s `horizontal_alignment` use
`MainAxisAlignment`; alignment along the other direction uses `CrossAxisAlignment`. Common values include
`START`, `CENTER`, `END`, `SPACE_BETWEEN`, and `STRETCH`.

`expand=True` lets a control take the remaining space of its parent layout; `width` and `height` give explicit sizes.
`expand` only has an effect when the parent layout has space to distribute.

## Container

`Container` can wrap `content` and offers `padding`, background, border, border radius, shadow, alignment,
and click events:

~~~python
card = saturn.Container(
    saturn.Text("A surface"),
    padding=24,
    bgcolor=saturn.Colors.SURFACE_CONTAINER,
    border_radius=16,
    width=320,
)
page.add(card)
~~~

`padding` is the space between the content and the boundary; `margin` is the space between the control and its neighbors.
Use `saturn.Padding.only(...)` when the four sides need different values:

~~~python
page.padding = saturn.Padding.only(left=24, top=16, right=12, bottom=16)
~~~

`Card` is a container with surface and shadow semantics, suitable for grouping information; `Container` is better suited
for scenarios that need fine-grained control over decoration and the clickable area.

## Stack

`Stack` lets children overlap; controls added later draw on top. It suits combining a background, content, and floating
actions in one area:

~~~python
background = saturn.Container(
    bgcolor=saturn.Colors.SURFACE_CONTAINER,
    border_radius=24,
    width=420,
    height=240,
)
overlay = saturn.Text("Overlay", left=24, top=24)
page.add(saturn.Stack([background, overlay], width=420, height=240))
~~~

`left`, `top`, `right`, and `bottom` are positioning values relative to the parent container. Controls in a Stack still participate in
hit testing; if an upper control covers a lower one, clicks reach the upper one first.

## Alignment and responsive sizing

The page lays out from the top left by default. Page-level settings can change the root content:

~~~python
page.horizontal_alignment = saturn.CrossAxisAlignment.CENTER
page.vertical_alignment = saturn.MainAxisAlignment.CENTER
~~~

A more common approach is to let a `Column` or `Container` handle alignment and keep the rest of the page
independent. When the window size changes, use `expand`, width constraints, and `ListView` to build content that
stretches; Saturn currently has no full `ResponsiveRow` and breakpoint system.

## Layout troubleshooting

1. Temporarily set `bgcolor` on the outer container to confirm its actual bounds.
2. Set `width`, `height`, or `expand` on controls that need to fill space.
3. Check that the `Row` and `Column` main axis and cross axis match your expectations.
4. Call `update` on the outer control after modifying a nested list.
5. Use the `Software` backend to rule out visual artifacts caused by `GPU` drivers.

## Key points of this chapter

First build a vertical page with `Column`, then add `Row`s where needed; use `Container` to provide
space and decoration, and `Stack` to overlay content. For the full parameters see
[Row](../api/Row.md), [Column](../api/Column.md),
[Container](../api/Container.md), and [Stack](../api/Stack.md).
