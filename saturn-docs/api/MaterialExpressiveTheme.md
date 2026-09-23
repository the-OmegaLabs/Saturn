# MaterialExpressiveTheme

Material Expressive 配色主题。

[← API 索引](./README.md)

源码：[`saturn/types.py`](../../saturn/types.py)（第 174 行）。

**基类：** [Theme](./Theme.md)

## 构造参数

```python
saturn.MaterialExpressiveTheme(font_family: 'str | None' = None, color_scheme_seed: 'str | None' = None, expressive: 'bool' = True) -> None
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `font_family` | `str | None` | `None` | 使用页面注册的字体名称。 |
| `color_scheme_seed` | `str | None` | `None` | 生成主题配色的种子颜色。 |
| `expressive` | `bool` | `True` | 是否启用 Expressive 尺寸与形状行为。 |
