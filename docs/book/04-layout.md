# 布局：Row、Column、Stack 和 Container

Saturn 的布局控件把“显示什么”和“放在哪里”分开。Text、Button 和
TextField 提供内容；Row、Column、Stack 和 Container 决定位置、间距与装饰。

## Column 和 Row

Column 从上到下排列子控件，Row 从左到右排列。两者都可以接收 controls
列表或位置参数，并通过 spacing、对齐和 expand 控制空间。

~~~python
import saturn


def main(page: saturn.Page):
    page.add(
        saturn.Column([
            saturn.Text("Account", size=24),
            saturn.Row([
                saturn.TextField(label="Name", expand=True),
                saturn.FilledButton("Save"),
            ], spacing=12, vertical_alignment=saturn.CrossAxisAlignment.CENTER),
        ], spacing=16),
    )


saturn.run(main)
~~~

Column 的 vertical_alignment 和 Row 的 horizontal_alignment 使用
MainAxisAlignment；反方向的对齐使用 CrossAxisAlignment。常用值包括
START、CENTER、END、SPACE_BETWEEN 和 STRETCH。

expand=True 让控件占用父布局的剩余空间；width 和 height 给出明确尺寸。
只有父布局有可分配空间时，expand 才能体现效果。

## Container

Container 可以包裹 content，并提供 padding、背景、边框、圆角、阴影、对齐
和点击事件：

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

padding 是内容与边界之间的空间；margin 是控件与相邻控件之间的空间。
需要四边不同的值时使用 saturn.Padding.only(...)：

~~~python
page.padding = saturn.Padding.only(left=24, top=16, right=12, bottom=16)
~~~

Card 是带有表面和阴影语义的容器，适合信息分组；Container 更适合需要
精细控制装饰和点击区域的场景。

## Stack

Stack 让子控件重叠，后加入的控件绘制在上面。它适合把背景、内容和浮动
操作组合在一个区域：

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

left、top、right、bottom 是相对父容器的定位值。Stack 中的控件仍然参加
命中测试；如果上层控件覆盖了下层，点击会先到达上层。

## 对齐和响应式尺寸

页面默认从左上开始布局。页面级设置可以改变根内容：

~~~python
page.horizontal_alignment = saturn.CrossAxisAlignment.CENTER
page.vertical_alignment = saturn.MainAxisAlignment.CENTER
~~~

更常见的做法是让一个 Column 或 Container 负责对齐，让页面的其他区域
保持独立。窗口尺寸变化时，使用 expand、宽度约束和 ListView 构建可以
伸缩的内容；Saturn 目前没有 Flet 的完整 ResponsiveRow 和断点系统。

## 布局排查

1. 给外层容器临时设置 bgcolor，确认它的实际边界。
2. 给需要填满空间的控件设置 width、height 或 expand。
3. 检查 Row 和 Column 的主轴、交叉轴是否符合预期。
4. 修改嵌套列表后调用外层控件的 update。
5. 用 Software 后端排除 GPU 驱动造成的视觉干扰。

## 本章要点

先用 Column 建立垂直页面，再在需要的地方加入 Row；用 Container 提供
空间和装饰，用 Stack 叠加内容。完整参数见
[Row](../api/Row.md)、[Column](../api/Column.md)、
[Container](../api/Container.md) 和 [Stack](../api/Stack.md)。
