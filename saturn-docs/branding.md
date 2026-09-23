# Saturn 标志

[← 文档首页](./README.md) · [截图画廊](./gallery.md)

主 README 保留经典的黑色方形 Saturn 标志。演示程序使用同一环星图形的透明背景版本，能够随浅色或深色主题着色。

![透明背景标志在紫色背景上的预览](./assets/logo-transparent-preview.png)

透明素材：[saturn-logo-transparent.png](../saturn-logo-transparent.png)。它由 [经典 SVG](../saturn-logo.svg) 生成：先保留星球对后方轨道的遮挡，再把黑色像素转为透明。可用 `python tools/make_transparent_logo.py` 重新生成。

所有演示的标题区和 960 × 800 窗口尺寸集中定义在 [`examples/demo_common.py`](../examples/demo_common.py)。
