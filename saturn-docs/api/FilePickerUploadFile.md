# FilePickerUploadFile

上传文件时使用的目标地址与请求方式。

[← API 索引](./README.md)

源码：[`saturn/services.py`](../../saturn/services.py)（第 29 行）。

## 构造参数

```python
saturn.FilePickerUploadFile(upload_url: 'str', method: 'str' = 'PUT', id: 'int | None' = None, name: 'str | None' = None) -> None
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `upload_url` | `str` | `必填` | 文件上传的目标地址。 |
| `method` | `str` | `'PUT'` | 触发操作的方法名称。 |
| `id` | `int | None` | `None` | 文件或对象的标识值。 |
| `name` | `str | None` | `None` | 对象、文件或资源的名称。 |
