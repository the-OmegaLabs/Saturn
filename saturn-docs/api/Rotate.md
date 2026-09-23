# Rotate

定义控件的旋转角度和旋转中心。

[← API 索引](./README.md)

源码：[`saturn/types.py`](../../saturn/types.py)（第 335 行）。

## 构造参数

```python
saturn.Rotate(angle: 'float' = 0.0, alignment: 'Alignment | None' = None, origin: 'Offset | None' = None, transform_hit_tests: 'bool' = True, filter_quality: 'object' = None) -> None
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `angle` | `float` | `0.0` | 旋转角度。 |
| `alignment` | `Alignment | None` | `None` | 子内容在容器或布局中的排列方式。 |
| `origin` | `Offset | None` | `None` | 变换的参考原点。 |
| `transform_hit_tests` | `bool` | `True` | 几何变换是否同步影响点击命中区域。 |
| `filter_quality` | `object` | `None` | 图片缩放时使用的采样质量。 |
