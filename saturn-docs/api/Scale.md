# Scale

定义控件沿水平和垂直方向的缩放。

[← API 索引](./README.md)

源码：[`saturn/types.py`](../../saturn/types.py)（第 324 行）。

## 构造参数

```python
saturn.Scale(scale: 'float | None' = None, scale_x: 'float | None' = None, scale_y: 'float | None' = None, alignment: 'Alignment | None' = None, origin: 'Offset | None' = None, transform_hit_tests: 'bool' = True, filter_quality: 'object' = None) -> None
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `scale` | `float | None` | `None` | 绘制控件时使用的缩放值。 |
| `scale_x` | `float | None` | `None` | 水平方向的缩放比例。 |
| `scale_y` | `float | None` | `None` | 垂直方向的缩放比例。 |
| `alignment` | `Alignment | None` | `None` | 子内容在容器或布局中的排列方式。 |
| `origin` | `Offset | None` | `None` | 变换的参考原点。 |
| `transform_hit_tests` | `bool` | `True` | 几何变换是否同步影响点击命中区域。 |
| `filter_quality` | `object` | `None` | 图片缩放时使用的采样质量。 |
