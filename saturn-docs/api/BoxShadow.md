# BoxShadow

定义控件阴影的扩展、模糊、颜色和偏移。

[← API 索引](./README.md)

源码：[`saturn/types.py`](../../saturn/types.py)（第 344 行）。

## 构造参数

```python
saturn.BoxShadow(spread_radius: 'float' = 0.0, blur_radius: 'float' = 0.0, color: 'object' = '#000000', offset: 'Offset' = <factory>) -> None
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `spread_radius` | `float` | `0.0` | 阴影轮廓向外扩张的距离。 |
| `blur_radius` | `float` | `0.0` | 阴影模糊半径。 |
| `color` | `object` | `'#000000'` | 前景、文字或绘制内容的颜色。 |
| `offset` | `Offset` | `<factory>` | 在布局位置之外施加的位移。 |
