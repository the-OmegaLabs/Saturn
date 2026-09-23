# Duration

以毫秒等形式表示动画或等待时长。

[← API 索引](./README.md)

源码：[`saturn/types.py`](../../saturn/types.py)（第 137 行）。

## 构造参数

```python
saturn.Duration(microseconds: 'int' = 0, milliseconds: 'int' = 0, seconds: 'int' = 0, minutes: 'int' = 0, hours: 'int' = 0, days: 'int' = 0) -> None
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `microseconds` | `int` | `0` | 时间值中的微秒数。 |
| `milliseconds` | `int` | `0` | 时间值中的毫秒数。 |
| `seconds` | `int` | `0` | 时间值中的秒数。 |
| `minutes` | `int` | `0` | 时间值中的分钟数。 |
| `hours` | `int` | `0` | 时间值中的小时数。 |
| `days` | `int` | `0` | 时间值中的天数。 |
