# Expressive 组件与绘制

## 组件

- `MaterialExpressiveTheme`：浅色 on-container 配色；深色随 `page.theme_mode` 切换。
- `ExpressiveButton` / `ExpressiveIconButton`：五档尺寸、按下和选中形状变化。
- `ToggleButton`、`ElevatedToggleButton`、`FilledTonalToggleButton`、`OutlinedToggleButton`。
- `SplitButton`：独立主操作与副操作，ripple 使用两段各自的不对称圆角遮罩。
- `ButtonGroup`：按压项扩大 15%，相邻项缩小；绘制与命中使用相同动画布局。
- `FloatingActionButton`、Small/Medium/Large/Extended 变体：形状遮罩经双层高斯柔化形成阴影。
- `ListItem`：一至三行内容、前后槽位、选中及禁用状态。
- `LoadingIndicator`：SoftBurst → Cookie9Sided → Pentagon → Pill → Sunny → Cookie4Sided → Oval 的七形态 RoundedPolygon morph；每段 650ms、持续旋转。`value` 数值模式为 Circle → SoftBurst，`contained=True` 添加容器。
- `WavyProgressIndicator` / `LinearWavyProgressIndicator`、`CircularWavyProgressIndicator`：支持数值进度与不确定进度、移动波形、颜色、振幅、波长和波速。
- `FloatingToolbar` / Horizontal/Vertical 变体：64dp 胶囊容器，可收起 leading/trailing 槽位；隐藏部分不可点击。
- `FloatingActionButtonMenu` / `FloatingActionButtonMenuItem`：锚定菜单、滚动长列表、选择回调、点击空白处或 Escape 关闭。

## 示例

```python
import saturn as ft

def main(page):
    page.theme = ft.MaterialExpressiveTheme()
    page.add(
        ft.LoadingIndicator(contained=True),
        ft.WavyProgressIndicator(.6),
        ft.FloatingToolbar(ft.IconButton(ft.Icons.EDIT), ft.IconButton(ft.Icons.SHARE)),
        ft.FloatingActionButtonMenu([
            ft.FloatingActionButtonMenuItem("Create", icon=ft.Icons.ADD,
                                           on_click=lambda e: print("create")),
        ]),
    )

ft.run(main)
```

- 基础展板：`uv run python examples/expressive_demo.py`。
- 动画展板：`uv run python examples/expressive_motion_demo.py`；可加 `--dark`、`--menu`、`--pressed`。
- 回归检查：`uv run python -m tests.expressive_checks`。

## 绘制与资源

所有新形状在共享绘制路径中生成，软件、OpenGL 与 Vulkan 使用同一份轮廓。
轮廓变换使用预生成的匹配 Bézier 控制点，运行时不需要 JVM；再生成工具为 `tools/ExportLoadingShapes.java`。
原始参考资料、资源出处和第三方许可证保存在 `references/`。

输入框缺口采用分区描边，不覆盖父容器背景；空字段缺口的宽度和深度随标签浮动进度一起变化，有值字段的标签与缺口在焦点切换时保持浮动状态。
阴影按完整形状模糊并缓存，长标签不会改变阴影的圆角结构。
组件形状切换仍使用框架的插值动画；LoadingIndicator 使用阻尼弹簧响应。
ButtonGroup 的连接模式当前提供 2dp 间距，尚无溢出菜单。
