# Radio

一组互斥选项中的单个单选按钮。

[← API 索引](./README.md)

源码：[`saturn/widgets/inputs.py`](../../saturn/widgets/inputs.py)（第 1123 行）。

## 效果图

![Radio 控件的深色主题效果](../images/controls/Radio.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.Radio("standard", label="Standard"))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [Control](./Control.md)

## 构造参数

```python
saturn.Radio(value=None, *, label: 'str' = '', label_position=<LabelPosition.RIGHT: 'right'>, active_color=None, **base)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `value` | `—` | `None` | 控件或数据对象的当前值。 |
| `label` | `str` | `''` | 显示在输入框、选项或控件旁的标签。 |
| `label_position` | `—` | `<LabelPosition.RIGHT: 'right'>` | 标签相对于选择控件的位置。 |
| `active_color` | `—` | `None` | 选中或开启状态使用的颜色。 |
| `**base` | `—` | `额外关键字参数` | 传给基础 Control 构造函数的关键字参数，例如 width、height。 |

`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。
