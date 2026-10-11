# 阅读 API 参考

本书按开发任务讲解概念。API 参考按公开符号组织，记录当前代码导出的类型、
构造签名、常用方法和示例。

## 从哪个页面查起

| 我想做什么 | 起点 |
| --- | --- |
| 启动应用 | [run](../api/run.md)、[App](../api/App.md) |
| 控制页面 | [Page](../api/Page.md)、[Control](../api/Control.md) |
| 排列内容 | [Row](../api/Row.md)、[Column](../api/Column.md)、[Stack](../api/Stack.md) |
| 装饰区域 | [Container](../api/Container.md)、[Card](../api/Card.md) |
| 显示文字和图像 | [Text](../api/Text.md)、[Image](../api/Image.md) |
| 接受输入 | [TextField](../api/TextField.md)、[Dropdown](../api/Dropdown.md) |
| 做原生子窗口 | [Subpage](../api/Subpage.md) |
| 配置颜色和主题 | [Theme](../api/Theme.md)、[Colors](../api/Colors.md) |
| 列出所有符号 | [API index](../api/README.md) |

## 如何读参数表

每个类型页面列出当前源码签名。参数可能来自控件本身，也可能通过
**base 传给通用 Control。Control 页面列出了大小、可见性、布局、动画、
焦点和变换参数。

一个参数“被构造函数接受”不一定表示功能实现。对 Flet 兼容参数，API 页
会标注非默认值不支持；完整差异见
[Control 参数比较](../control-parameters-comparison.md)。

## 按源码更新

仓库中的 API 页由工具生成：

~~~powershell
python tools/build_saturn_docs.py
~~~

这会从 saturn.__all__、运行时签名、参数说明和示例生成 docs/api/。手写
章节保持独立，不会被这个命令覆盖。

## 本章要点

先按任务阅读概念章节，再按符号跳到 API 页；遇到跨框架兼容疑问，查差异表
并在本地运行代码。当前版本的源代码是最终行为依据。
