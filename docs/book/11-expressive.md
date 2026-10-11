# Material 3 Expressive

Saturn.Compose 将 Material 3 Expressive 控件集中到一个命名空间。标准控件
仍然可以从 saturn 顶层导入；新应用可以用 Compose 让意图更明显。

## 使用 Compose

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

Compose.Theme 是 MaterialExpressiveTheme。Compose.Button 和
Compose.IconButton 启用尺寸、形状和状态变化；Compose 下的 FilledButton、
OutlinedButton、TextButton 等变体默认使用 Expressive 的 small 尺寸。

## 可用控件

Expressive 组包括：

- Button、IconButton、SplitButton 和 ButtonGroup；
- ToggleButton 及其 Elevated、FilledTonal、Outlined 变体；
- Small、Medium、Large、Extended FloatingActionButton；
- ListItem、LoadingIndicator 和线性/圆形 WavyProgressIndicator；
- FloatingToolbar 和 FloatingActionButtonMenu。

它们仍遵循普通 Saturn 控件的树、事件和 update 规则：

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

LoadingIndicator 和波浪进度控件会请求动画帧；不可见控件和 Software 后端
不会执行完整的 GPU 片段动画。

## 与标准控件混用

Compose 控件和普通 Text、TextField、ListView 可以放在同一棵树中：

~~~python
page.add(
    saturn.Text("Standard content"),
    saturn.Compose.FilledButton("Expressive action"),
)
~~~

标准顶层的 Expressive 别名仍保留，用于迁移旧代码。新代码使用
saturn.Compose.* 更容易区分标准 API 和扩展 API。

## 本章要点

Compose 是 Saturn 的命名空间，不是另一个运行时。先掌握标准控件和页面
更新，再用 Expressive 提升状态动画与 Material 视觉表达。更多示例见
[Expressive 指南](../expressive.md)。
