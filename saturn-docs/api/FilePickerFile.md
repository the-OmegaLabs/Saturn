# FilePickerFile

文件选择器返回的单个文件信息。

[← API 索引](./README.md)

源码：[`saturn/services.py`](../../saturn/services.py)（第 20 行）。

## 构造参数

```python
saturn.FilePickerFile(id: 'int', name: 'str', size: 'int', path: 'str | None' = None, bytes: 'bytes | None' = None) -> None
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `id` | `int` | `必填` | 文件或对象的标识值。 |
| `name` | `str` | `必填` | 对象、文件或资源的名称。 |
| `size` | `int` | `必填` | 文字、图标或控件的尺寸等级。 |
| `path` | `str | None` | `None` | 本地文件或目录路径。 |
| `bytes` | `bytes | None` | `None` | 文件或资源的字节内容。 |
