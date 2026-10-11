# 在浏览器中运行

Saturn 的桌面运行时由 saturn.run 启动。可选的 saturn.web 则用 FastAPI、
WebSocket 和浏览器 Canvas 运行受支持的控件子集。Web 是独立部署路径，
不会把原生窗口 API 变成浏览器窗口。

## 安装可选依赖

~~~powershell
uv add "saturn[web] @ git+https://github.com/the-OmegaLabs/Saturn.git"
~~~

若开发的是 Saturn 仓库示例：

~~~powershell
uv sync --extra web
uv run python examples/web_sessions.py
~~~

打开终端输出的本地地址。示例支持独立页面、共享会话、同步文本、命名消息
和滚动列表。

## 创建 FastAPI 应用

~~~python
from saturn.web import create_app


def main(page):
    page.add(saturn.Text("Hello from a browser"))


app = create_app(main)
~~~

create_app 返回标准 FastAPI app，可以像其他 ASGI 应用一样挂载路由。也可用
saturn.web.run(main, host="127.0.0.1", port=8000) 由 Uvicorn 启动。

如果挂载到现有 FastAPI app，需在宿主 lifespan 中接入 Saturn Web child
lifespan。详细写法见 [Web sessions](../web.md#fastapi-integration)。

## 独立视图和共享会话

默认每个浏览器连接得到自己的 Page。想要两个标签共享同一棵控件树时，在
首次修改 Page 之前选定同一个 session：

~~~python
def main(page):
    page.web.session = "shared-counter"
    if not page.web.is_new_session:
        return
    page.add(saturn.Text("Shared page"))
~~~

对共享控件的更新会同步给会话中的其他视图。视口大小、焦点、光标选择、
输入法草稿、滚动位置和动画播放进度仍然是各自浏览器视图的状态。

自定义 session ID 只是状态选择器，不是身份验证。部署时使用 authorize
校验请求；敏感资源需要自己的认证和授权策略。

## Web 的功能边界

Web 客户端使用 Canvas 2D。基础支持包括文字、按钮、输入、布局、图像、
ListView、AlertDialog 和 SnackBar。原生文件对话框、子窗口、GPU Shader、
完整的 TextField 装饰与所有桌面事件并不适用。

页面保持在服务进程内存中，服务重启会清除会话。当前注册表是单进程内存
状态，生产部署使用一个 worker，或自行提供一致的外部会话架构。

## 本章要点

saturn.web 是共享控件模型上的另一个 renderer 和会话层。先阅读
[Web 会话指南](../web.md)了解事件顺序、授权、生命周期与覆盖情况，再部署
给真实用户。
