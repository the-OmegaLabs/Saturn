# FilePickerResultEvent

FilePickerResultEvent(name: 'str', control: "'FilePicker'", files: 'list[FilePickerFile]', data: 'object' = None)

[← API 索引](./README.md)

源码：[`saturn/services.py`](../../saturn/services.py)（第 37 行）。

## 构造

```python
ft.FilePickerResultEvent(name: 'str', control: "'FilePicker'", files: 'list[FilePickerFile]', data: 'object' = None) -> None
```

### 参数

| 参数 | 类型标注 | 默认值 |
| --- | --- | --- |
| `name` | `str` | `必填` |
| `control` | `FilePicker` | `必填` |
| `files` | `list[FilePickerFile]` | `必填` |
| `data` | `object` | `None` |

## 本类属性

`control`、`data`、`files`、`name`、`page`。

---

本页依据仓库当前公开 API 与源码生成。继承成员请查阅基类；参数表中的 `**base` 会传给基类。
