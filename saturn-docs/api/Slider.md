# Slider

通过拖动滑块选择范围内的数值。

[← API 索引](./README.md)

源码：[`saturn/widgets/inputs.py`](../../saturn/widgets/inputs.py)（第 1216 行）。

## 效果图

![Slider 控件的深色主题效果](../images/controls/Slider.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.Slider(value=0.65, width=320))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [Control](./Control.md)

## 构造参数

```python
saturn.Slider(value=None, *, min: 'float' = 0.0, max: 'float' = 1.0, divisions: 'int | None' = None, label=None, round: 'int' = 0, active_color=None, inactive_color=None, thumb_color=None, on_change=None, on_change_start=None, on_change_end=None, **base)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `value` | `—` | `None` | 滑块当前选中的数值。 |
| `min` | `float` | `0.0` | 可选择数值的下界。 |
| `max` | `float` | `1.0` | 可选择数值的上界。 |
| `divisions` | `int | None` | `None` | 把范围划分为多少个离散步进。 |
| `label` | `—` | `None` | 显示在输入框、选项或控件旁的标签。 |
| `round` | `int` | `0` | 数值标签或输出保留的小数位数。 |
| `active_color` | `—` | `None` | 选中或开启状态使用的颜色。 |
| `inactive_color` | `—` | `None` | 未选中状态的颜色。 |
| `thumb_color` | `—` | `None` | 滑块圆点的颜色。 |
| `on_change` | `—` | `None` | 值改变时调用的回调。 |
| `on_change_start` | `—` | `None` | 开始拖动或修改数值时调用的回调。 |
| `on_change_end` | `—` | `None` | 结束拖动或修改数值时调用的回调。 |
| `**base` | `—` | `额外关键字参数` | 传给基础 Control 构造函数的关键字参数，例如 width、height。 |

`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。
