# 欢迎使用 Saturn

Saturn 是一个现代化、轻量级、支持 GPU 加速的 Python 桌面 UI 框架。

更多介绍，参阅 [the-OmegaLabs/Saturn.git](https://github.com/the-OmegaLabs/Saturn) 。

~~~python
import saturn

def main(page: saturn.Page):
    page.add(saturn.Text("Hello, Saturn"))

saturn.run(main)
~~~

这是 Saturn 创建一个窗口的最小实现，效果如下：

![00-hello.png](./assets/00-hello.png)

这段代码使用了 `saturn.run` 创建一个窗口，向 `main` 函数传入一个 `saturn.Page`。`main` 可以是普通函数、
绑定方法或异步函数。

## 四个核心概念

### 根 (`saturn.Page`)

`Page` 代表一个窗口中的应用页面。它拥有顶层 `controls`、主题、字体、对话框、
服务和事件处理器。可以用 `add`、`insert`、`remove`、`clean` 管理直接子控件。

`page.controls` 是一个 `Page` 的控件列表。可以用 `add`、`insert`、`remove`、`clean` 管理直接子控件。

`page.window` 管理原生窗口。

`page.renderer` 管理当前渲染器，以及渲染器设置。

### 节点 (`saturn.Control`)

Text、Button、Row、Column、Container、TextField 等都是 Control。一个控件
可以有子控件：Row 和 Column 通过 controls 保存子项，Container 通过 content
包裹一个子项。每个控件最多属于一棵控件树。

### 自动控件更新

无需手动管理空间状态。修改 value、checked 或子控件 controls 后，调用控件
的 control.update() 或页面的 page.update()，让 Saturn 重新同步、布局并绘制。
add 和 remove 已经会请求更新；一次操作修改多个属性时，通常最后统一更新一次。

如果你并不想自动更新控件，可以修改 `page.auto_update` 为 False。

### Renderer 负责绘制

Saturn 支持 Software、OpenGL 和实验性的 Vulkan 后端。默认运行
saturn.run(main) 使用 OpenGL；应用逻辑仍使用相同的控件 API。GPU 初始化
失败时可以回退到 Software，实际后端可从 page.renderer.name 读取。

## Saturn 与 Flet 的关系

Saturn 使用了许多熟悉的名字：Page、Text、Button、Row、Column、TextField
和 FilePicker。这让已有 Flet 经验的开发者容易开始，但它们不是同一个实现。
Saturn 当前主要面向本地桌面，Web 运行时是可选扩展；Flet 中的移动、平台服务、
完整导航和所有构造参数不会自动出现在 Saturn 中。

迁移或对照时，先看[功能映射](../flet-mapping.md)，再看
[参数差异表](../control-parameters-comparison.md)。本书讲常用的 Saturn
开发路径；API 页面记录当前版本实际支持的签名。

## 什么时候选择 Saturn

Saturn 适合：

- 需要 Python 本地桌面窗口、输入、布局和 Material 风格控件的工具；
- 希望 UI 状态和事件在本地进程内运行；
- 需要原生子窗口、渲染器选择或 GPU 着色器的应用；
- 想从一套小而熟悉的 API 开始，再按需要使用 Expressive 和 Web 扩展。

如果应用依赖 Saturn 尚未实现的移动组件、服务或参数，应先确认替代方案，
或继续使用 Flet。

## 本章要点

Saturn 应用从 saturn.run 开始；Page 是根，Control 组成树，事件修改状态，
update 请求绘制。下一章准备开发环境，然后用 Application 类建立项目脚手架。
