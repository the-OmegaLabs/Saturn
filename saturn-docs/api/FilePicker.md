# FilePicker

Opens system file selection and save dialogs.

[← API index](./README.md)

Source: [`saturn/services.py`](../../saturn/services.py) (line 63).

## Public methods

| Method | Description |
| --- | --- |
| `pick_files(self, dialog_title=None, initial_directory=None, file_type=<FilePickerFileType.ANY: 'any'>, allowed_extensions=None, allow_multiple=False, with_data=False, compression_quality=0, cancel_upload_on_window_blur=True)` | Opens the system file picker. |
| `get_directory_path(self, dialog_title=None, initial_directory=None)` | Opens the system directory picker. |
| `save_file(self, dialog_title=None, file_name=None, initial_directory=None, file_type=<FilePickerFileType.ANY: 'any'>, allowed_extensions=None, src_bytes=None)` | Opens the system save-file dialog. |
| `upload(self, files: 'list[FilePickerUploadFile]')` | Uploads selected files to the given destination. |

## Constructor parameters

```python
saturn.FilePicker(on_result=None, on_upload=None, *, data=None, key=None, ref=None)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `on_result` | `—` | `None` | Callback called when a file selection or save returns a result. |
| `on_upload` | `—` | `None` | Callback called when file upload status changes. |
| `data` | `—` | `None` | Custom data attached to the control or event. |
| `key` | `—` | `None` | Key used to locate a control or service. |
| `ref` | `—` | `None` | Place to store a control or service reference. |
