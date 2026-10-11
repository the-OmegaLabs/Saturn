# 导航与原生子窗口

Saturn 提供共享 route 字符串和原生 Subpage 窗口。route 负责报告当前导航
状态；Subpage 则创建一个真正独立的操作系统窗口。

## 处理应用 route

~~~python
def route_changed(event: saturn.RouteChangeEvent):
    print("route:", event.route)
    if event.route == "/settings":
        show_settings()
    elif event.route == "/":
        show_home()


page.on_route_change = route_changed
page.go("/settings")
~~~

route = value 和 go(value) 都会通知注册了 on_route_change 的 Page。一次
应用中的主页面和子页面共享 route。Saturn 不会自动创建、销毁或切换一组
Flet View；回调需要自己决定控件或窗口如何变化。

## 打开设置窗口

~~~python
def settings(child: saturn.Subpage):
    child.window.width = 420
    child.window.height = 360
    child.add(
        saturn.Text("Preferences", size=24),
        saturn.Switch(label="Notifications", value=True),
        saturn.FilledButton("Close", on_click=lambda e: child.close()),
    )


def open_settings(event):
    page.open_subpage(settings, title="Preferences")
~~~

page.open_subpage() 立即返回 Subpage。窗口在 UI 线程异步创建；传入的
settings(child) 回调会在原生窗口建立后运行。返回的 Subpage 也是 Page，
可以添加控件、设置 theme、处理事件和调用 update。

## 窗口生命周期

- show() 与 hide() 显示或隐藏同一个窗口，不销毁控件；
- close() 请求关闭，并遵守 prevent_close 与 window.on_event；
- destroy() 强制关闭并销毁子孙窗口；
- child.closed 检查窗口是否已关闭；关闭的 Subpage 不能重新打开；
- 关闭父窗口会关闭它的所有子窗口，关闭子窗口不会关闭父窗口。

可以保存子窗口引用，避免重复创建：

~~~python
children = {}


def open_settings(event):
    child = children.get("settings")
    if child is None or child.closed:
        child = page.open_subpage(settings, title="Preferences")
        children["settings"] = child
    else:
        child.show()
        child.to_front()
~~~

## 原生窗口属性

窗口尺寸通过 page.window 设置。width 和 height 表示包含原生边框的外框尺寸；
page.width 与 page.height 表示只读的内容区域。位置、最小尺寸、最大尺寸、
标题栏、可见状态和关闭拦截都属于 Window API。

子窗口可通过 anchor、offset 和 follow_parent 相对父窗口定位。modal=True
会阻止父窗口接受输入。具体可用能力取决于平台；当前主要在 Windows 上验证。

## 本章要点

route 只通知应用状态变化，应用决定显示什么；Subpage 是拥有独立 Page 和
窗口配置的原生子窗口。查看[子窗口完整指南](../subpages.md)和
[Window API](../window.md)了解平台差异。
