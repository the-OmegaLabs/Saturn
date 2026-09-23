# Offset

定义二维位移及其命中测试行为。

[← API 索引](./README.md)

源码：[`saturn/types.py`](../../saturn/types.py)（第 316 行）。

## 构造参数

```python
saturn.Offset(x: 'float' = 0.0, y: 'float' = 0.0, transform_hit_tests: 'bool' = True, filter_quality: 'object' = None) -> None
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `x` | `float` | `0.0` | 水平坐标或位移分量。 |
| `y` | `float` | `0.0` | 垂直坐标或位移分量。 |
| `transform_hit_tests` | `bool` | `True` | 几何变换是否同步影响点击命中区域。 |
| `filter_quality` | `object` | `None` | 图片缩放时使用的采样质量。 |
