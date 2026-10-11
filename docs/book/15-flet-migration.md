# 从 Flet 迁移

Saturn 的 API 设计受到 Flet 的启发，许多入口具有相似名称。迁移时可以复用
部分应用结构，但不能假设所有控件、参数和运行时完全等价。

## 先换入口，再核对行为

熟悉的简化入口通常可以这样写：

~~~python
import saturn


def main(page: saturn.Page):
    page.add(saturn.Text("Hello"))


saturn.run(main)
~~~

Page、Text、Row、Column、Container 和按钮家族等 API 有重叠。逐个检查：

1. 确认该名称出现在 Saturn.__all__；
2. 对照 Saturn 构造签名和参数差异表；
3. 运行实际事件和绘制路径，不能只用“构造成功”判断支持；
4. 搜索平台服务、移动行为、路由、生命周期和未实现属性。

## Page 回调迁移

Saturn 页面事件回调接收事件对象。使用 event.page 取得 Page：

~~~python
def resized(event):
    print(event.width, event.height, event.page.title)


page.on_resize = resized
~~~

如果旧代码把 Page 本身作为参数，需要将访问改成 event.page，或直接使用
PageResizeEvent、KeyboardEvent 上的字段。

## 显式更新

控件通常是可变对象。修改它的属性后调用 update：

~~~python
label.value = "Updated"
label.update()
~~~

页面 controls 列表直接修改后调用 page.update()。大多数常用控件回调支持
单个事件参数或零参数函数。

## Compose 扩展

Material Expressive 相关类型位于 saturn.Compose。新代码可以明确写：

~~~python
page.add(saturn.Compose.FilledButton("Save"))
~~~

标准控件仍从 saturn 导入。Compose 并不代表 Flutter Compose；它是 Saturn
的 Material 3 Expressive 控件分组。

## 运行时差异

- saturn.run 启动本地桌面窗口，默认 OpenGL；Flet 的 web/mobile runtime
  与其不同。
- Saturn 当前主要验证 Windows，平台服务和无障碍覆盖有限。
- Saturn 的 FilePicker 是本地文件/目录/保存对话框，upload 目前不支持。
- ListView 的部分参数存在，但延迟布局和反向滚动等行为需逐项检查。
- saturn.web 是可选的 Canvas/WebSocket runtime，不等价于完整 Flet Web。
- WebGL Shader、浏览器历史、Flet View 栈和完整移动服务不是 Saturn 功能。

## 检查迁移边界

- [Flet mapping](../flet-mapping.md)：概念和公开名称映射；
- [参数对照](../control-parameters-comparison.md)：已实现、缺失和明确不支持的参数；
- [Page 差异](../page-properties-comparison.md)：事件、主题、媒体和生命周期；
- [Compose 验证](../compose.md)：共享控件构造测试和功能缺口。

## 本章要点

先迁移一条小而完整的用户路径，再决定是否迁移整个应用。成功构造不是行为
兼容证据；对 UI 重要的输入、回调、滚动和视觉细节都应在 Saturn 中实测。
