# Page、控件树与更新

Saturn 的 UI 是一棵树。Page 是根节点，controls 是直接子节点，Row、
Column、Stack、ListView 等容器继续拥有自己的子节点。

~~~python
import saturn


def main(page: saturn.Page):
    title = saturn.Text("Today")
    actions = saturn.Row([
        saturn.Button("Refresh"),
        saturn.Button("Settings"),
    ], spacing=8)
    page.add(title, actions)


saturn.run(main)
~~~

这段代码建立的控件树如下：

~~~text
Page
├── Text("Today")
└── Row
    ├── Button("Refresh")
    └── Button("Settings")
~~~

## 添加和删除

页面方法操作顶层控件：

~~~python
page.add(saturn.Text("one"), saturn.Text("two"))
page.insert(0, saturn.Text("first"))
page.remove_at(1)
page.clean()
~~~

容器的 controls 列表也可以直接改变，但之后要更新拥有它的控件：

~~~python
items = saturn.Column()
items.controls.append(saturn.Text("new item"))
items.update()
~~~

一个 Control 不能同时出现在页面的两个位置。把同一个实例重复放入树会
抛出 ValueError；要重复显示内容，请创建多个控件实例。

## 修改属性

控件属性是可变的：

~~~python
message = saturn.Text("Waiting")
page.add(message)

message.value = "Ready"
message.color = saturn.Colors.PRIMARY
message.update()
~~~

update 会重新协调控件归属，并在需要时重新布局。只改变不影响几何尺寸的
外观时，repaint() 可以只请求绘制；普通应用使用 update() 更简单。

`page.auto_update` 默认为 `True`。设为 `False` 后，控件的隐式更新、输入
状态变化和动画帧不会自动请求新帧；控件树和状态仍会在内存中同步。可以手动调用
`page.update()` 或 `page.repaint()` 强制显示最新状态，重新设为 `True` 时
也会立即刷新一次：

~~~python
page.auto_update = False
message.value = "Updated in memory"
page.update()
page.auto_update = True
~~~

一次事件通常修改多个对象，最后统一更新一次：

~~~python
def reset(event):
    name.value = ""
    status.value = "Reset"
    page.update()
~~~

事件回调可以接收零个参数，也可以接收一个事件对象。事件的 event.control
是触发它的控件，event.page 是所属页面。

## 对话框和覆盖层

AlertDialog 和 SnackBar 不放在普通 controls 中，而是由 page.show_dialog()
放到 overlay：

~~~python
def save(event):
    page.show_dialog(saturn.SnackBar("Saved"))


def close_dialog(event):
    page.pop_dialog()
~~~

可见的 AlertDialog 会限制键盘焦点；SnackBar 是非阻塞提示。要自己控制
生命周期，可以保存 dialog 引用并调用 page.pop_dialog(dialog)。

## 所有权和线程

控件附着到 Page 后，control.page 指向它的页面，control.parent 指向父控件。
不要把一个已附着的控件跨页面复用。

页面回调由 Saturn 的工作线程或应用异步循环调度。回调中修改控件后调用
update 是安全的；直接操作 SDL、窗口句柄或 GPU renderer 必须回到 UI 线程。
需要把工作排入应用上下文时，可以使用 page.run_task(handler, ...)。

## 本章要点

先构建控件树，再在事件中修改状态，最后请求更新。接下来用 Row、Column、
Container 和 Stack 把这棵树排成可读的界面。
