# Saturn 使用手册

本手册面向想用 Saturn 编写应用的 Python 开发者，按类似
[The Rust Book](https://doc.rust-lang.org/book/) 的顺序组织：先打开一个
窗口，再理解 Page 和控件树，然后逐步加入布局、事件、状态、输入、
主题、导航和渲染。

Saturn 的概念和命名参考了 [Flet 文档](https://flet.dev/docs/)，但 Saturn
是独立的 Python 桌面 UI 框架。示例只使用本仓库实际导出的 API。遇到与
Flet 同名的控件，以 Saturn 的实现和 [API 参考](./api/README.md)为准。

> Saturn 目前处于 alpha 阶段，公共 API 和功能覆盖仍可能变化。手册会说明
> 功能边界，不会把 Flet 文档中的名称自动当成 Saturn 已实现的能力。

## 从哪里开始

第一次使用 Saturn，请从[安装与运行](./book/01-installation.md)开始。
依赖已经准备好时，直接阅读[项目脚手架：第一个窗口](./getting-started.md)，
再按下面的章节顺序继续。

## Saturn 使用手册

### 入门

1. [Saturn 是什么](./book/00-introduction.md)
2. [安装与运行](./book/01-installation.md)
3. [项目脚手架：第一个窗口](./getting-started.md)
4. [Page、控件树与更新](./book/03-page-control-tree.md)

### 构建界面

5. [布局：Row、Column、Stack 和 Container](./book/04-layout.md)
6. [事件与状态](./book/05-events-state.md)
7. [输入、表单与反馈](./book/06-inputs.md)
8. [主题、颜色与字体](./book/07-theme.md)
9. [列表、滚动与性能](./book/08-lists.md)

### 构建应用

10. [导航与原生子窗口](./book/09-navigation-windows.md)
11. [动画与渲染后端](./book/10-animation-rendering.md)
12. [Material 3 Expressive](./book/11-expressive.md)
13. [文件服务与资源](./book/12-services-assets.md)
14. [在浏览器中运行](./book/13-web.md)
15. [测试、诊断与发布](./book/14-testing-packaging.md)

### 迁移与参考

16. [从 Flet 迁移](./book/15-flet-migration.md)
17. [阅读 API 参考](./book/16-api-reference.md)
18. [架构与扩展 Saturn](./book/17-architecture.md)

每章都尽量提供可以复制运行的代码。章节只依赖前面介绍的概念；需要完整
构造签名、属性和方法时，再跳到 API 参考。

## 常用入口

| 目标 | 文档 |
| --- | --- |
| 五分钟打开窗口 | [项目脚手架](./getting-started.md) |
| 查找控件或类型 | [API index](./api/README.md) |
| 查看截图和示例 | [Gallery](./gallery.md) |
| 配置原生窗口 | [Native windows](./window.md) |
| 选择后端或 GPU | [Renderer settings](./rendering.md) |
| 创建 Expressive UI | [Compose](./compose.md) |
| 共享浏览器会话 | [Web sessions](./web.md) |
| 编写 GLSL 背景 | [Shaders](./shaders.md) |
| 查看 Flet 差异 | [Flet mapping](./flet-mapping.md) |
| 理解平台拆分 | [Platform adapters](./platform-adapters.md) |
| 评估 Linux 桌面路线 | [Linux desktop roadmap](./linux-desktop-roadmap.md) |

## 本地阅读与生成

这些章节是普通 Markdown，可以直接在 GitHub 或编辑器中阅读。
SUMMARY.md 是 mdBook 的目录文件。

运行下面的命令可重新生成源码驱动的 API 页面和目录：

~~~powershell
python tools/build_saturn_docs.py
~~~

生成器不会覆盖本手册的手写章节。
