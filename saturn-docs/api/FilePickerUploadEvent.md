# FilePickerUploadEvent

FilePickerUploadEvent(name: 'str', control: "'FilePicker'", file_name: 'str', progress: 'float | None' = None, error: 'str | None' = None, data: 'object' = None)

[← API 索引](./README.md)

源码：[`saturn/services.py`](../../saturn/services.py)（第 49 行）。

## 构造

```python
ft.FilePickerUploadEvent(name: 'str', control: "'FilePicker'", file_name: 'str', progress: 'float | None' = None, error: 'str | None' = None, data: 'object' = None) -> None
```

### 参数

| 参数 | 类型标注 | 默认值 |
| --- | --- | --- |
| `name` | `str` | `必填` |
| `control` | `FilePicker` | `必填` |
| `file_name` | `str` | `必填` |
| `progress` | `float | None` | `None` |
| `error` | `str | None` | `None` |
| `data` | `object` | `None` |

## 本类属性

`control`、`data`、`error`、`file_name`、`name`、`page`、`progress`。

---

本页依据仓库当前公开 API 与源码生成。继承成员请查阅基类；参数表中的 `**base` 会传给基类。
