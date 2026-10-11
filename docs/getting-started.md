# 项目脚手架：第一个窗口

[← 手册目录](./README.md) · [下一章：页面与控件树](./book/03-page-control-tree.md)

本章会建立一个很小的 Saturn 应用。例子采用 Application 类保存界面对象，
并把 create_window 作为 saturn.run 的入口回调。

## 1. 创建项目

Saturn 当前没有发布到 PyPI 上的这个项目包名；PyPI 上另有一个名为 Saturn
的时间日期库。创建新项目时，从 Saturn 仓库安装，避免执行 uv add saturn
或 pip install saturn 后装到同名的其他包。

使用 uv 创建 Python 项目，并把 Saturn 仓库作为依赖：

~~~powershell
uv init hello-saturn
cd hello-saturn
uv add "saturn @ git+https://github.com/the-OmegaLabs/Saturn.git"
~~~

项目目录可以保持很简单：

~~~text
hello-saturn/
├── main.py
├── pyproject.toml
└── uv.lock
~~~

uv 会维护依赖和锁文件。提交 uv.lock 可以让其他开发者安装同一组版本。
开发 Saturn 本身时，则克隆仓库并运行 uv sync；这会安装仓库示例所需的
依赖。

## 2. 写入最小应用

在 main.py 中写入：

~~~python
import saturn


class Application:
    def __init__(self):
        pass

    def create_window(self, page: saturn.Page):
        self.page = page

        hello = saturn.Text(value="Hello, World!")

        self.page.add(hello)


if __name__ == "__main__":
    saturn.run(main=Application().create_window)
~~~

运行它：

~~~powershell
uv run python main.py
~~~

窗口中会出现 “Hello, World!”。这几行建立了 Saturn 应用的基本结构：

- Application 是你自己的应用对象，可以在其中保存控件引用和应用状态。
- create_window 是入口回调；saturn.run 启动后会将新建的 Page 传给它。
- Page 是当前窗口的根控件，使用 page.add() 将控件加入可见的界面。
- Text 是一个显示文字的控件。

注意 saturn.run(main=Application().create_window) 最后没有括号。带括号会
立刻调用 create_window，但此时还没有 Page 可以传入。绑定方法会保留
Application 实例，运行期间可以访问 self。

## 3. 添加按钮和可变状态

现在给文字添加点击行为。把 Application 替换为：

~~~python
import saturn


class Application:
    def __init__(self):
        self.click_count = 0

    def create_window(self, page: saturn.Page):
        self.page = page
        page.title = "Hello Saturn"
        page.padding = 24

        self.message = saturn.Text(value="Hello, World!", size=28)
        button = saturn.FilledButton("Click me", on_click=self.handle_click)

        page.add(self.message, button)

    def handle_click(self, event: saturn.ControlEvent):
        self.click_count += 1
        self.message.value = f"Clicked {self.click_count} times"
        self.message.update()


if __name__ == "__main__":
    saturn.run(main=Application().create_window)
~~~

控件是可变对象。事件处理器修改 message.value 后，调用
message.update() 请求重新布局和绘制该控件。若一次操作修改了多个控件，
可以在修改结束后调用 page.update()。

page.add() 和 page.remove() 等页面方法会自行请求更新；直接修改普通属性或
嵌套控件列表时，记得调用所属控件的 update() 或 page.update()。

## 4. 常用窗口设置

入口回调中可以设置标题、窗口大小、主题和页面边距：

~~~python
def create_window(self, page: saturn.Page):
    page.title = "Task list"
    page.window.width = 960
    page.window.height = 720
    page.theme_mode = saturn.ThemeMode.DARK
    page.padding = 24
    page.add(saturn.Text("Tasks"))
~~~

page.window.width 和 height 设置原生窗口外框的尺寸；page.width 与
page.height 是只读的内容区域尺寸。详情见[窗口章节](./window.md)。

## 接下来

- 学习 [Page、控件树与更新](./book/03-page-control-tree.md)，理解控件如何归属页面。
- 使用 [Row、Column 和 Container](./book/04-layout.md) 排列内容。
- 在 [事件与状态](./book/05-events-state.md) 中扩展交互。
- 查阅 [Text](./api/Text.md)、[FilledButton](./api/FilledButton.md) 和
  [Page](./api/Page.md) 的完整 API。
- 在仓库中运行 [hello 示例](../examples/hello.py) 和
  [控件画廊](./gallery.md)。
