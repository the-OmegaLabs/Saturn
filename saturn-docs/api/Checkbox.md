# Checkbox

允许独立勾选或取消勾选的输入控件。

[← API 索引](./README.md)

源码：[`saturn/widgets/inputs.py`](../../saturn/widgets/inputs.py)（第 931 行）。

## 效果图

![Checkbox 控件的深色主题效果](../images/controls/Checkbox.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.Checkbox("Remember my choice", value=True))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** `_Toggle`

## 构造参数

```python
saturn.Checkbox(label: 'str' = '', *, value=False, active_color=None, label_position=<LabelPosition.RIGHT: 'right'>, on_change=None, **base)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `label` | `str` | `''` | 显示在输入框、选项或控件旁的标签。 |
| `value` | `—` | `False` | 复选框当前是否勾选。 |
| `active_color` | `—` | `None` | 选中或开启状态使用的颜色。 |
| `label_position` | `—` | `<LabelPosition.RIGHT: 'right'>` | 标签相对于选择控件的位置。 |
| `on_change` | `—` | `None` | 值改变时调用的回调。 |
| `**base` | `—` | `额外关键字参数` | 传给基础 Control 构造函数的关键字参数，例如 width、height。 |

`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。
