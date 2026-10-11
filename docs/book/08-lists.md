# 列表、滚动与性能

ListView 用于显示纵向或横向滚动内容。它拥有固定视口，并在滚动时处理
内部子控件的布局和裁剪。

## 建立列表

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

ListView 可用 horizontal=True 改为横向滚动。scroll 可选 AUTO、ALWAYS、
HIDDEN 或 NONE；具体滚动方式以当前桌面实现为准。

## 追加内容

~~~python
def add_row(event):
    list_view.controls.append(saturn.Text("New row"))
    list_view.update()
~~~

列表的直接子项发生变化后，更新 ListView。若 auto_scroll=True，内容变化后
会滚到末尾。也可以用 scroll_to(offset=...) 或 delta=... 控制位置。

## 长列表

如果每一行高度固定，给 ListView 设置 item_extent，或给每个子项明确 height：

~~~python
list_view = saturn.ListView(
    [saturn.Text(f"Record {index}") for index in range(5000)],
    item_extent=40,
    spacing=2,
    height=600,
)
~~~

已知行高时 Saturn 可以只摆放视口附近的控件；控件对象仍然存在于 Python
列表中，因此这不是一个会按需创建业务对象的分页数据源。高度不固定的行
仍需测量，窗口宽度变化也可能触发行高重算。

可用 first_item_prototype 或 prototype_item 复用原型尺寸，但只有当行高
一致时才适用。快速跳转到尚未测量的可变高度内容时，布局可能需要先完成测量。

## 滚动事件

~~~python
def scrolled(event):
    print("offset:", event.data)


list_view.on_scroll = scrolled
~~~

事件会按 scroll_interval 合并高频通知。若只需要视觉滚动效果，不要在每个
滚动事件中重建整棵列表；只更新确实变化的内容。

## 性能建议

- 给同高度的大列表设置 item_extent。
- 不要在滚动回调里同步执行磁盘、网络或长时间计算。
- 控件样式尽量复用主题，避免为每一行创建重复的复杂阴影。
- 一次批量修改多个行后，调用一次 list_view.update()。
- 若列表数据来自服务端，将数据分页逻辑保留在应用层；ListView 不会替你
  请求更多数据。

## 本章要点

ListView 管视口、滚动和可见布局；应用仍然拥有数据和控件实例。更多细节见
[ListView API](../api/ListView.md) 和[渲染性能说明](../rendering.md)。
