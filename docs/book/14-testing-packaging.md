# 测试、诊断与发布

GUI 应用可以把业务逻辑与视图更新分开测试。Saturn 页面依赖窗口和渲染器，
因此简单的单元测试优先测试状态转换，集成测试再启动窗口验证行为和像素。

## 测试业务逻辑

如果点击处理只修改应用状态，可以直接测试它：

~~~python
app = Application()
app.count = 0
app.increment(None)
assert app.count == 1
~~~

较大的应用可以把状态转换放进独立函数，再在控件回调里调用该函数。
这样不需要在每个业务规则测试中都启动 SDL。

## 运行仓库检查

Saturn 仓库包含行为、渲染、兼容性和 Web 检查脚本。通常从仓库根目录运行：

~~~powershell
uv run python tests/page_compatibility_checks.py
uv run python tests/flet_api_checks.py
uv run python tests/subpage_checks.py software
~~~

显卡和桌面窗口相关的检查需要可用的图形环境。提交前只运行与改动相关、
且当前机器可以支持的测试，并记录未运行的 GPU 覆盖。

## 诊断启动和 GPU

先尝试 Software 后端：

~~~powershell
$env:SATURN_BACKEND = "software"
uv run python main.py
~~~

如果问题只在 OpenGL 或 Vulkan 出现，打印 page.renderer.name、
page.renderer.gpu_name，并注册 on_render_failed/on_render_ready。
它们区分“请求的后端”和“实际启动的后端”。

## 检查包的导入位置

~~~powershell
uv run python -c "import saturn; print(saturn.__file__)"
~~~

这个同名包在 PyPI 上容易混淆，因此项目目前建议从 Saturn 仓库 Git URL
安装。项目没有承诺所有桌面平台上的 wheel 都可用。

## 依赖和资源

- 运行库版本通过 uv.lock 锁定；
- web、vulkan、cjk 和 icons 是可选 extras；
- 图片、字体和 GLSL 文件应作为项目资源一起分发；
- 使用基于 __file__ 的路径定位资源，不依赖启动时工作目录；
- 字体和图片的许可证也需要随应用遵守和保留。

构建 Saturn 自身的 wheel 可使用仓库的 tools/build-wheel.ps1。这个脚本为
Saturn 项目的贡献者使用；普通应用开发者应把 Saturn 作为依赖发布自己的包。

## 打包前的兼容性检查

在目标电脑上检查：

1. Python 版本、SDL 窗口和 GPU 驱动；
2. 应用使用的每一个控件参数是否已实现；
3. Software fallback 下的界面是否仍可解释；
4. 字体、图片、GLSL 和数据文件是否已打包；
5. 关闭主窗口、子窗口和后台任务时的生命周期。

Saturn 当前没有官方的跨平台应用打包工具链。alpha 版本发布需要由应用
开发者自己选择并验证打包方案。

## 本章要点

测试业务状态转换可以快速而稳定；渲染、窗口和输入需要在图形环境做集成
检查。发布前固定依赖、明确资源路径，并核对项目实际使用的功能边界。
