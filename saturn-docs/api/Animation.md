# Animation

定义属性变化动画的时长和曲线。

[← API 索引](./README.md)

源码：[`saturn/types.py`](../../saturn/types.py)（第 158 行）。

## 构造参数

```python
saturn.Animation(duration: 'object' = <factory>, curve: 'AnimationCurve' = <AnimationCurve.LINEAR: 'linear'>) -> None
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `duration` | `object` | `<factory>` | 持续时间；具体单位由相应类定义。 |
| `curve` | `AnimationCurve` | `<AnimationCurve.LINEAR: 'linear'>` | 动画插值使用的曲线。 |
