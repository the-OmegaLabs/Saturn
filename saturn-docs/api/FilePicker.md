# FilePicker

调用系统文件选择与保存对话框。

[← API 索引](./README.md)

源码：[`saturn/services.py`](../../saturn/services.py)（第 63 行）。

## 本类公开方法

| 方法 | 说明 |
| --- | --- |
| `pick_files(self, dialog_title=None, initial_directory=None, file_type=<FilePickerFileType.ANY: 'any'>, allowed_extensions=None, allow_multiple=False, with_data=False, compression_quality=0, cancel_upload_on_window_blur=True)` | 打开系统文件选择对话框。 |
| `get_directory_path(self, dialog_title=None, initial_directory=None)` | 打开系统目录选择对话框。 |
| `save_file(self, dialog_title=None, file_name=None, initial_directory=None, file_type=<FilePickerFileType.ANY: 'any'>, allowed_extensions=None, src_bytes=None)` | 打开系统文件保存对话框。 |
| `upload(self, files: 'list[FilePickerUploadFile]')` | 将指定文件上传到给定地址。 |

## 构造参数

```python
saturn.FilePicker(on_result=None, on_upload=None, *, data=None, key=None, ref=None)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `on_result` | `—` | `None` | 文件选择或保存操作返回结果时调用的回调。 |
| `on_upload` | `—` | `None` | 文件上传状态变化时调用的回调。 |
| `data` | `—` | `None` | 附着在控件或事件上的自定义数据。 |
| `key` | `—` | `None` | 用于定位控件或服务的键。 |
| `ref` | `—` | `None` | 保存控件或服务引用的位置。 |
