# Theme

定义页面颜色与外观的主题值。

[← API 索引](./README.md)

源码：[`saturn/types.py`](../../saturn/types.py)（第 164 行）。

## 构造参数

```python
saturn.Theme(font_family: 'str | None' = None, color_scheme_seed: 'str | None' = None) -> None
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `font_family` | `str | None` | `None` | 使用页面注册的字体名称。 |
| `color_scheme_seed` | `str | None` | `None` | 生成主题配色的种子颜色。 |
