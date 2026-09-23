# FilePickerUploadEvent

文件上传进度与错误信息事件。

[← API 索引](./README.md)

源码：[`saturn/services.py`](../../saturn/services.py)（第 49 行）。

## 构造参数

```python
saturn.FilePickerUploadEvent(name: 'str', control: "'FilePicker'", file_name: 'str', progress: 'float | None' = None, error: 'str | None' = None, data: 'object' = None) -> None
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `name` | `str` | `必填` | 对象、文件或资源的名称。 |
| `control` | `FilePicker` | `必填` | 产生事件或关联数据的控件。 |
| `file_name` | `str` | `必填` | 保存时建议使用的文件名。 |
| `progress` | `float | None` | `None` | 上传或操作的完成进度。 |
| `error` | `str | None` | `None` | 操作失败时的错误信息。 |
| `data` | `object` | `None` | 附着在控件或事件上的自定义数据。 |
