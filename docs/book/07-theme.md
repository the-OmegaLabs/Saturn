# 主题、颜色与字体

Page 统一管理颜色方案、明暗模式和字体别名。优先从主题开始，再对少数
控件覆盖颜色，避免每个按钮都写一组重复参数。

## 明暗主题

~~~python
page.theme_mode = saturn.ThemeMode.DARK
page.theme = saturn.Theme(font_family="Inter", color_scheme_seed="#6750A4")
page.dark_theme = saturn.Theme(font_family="Inter", color_scheme_seed="#6750A4")
~~~

ThemeMode 有 LIGHT、DARK 和 SYSTEM。显式指定 LIGHT 或 DARK 时更容易在
不同电脑上得到一致结果；SYSTEM 会跟随平台当前的应用明暗偏好。

color_scheme_seed 只选择 Saturn 已支持的颜色角色方案，不是完整的 Material
动态配色引擎。颜色令牌可从 saturn.Colors 使用，例如 PRIMARY、
ON_SURFACE、SURFACE_CONTAINER 和 ERROR。控件级的 color、bgcolor 等参数
仍可覆盖主题。

## 本地字体

在 Page 注册字体文件，再按别名使用：

~~~python
from pathlib import Path

font_path = Path(__file__).parent / "assets" / "Brand.woff2"
page.fonts = {"brand": str(font_path)}
page.theme = saturn.Theme(font_family="brand")
page.add(saturn.Text("Brand font", font_family="brand", size=24))
~~~

支持本地 TTF、OTF、TTC、WOFF 和 WOFF2。相对路径先相对于当前工作目录，
然后尝试 assets 目录；发布应用时建议从 __file__ 构造明确路径。

HTTP(S) 字体会在后台加载。加载过程中先显示回退字体，完成后 Saturn 会
重新测量文字并刷新布局。下载失败会保留回退文字并输出警告。page.fonts
字典修改后调用 page.update()。

Saturn 自带 Inter，并可通过可选的 CJK 字体包安装中文字体。显式设置
fallback 列表有助于控制混合语言文本的字形来源。

## 颜色和文字样式

可以直接在控件上设置颜色，也可以构造 TextStyle：

~~~python
heading = saturn.Text(
    "Build with Saturn",
    style=saturn.TextStyle(
        size=28,
        weight=saturn.FontWeight.BOLD,
        color=saturn.Colors.ON_SURFACE,
    ),
)
~~~

Text 也支持 size、weight、italic、text_align、max_lines、no_wrap 和
overflow 等常用选项。完整细节请查 [Text](../api/Text.md) 与
[TextStyle](../api/TextStyle.md)。

## 主题变化

修改 Page 主题或主题模式后，调用 page.update() 应用新样式：

~~~python
def toggle_theme(event):
    page.theme_mode = (
        saturn.ThemeMode.LIGHT
        if page.theme_mode is saturn.ThemeMode.DARK
        else saturn.ThemeMode.DARK
    )
    page.update()
~~~

主题按 Page 隔离。原生子窗口最初继承父窗口主题和字体，但后续可以独立配置。

## 本章要点

主题控制应用默认值，控件参数处理局部例外，字体别名将资源路径和样式解耦。
窗口和平台主题边界见 [Page 指南](../page.md)。
