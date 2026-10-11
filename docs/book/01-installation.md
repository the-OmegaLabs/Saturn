# 安装与运行

## 系统要求

- Python 3.10 或更高版本；
- 一个能运行 SDL 的桌面环境；
- 使用 OpenGL 时需要可用的 OpenGL 驱动；
- 使用 Vulkan 时需要 Vulkan 驱动、可选的 vulkan Python 包和相应工具链。

Saturn 当前主要在 Windows 上开发和验证。其他平台的代码路径正在建设中；
即使能启动，也应先验证窗口、输入和字体行为。

## 从源码运行 Saturn

这是贡献者和想运行仓库示例的方式：

~~~powershell
git clone https://github.com/the-OmegaLabs/Saturn.git
cd Saturn
uv sync
uv run python examples/hello.py
~~~

也可以在已激活的虚拟环境中安装可编辑版本：

~~~powershell
python -m pip install -e .
~~~

uv sync 会安装 pyproject.toml 中的默认示例组。浏览器示例需要 web 可选依赖：

~~~powershell
uv sync --extra web
~~~

Vulkan 和额外字体、图标包是独立的可选项：

~~~powershell
uv sync --extra vulkan
uv sync --extra cjk --extra icons
~~~

## 在新项目中使用

Saturn 的项目仓库地址是
https://github.com/the-OmegaLabs/Saturn。安装时建议显式使用 Git URL：

~~~powershell
uv init hello-saturn
cd hello-saturn
uv add "saturn @ git+https://github.com/the-OmegaLabs/Saturn.git"
~~~

PyPI 上有另一个同名的 Saturn 时间日期库。直接执行 uv add saturn 或
pip install saturn 可能得到错误的包；如果导入后找不到 Page、Text 或 run，
先检查安装来源。

## 验证导入

~~~powershell
uv run python -c "import saturn; print(saturn.__file__)"
~~~

输出应指向当前虚拟环境或仓库中的 saturn/__init__.py。然后运行
uv run python examples/hello.py；如果窗口出现，基础安装就完成了。

## 选择渲染后端

默认入口选择 OpenGL：

~~~python
saturn.run(main)
~~~

需要诊断或没有可用 GPU 时，可以选择软件后端：

~~~python
saturn.run(main, backend=saturn.Renderer.SOFTWARE)
~~~

Vulkan 是实验性后端：

~~~python
saturn.run(main, backend=saturn.Renderer.VULKAN)
~~~

省略 backend 时可以通过环境变量选择：

~~~powershell
$env:SATURN_BACKEND = "software"
uv run python main.py
~~~

如果 GPU 初始化失败，OpenGL 和 Vulkan 会打印回退提示并尝试使用软件渲染。
应用可以通过 page.on_render_failed 和 page.on_render_ready 记录这次恢复。

## 下一步

安装完成后，按[项目脚手架](../getting-started.md)写入 main.py。不要先学习
所有控件；先让一个 Text 和一个 Button 跑起来，再按需要查 API。
