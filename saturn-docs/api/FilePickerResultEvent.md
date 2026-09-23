# FilePickerResultEvent

文件选择或保存操作完成时传入的结果事件。

[← API 索引](./README.md)

源码：[`saturn/services.py`](../../saturn/services.py)（第 37 行）。

## 构造参数

```python
saturn.FilePickerResultEvent(name: 'str', control: "'FilePicker'", files: 'list[FilePickerFile]', data: 'object' = None) -> None
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `name` | `str` | `必填` | 对象、文件或资源的名称。 |
| `control` | `FilePicker` | `必填` | 产生事件或关联数据的控件。 |
| `files` | `list[FilePickerFile]` | `必填` | 选择、上传或返回的文件列表。 |
| `data` | `object` | `None` | 附着在控件或事件上的自定义数据。 |
