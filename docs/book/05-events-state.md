# 事件与状态

Saturn 的交互是“事件回调修改状态，更新控件树”。控件不要求你使用某种
状态管理库；一个 Application 对象、闭包或普通数据类都可以保存状态。

## 处理点击

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

on_click 回调通常接收一个 ControlEvent。event.control 是按钮本身，
event.page 是 Page，event.data 通常为 None。回调也可以定义为无参数函数：

~~~python
saturn.Button("Close", on_click=lambda: page.window.close())
~~~

Saturn 会根据函数签名决定是否传入事件。

## 常用事件数据

| 控件 | 事件 | event.data |
| --- | --- | --- |
| Button、Container | on_click | 通常为 None |
| TextField | on_change、on_submit | 当前字符串 |
| Checkbox、Switch、Radio | on_change | "true"、"false"，Checkbox 三态也可能是 "null" |
| Slider | on_change | 当前数值 |
| Dropdown | on_select | 选项 key |
| ListView | on_scroll | 当前滚动偏移量 |

读取控件属性通常比解析 event.data 更直观：

~~~python
def changed(event):
    print(field.value, checkbox.value, slider.value)
~~~

## 同步和异步处理器

事件处理器可以是同步函数、async def，或返回 awaitable 的普通函数。异步
处理器运行在应用的异步循环中：

~~~python
import asyncio


async def save(event):
    await asyncio.sleep(0.2)
    status.value = "Saved"
    status.update()
~~~

耗时的同步工作不要直接阻塞回调。用 page.run_task 将工作排入应用上下文，
或自己使用线程/进程，再把结果交回页面。不要在后台线程直接操作 SDL 或
GPU 对象。

## 一个可维护的状态边界

把业务状态放在 Application，把视图控件作为属性保存；事件方法只做三件事：
读取状态、改变状态、更新受影响的控件。

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

如果一次事件影响多个区域，使用 page.update()：

~~~python
self.summary.value = f"{len(self.tasks)} tasks"
self.items.controls = [saturn.Text(task) for task in self.tasks]
self.page.update()
~~~

## 页面事件

~~~python
def resized(event: saturn.PageResizeEvent):
    print(event.width, event.height, event.page.title)


def keyboard(event: saturn.KeyboardEvent):
    if event.ctrl and event.key == "S":
        save_document()


page.on_resize = resized
page.on_keyboard_event = keyboard
~~~

on_resize、on_keyboard_event 和 on_platform_brightness_change 接收事件对象，
而不是旧版本中直接传入 Page。handler 可以是单个回调，也可以是回调列表。

## 本章要点

事件对象告诉你发生了什么，Application 状态告诉你应用当前是什么，控件树
负责显示结果。明确这三个边界后，应用规模变大也不会把业务逻辑塞进布局代码。
