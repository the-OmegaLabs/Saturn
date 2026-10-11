# 架构与扩展 Saturn

应用开发通常只需要 Page、Control 和公开 widgets。理解这几个层次有助于
排查问题，也能帮助有经验的开发者为项目贡献实现。

## 运行时层

saturn.run 在应用进程中创建 App，启动 pygame/SDL 窗口和所选 renderer，
再创建 Page 并调用入口回调。App 管理 UI 事件循环、命令队列、后台 asyncio
循环、多个子窗口和渲染器生命周期。

main 回调和控件事件不是 SDL 绘制钩子。普通代码应修改控件状态并调用
update；只有 renderer 实现和平台适配层才直接使用 GPU、SDL 或原生句柄。

## 控件层

Control 提供布局尺寸、可见和禁用状态、变换、更新与生命周期。widgets 的
子类定义内容、绘制几何、子节点和输入响应。Page 把控件树交给布局系统，
再把绘制命令交给 Software 或 GPU renderer。

控件树有单一所有者。附着和移除会同步 page 与 parent 引用；在不同窗口
复用同一个控件实例会造成所有权错误。

## 绘制层

Software renderer 提供不需要 OpenGL context 的绘制路径。OpenGL 和 Vulkan
使用 GPU pipeline 处理几何、纹理、裁剪和部分效果。文字、图片和 SVG 需要
源纹理或字体栅格化，因此“GPU renderer”不代表没有 CPU 准备工作。

Shader 是公开的 GPU 绘制入口之一，不是所有控件的后处理滤镜。自定义 GLSL
需要 GPU renderer；Software 只绘制 fallback。

## 从哪里开始修改

- 新公开类型：实现控件/类型，导出于 saturn.__init__，更新 API 类别；
- 新构造参数：更新控件实现、参数说明和相关对照表；
- 新控件示例：编辑 tools/control_examples.py，并生成预览截图；
- 手写用户指南：放在 docs/ 或 docs/book/，不要放入生成的 docs/api 页面；
- renderer 或事件改变：添加覆盖真实行为的测试，并检查 Software、OpenGL
  和 Vulkan 的适用范围。

API 文档生成器会验证公开符号目录、控件示例集合、图像和 Markdown 链接。
修改导出 API 时运行它，避免文档索引和源码漂移。

## 可选 Web Runtime

saturn.web 复用 Page 和一部分 Control API，但有独立的 FastAPI app、会话注册表、
序列化场景和浏览器 Canvas renderer。桌面和 Web 不是同一个绘制后端；某个
Control 可在桌面使用，不代表 Web 有它的序列化和输入适配器。

## 本章要点

公共 API 由运行时、控件树和 renderer 共同实现。扩展时应保持层次清晰，让
语义留在 Control/Widget，将平台特定操作放在适当的适配层，并用面向用户的
指南解释最终行为。
