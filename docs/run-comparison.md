# Saturn.run 与 Flet.run

核验日期：2026-09-27。Flet 部分依据本地安装的 **Flet 1.0.1** 的 `flet/app.py` 实际签名和源码；Saturn 部分依据本仓库实现。

## 窗口尺寸

两者的 `run()` 都不接受 `width`、`height`。尺寸在入口函数中通过 `page.window` 设置：

```python
import saturn as ft


def main(page: ft.Page):
    page.window.width = 960
    page.window.height = 800
    page.title = "My app"
    page.add(ft.Text("Hello"))


ft.run(main)
```

换成 `import flet as ft` 时，窗口配置写法相同。`page.window.width/height` 表示原生窗口外框尺寸；`page.width/height` 表示内容区尺寸。Saturn 未设置尺寸时使用 800×600 的初始窗口。

## 入口差异

Saturn 的实际签名：

```python
saturn.run(main, *, backend=None, title="saturn")
```

| 项目 | Saturn | Flet 1.0.1 |
| --- | --- | --- |
| `main(page)` | 支持普通函数、绑定方法和协程 | 支持普通函数、绑定方法和协程 |
| `width`、`height` | 不接受，通过 `page.window` 设置 | 不接受，通过 `page.window` 设置 |
| `backend` | 选择 OpenGL、Vulkan 或软件渲染；默认 OpenGL，可用 `SATURN_BACKEND` 覆盖 | 无此参数 |
| `title` | 可设置初始标题，也可在入口中设置 `page.title` | 无此启动参数，通过 `page.title` 设置 |
| `before_main` | 未实现，传入会报 `TypeError` | 在创建 Page 后、运行 main 前调用 |
| `name`、`host`、`port`、`view` | 未实现，传入会报 `TypeError` | 配置应用名称、服务地址及呈现模式 |
| `assets_dir`、`upload_dir` | 未实现，图片等资源使用实际文件路径 | 配置资源与上传目录 |
| `web_renderer`、`route_url_strategy`、`no_cdn` | 未实现 | 配置 Web 渲染与路由 |
| `export_asgi_app` | 未实现 | 可返回 FastAPI ASGI 应用 |
| 返回值 | 窗口关闭后返回 `App` | 普通运行返回 `None`；ASGI 导出模式返回应用 |
| 执行方式 | SDL 窗口事件循环；普通回调在线程执行，协程在后台 asyncio 循环执行 | 根据呈现模式启动 socket/Web transport，普通 `run()` 使用 asyncio 启动流程 |

Saturn 移除了原来静默忽略任意启动关键字的 `**_flet_ignored`。参数未实现时会直接报错，迁移时按上表调整。

绑定方法需要传实例方法，例如 `ft.run(Application().create_window)`。

[返回文档首页](./README.md) · [run API](./api/run.md)
