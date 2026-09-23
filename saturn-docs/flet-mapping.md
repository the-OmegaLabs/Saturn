# Flet 对照与范围

[← 文档首页](./README.md) · [API 索引](./api/README.md)

`flet-skill/` 是本地 Flet 1.x 知识库，适合查 Flet 本身；`saturn-docs/` 只收录 Saturn 在 `saturn.__all__` 中公开的符号。两者分类相近，便于查阅，但接口覆盖范围以 Saturn API 页与源码为准。

| 熟悉的 Flet 概念 | Saturn 入口 | 当前用途 |
| --- | --- | --- |
| `ft.run()`、`Page` | [run](./api/run.md)、[Page](./api/Page.md) | 创建窗口和页面、添加控件 |
| `Row`、`Column`、`Container` | [布局类](./api/README.md#布局与内容) | 排列和装饰控件 |
| `Text`、`Icon`、`Image` | [内容类](./api/README.md#布局与内容) | 显示文本、图标、图片 |
| `Button` 与按钮变体 | [按钮类](./api/README.md#按钮与操作) | 常规操作和 Expressive 操作 |
| 输入与反馈 | [输入与反馈](./api/README.md#输入与反馈) | 文本、选择、进度、弹窗 |
| 主题与类型 | [样式与类型](./api/README.md#样式与类型) | 颜色、枚举、动画和边框 |
| `FilePicker` | [FilePicker](./api/FilePicker.md) | 本地文件选择与保存 |

迁移时先替换导入并运行示例，再逐项检查构造参数、事件数据与渲染效果。Saturn 的 `Control` 构造函数接受额外 Flet 风格关键字，但这不表示这些关键字都会产生视觉或交互效果；请以具体控件实现和截图为准。

当前 Saturn 面向本地桌面应用，不提供 Flet 的完整 Web、移动端、平台服务与控件清单。
