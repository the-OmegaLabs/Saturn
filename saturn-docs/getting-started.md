# 五分钟上手

[← 文档首页](./README.md) · [API 索引](./api/README.md)

## 安装与运行

需要 Python 3.10 或更新版本。当前主要在 Windows 上开发和测试。

```powershell
uv sync
uv run python examples/hello.py
```

## 第一个窗口

```python
import saturn


def main(page: saturn.Page):
    page.title = "Hello Saturn"
    page.theme_mode = saturn.ThemeMode.DARK
    page.padding = 24

    message = saturn.Text("你好，Saturn", size=24)

    def clicked(event: saturn.ControlEvent):
        message.value = "按钮已点击"
        message.update()

    page.add(message, saturn.FilledButton("点击我", on_click=clicked))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE)
```

`saturn.run()` 创建窗口并把 [`Page`](./api/Page.md) 交给 `main`。通过 `page.add()` 加入控件；修改控件后调用 `control.update()` 或 `page.update()` 请求重绘。回调中的 `event.control` 指向触发事件的控件。

## 切换绘制后端

```python
saturn.run(main, backend=saturn.Render.OPENGL)
```

也可在省略 `backend` 时设置环境变量 `SATURN_BACKEND`。`Render.VULKAN` 已导出；具体可用性取决于本机驱动与当前实现。

## 接着浏览

- [截图画廊](./gallery.md) 展示主要控件的视觉效果。
- [API 索引](./api/README.md) 按组件类别查参数和方法。
- [Flet 对照与范围](./flet-mapping.md) 帮助迁移 Flet 桌面界面。
