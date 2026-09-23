<p align="center"><img src="../saturn-logo.svg" width="96" alt="Saturn 经典环形星球 logo"></p>

# Saturn 文档

Saturn 是面向 Python 桌面应用的轻量 UI 框架。这套文档按仓库里的 `flet-skill/` 分类方式整理，方便从熟悉的 Flet 概念找到对应的 Saturn 实现。内容依据当前代码生成和编写，适用于此仓库版本。

> Saturn 仍处于 alpha 阶段。公开 API 会变化；同名 Flet 控件也不保证所有参数和行为都相同。

## 从这里开始

| 入口 | 适合做什么 |
| --- | --- |
| [五分钟上手](./getting-started.md) | 安装、运行第一个窗口、响应事件 |
| [API 索引](./api/README.md) | 逐个查看控件介绍、独立效果图、代码与构造参数 |
| [截图画廊](./gallery.md) | 观赏深色主题下的布局、按钮、输入与动态组件 |
| [标志设计](./branding.md) | 查看经典标志与透明版的使用方式 |
| [Flet 对照与范围](./flet-mapping.md) | 了解命名对应关系和已覆盖范围 |
| [Expressive 组件](../docs/expressive.md) | 查看 Expressive 实现说明和示例 |

## 常用 API 直达

- 页面与运行：[run](./api/run.md)、[Page](./api/Page.md)、[Control](./api/Control.md)
- 布局：[Row](./api/Row.md)、[Column](./api/Column.md)、[Container](./api/Container.md)、[Stack](./api/Stack.md)
- 内容：[Text](./api/Text.md)、[Icon](./api/Icon.md)、[Image](./api/Image.md)
- 交互：[Button](./api/Button.md)、[TextField](./api/TextField.md)、[Dropdown](./api/Dropdown.md)
- 主题：[Theme](./api/Theme.md)、[Colors](./api/Colors.md)、[MaterialExpressiveTheme](./api/MaterialExpressiveTheme.md)

![Saturn 按钮示例](../shots/buttons-demo.png)

API 页面由 `python tools/build_saturn_docs.py` 生成；手写指南不会被这个命令覆盖。
