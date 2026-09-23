# Compose 命名空间与 Flet 接口核验

## 已实现的分组

Material 3 Expressive 控件通过 `saturn.Compose` 集中访问，普通的 Flet 风格控件继续使用 `saturn.Text`、`saturn.Button`、`saturn.ListView` 等顶层名称。当前保留原有 Expressive 顶层名称，供已有 Saturn 程序迁移。`Compose` 中的按钮变体复用原有绘制实现，但构造时默认启用 Expressive 尺寸和形状动画；顶层 Flet 同名按钮维持原默认值。

```python
import saturn

def main(page: saturn.Page):
    page.theme = saturn.Compose.Theme()
    page.add(
        saturn.Text("普通 Flet 风格控件"),
        saturn.Compose.Button("Expressive"),
        saturn.Compose.LoadingIndicator(),
    )

saturn.run(main, backend=saturn.Renderer.OPENGL)
```

| 命名空间 | 主要成员 | 用途 |
| --- | --- | --- |
| `saturn` | `Button`, `IconButton`, `Text`, `TextField`, `ListView`, `FloatingActionButton` 等 | 与 Flet 同名的默认接口，行为以 Saturn 已实现的子集为准 |
| `saturn.Compose` | `Theme`、`Button`、`IconButton`、Filled/Tonal/Elevated/Outlined/Text 按钮、`SplitButton`、`ButtonGroup`、Toggle 系列、FAB 尺寸系列、`ListItem`、Loading/Wavy 系列、FloatingToolbar 和 FAB Menu 系列 | Saturn 的 Material 3 Expressive 扩展 |

`Compose.Button` 是 `ExpressiveButton` 的别名，`Compose.IconButton` 是 `ExpressiveIconButton` 的别名；`Compose.Theme` 是 `MaterialExpressiveTheme` 的别名。`Compose.FilledButton`、`FilledTonalButton`、`ElevatedButton`、`OutlinedButton`、`TextButton` 在构造时默认选用 `size="small"`，因此启用 Expressive 模式。`Compose.FloatingActionButton` 与顶层同名类共用实现。

## Flet 实包核验

2026-09-23 在项目虚拟环境中安装并导入 **Flet 1.0.1**，结合仓库 `flet-skill/` 的 Flet 1.x API 导出，对 `saturn.__all__` 与实际 `flet` 导出、构造函数签名进行了比对。共有 **68 个同名类**可比较。`python -m tests.flet_api_checks` 实际构造了 Flet 和 Saturn 的 **29 种**常用默认控件，核对共同参数的保存结果，并执行 Saturn 文字、输入、Slider 和 FAB 行为路径。这个核验只证明所测接口和行为，不等于 Flutter 绘制或全部 Flet 参数兼容。

| 已用 Flet 实包构造并比较属性 | 结果 |
| --- | --- |
| `Text`、`Button`、`TextField`、`ListView`、`Row`、`Column`、`Container` | 所测共同参数通过；`Container.padding=8` 在 Saturn 中规范化为四边 8 |
| `Checkbox`、`Switch`、`Slider`、`Dropdown`、`Radio`、`ProgressBar`、`FloatingActionButton` | 所测共同参数通过；FAB 的图标使用各包自身的 `Icons.ADD` |
| `Card`、`Divider`、Filled/Tonal/Outlined/Text 按钮、`Icon`、`IconButton`、`Image`、`ProgressRing`、`Stack`、`Tooltip`、`AlertDialog`、`GestureDetector`、`DropdownOption` | 所测共同参数通过 |

本轮发现并修复了构造检查遗漏的实际问题：`Text(no_wrap=True)` 原本没有生成绘制行，现在保留硬换行并仅在需要时裁剪；`Slider(min != 0, divisions=...)` 原本按零点量化，现在从 `min` 量化；`TextField` 增加 `max_length`、`shift_enter`、`show_cursor`、`obscuring_character` 的实际输入或显示逻辑；默认 `FloatingActionButton` 增加 Flet 的 `mini`、文字 `content` 与 `foreground_color`。这些路径均由上述脚本执行验证。`show_cursor=False` 隐藏光标并停用闪烁计时，`max_length=-1` 表示无限制。

签名比对同时发现明显的 API 边界：例如 Flet 1.0.1 `ListView` 有 `reverse`、`build_controls_on_demand` 和 `cache_extent`，Saturn 尚未实现；`TextField` 的 `keyboard_type` 等输入行为也未核验。Saturn 的 `**base` 会接收若干未实现参数，因此构造成功不代表参数生效。验证脚本会打印每种控件缺少显式实现的参数数目与示例，以便继续逐项补齐。

| 接口 | Flet 1.0.1 核验结果 | Saturn 当前状态 / 后续修复 |
| --- | --- | --- |
| `Button`、`Text`、`Row`、`Column`、`Container` | 同名类存在 | 保留常用构造和交互子集；逐项补齐实际渲染行为，避免把 `**base` 接受但忽略的参数算作兼容 |
| `ListView` | `item_extent`、`reverse`、`build_controls_on_demand` 等参数存在 | Saturn 已实现 `item_extent` 的固定尺寸布局和可见行按需布局；`reverse` 等参数尚未实现，需要按 Flet 定义继续核对 |
| `FloatingActionButton` | Flet 有 `mini`、`shape` 等参数 | Saturn 已支持 `mini`、文字 `content`、`foreground_color`；`shape` 和部分视觉参数仍未实现。Expressive 尺寸变体放在 `Compose` |
| `TextField` | Flet 有 `keyboard_type` 等参数 | Saturn 当前构造函数未显式覆盖完整 API，需逐项检查输入语义 |
| `ElevatedButton`、`ListItem`、`LoadingIndicator`、`SplitButton`、`ButtonGroup` | Flet 1.0.1 顶层无这些名称 | Saturn 扩展，归入 `Compose`；旧顶层别名暂留供迁移 |
| `MaterialExpressiveTheme` | Flet 1.0.1 顶层无此名称 | `Compose.Theme` 是 Saturn 扩展 |

**接口边界：**目前不能把 Saturn 描述为 Flet 1.0.1 全量兼容实现。`Control` 的 `**_flet_ignored` 以及若干控件的 `**base` 会接收部分参数但不产生对应效果。后续修复应优先处理常用属性的真实行为；暂不支持的属性应写入文档或显式提示。

## 迁移与后续任务

1. 新代码使用 `saturn.Compose.*` 表达 Expressive 组件；旧代码可逐步替换顶层 Expressive 名称。
2. 需要 Flet 完全一致的应用应按实际使用的参数和事件逐项验证；上述检查覆盖常用构造与属性，不声称全量兼容。
3. 若未来不兼容版本移除旧顶层 Expressive 别名，应另行安排迁移；本次不改变旧代码的导入结果。

Expressive 加载图形的第三方来源和许可说明见 [NOTICE](../saturn/_gen/NOTICE.md) 与 [Apache 2.0 全文](../saturn/_gen/LICENSE-APACHE-2.0.txt)。
