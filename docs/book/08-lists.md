# Lists, Scrolling, and Performance

ListView is used to display vertically or horizontally scrolling content. It owns a fixed viewport and handles
internal child layout and clipping while scrolling.

## Building a list

~~~python
rows = [
    saturn.Container(
        saturn.Text(f"Item {index}"),
        padding=12,
        bgcolor=saturn.Colors.SURFACE_CONTAINER,
        border_radius=8,
    )
    for index in range(20)
]

list_view = saturn.ListView(
    controls=rows,
    spacing=6,
    width=360,
    height=480,
)
page.add(list_view)
~~~

ListView can scroll horizontally with horizontal=True. `scroll` can be AUTO, ALWAYS,
HIDDEN, or NONE; the exact scrolling behavior depends on the current desktop implementation.

## Appending content

~~~python
def add_row(event):
    list_view.controls.append(saturn.Text("New row"))
    list_view.update()
~~~

Update the ListView after its direct children change. If auto_scroll=True, the view scrolls
to the end when content changes. You can also control the position with scroll_to(offset=...) or delta=....

## Long lists

If every row has a fixed height, set item_extent on the ListView, or give each child an explicit height:

~~~python
list_view = saturn.ListView(
    [saturn.Text(f"Record {index}") for index in range(5000)],
    item_extent=40,
    spacing=2,
    height=600,
)
~~~

When row heights are known, Saturn can lay out only the controls near the viewport; the control objects still exist in the Python
list, so this is not a paged data source that creates business objects on demand. Rows with non-fixed heights
still need measuring, and window width changes may trigger row height recomputation.

first_item_prototype or prototype_item can reuse a prototype size, but this only applies when row heights
are consistent. When jumping quickly to variable-height content that hasn't been measured yet, layout may need to complete measurement first.

## Scroll events

~~~python
def scrolled(event):
    print("offset:", event.data)


list_view.on_scroll = scrolled
~~~

Events merge high-frequency notifications according to scroll_interval. If you only need the visual scrolling effect, don't rebuild the entire list on every
scroll event; update only what actually changed.

## Performance tips

- Set item_extent for large lists with uniform row heights.
- Don't perform disk, network, or long computations synchronously in scroll callbacks.
- Reuse theme styles for control styling as much as possible; avoid creating duplicate complex shadows for every row.
- After batch-modifying many rows, call list_view.update() once.
- If list data comes from a server, keep the data pagination logic in the application layer; ListView will not
  request more data for you.

## Key points of this chapter

ListView manages the viewport, scrolling, and visible layout; the application still owns the data and control instances. For more details see
the [ListView API](../api/ListView.md) and the [rendering performance notes](../rendering.md).
