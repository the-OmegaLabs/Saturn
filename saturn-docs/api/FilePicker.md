# FilePicker

调用系统文件选择与保存对话框。

[← API 索引](./README.md)

源码：[`saturn/services.py`](../../saturn/services.py)（第 63 行）。

## 构造

```python
ft.FilePicker(on_result=None, on_upload=None, *, data=None, key=None, ref=None)
```

### 参数

| 参数 | 类型标注 | 默认值 |
| --- | --- | --- |
| `on_result` | `—` | `None` |
| `on_upload` | `—` | `None` |
| `data` | `—` | `None` |
| `key` | `—` | `None` |
| `ref` | `—` | `None` |

## 本类属性

`data`、`key`、`page`、`ref`。

## 事件回调

`on_result`、`on_upload`。

## 本类公开方法

| 方法 | 说明 |
| --- | --- |
| `pick_files(self, dialog_title=None, initial_directory=None, file_type=<FilePickerFileType.ANY: 'any'>, allowed_extensions=None, allow_multiple=False, with_data=False, compression_quality=0, cancel_upload_on_window_blur=True)` | — |
| `get_directory_path(self, dialog_title=None, initial_directory=None)` | — |
| `save_file(self, dialog_title=None, file_name=None, initial_directory=None, file_type=<FilePickerFileType.ANY: 'any'>, allowed_extensions=None, src_bytes=None)` | — |
| `upload(self, files: 'list[FilePickerUploadFile]')` | — |

---

本页依据仓库当前公开 API 与源码生成。继承成员请查阅基类；参数表中的 `**base` 会传给基类。
