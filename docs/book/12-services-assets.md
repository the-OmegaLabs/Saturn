# File Services and Assets

Saturn's services are registered explicitly through the Page. FilePicker uses system dialogs to pick files,
directories, or a save path; asset paths are managed by your application.

## Registering a FilePicker

~~~python
picker = saturn.FilePicker(on_result=self.file_picked)
page.services.append(picker)
page.update()
~~~

A service only owns a Page after being added to page.services. Removing the service and updating the page clears its ownership.

## Picking files

FilePicker's operations are asynchronous:

~~~python
async def choose_image(event):
    files = await picker.pick_files(
        dialog_title="Choose an image",
        file_type=saturn.FilePickerFileType.IMAGE,
        allow_multiple=False,
        with_data=False,
    )
    if files:
        selected.value = files[0].path or files[0].name
        selected.update()
~~~

You can also handle results through on_result:

~~~python
def file_picked(event: saturn.FilePickerResultEvent):
    for file in event.files:
        print(file.name, file.size, file.path)
~~~

FilePickerFile provides id, name, size, path, and optional bytes. Setting with_data=True
reads the file content into memory, which is only suitable for files of a manageable size.

## Directories and saving

~~~python
directory = await picker.get_directory_path(
    dialog_title="Choose output directory",
)
target = await picker.save_file(
    dialog_title="Save report",
    file_name="report.txt",
    src_bytes=b"hello",
)
~~~

upload() is not implemented in the current desktop service; the application must hand the selected path to an
HTTP client or another upload layer itself.

## Images and fonts

Image can read local paths or SVG. When shipping an application, don't assume the current working directory; use
Path(__file__).parent to construct asset paths:

~~~python
from pathlib import Path

asset = Path(__file__).parent / "assets" / "logo.png"
page.add(saturn.Image(str(asset), width=180, height=80))
~~~

Fonts should also use absolute paths or paths based on the module file. Relative paths are convenient in a development environment,
but when launched from a shortcut, a packager, or a service, the working directory may differ.

## Clipboard

Clipboard is an asynchronous service that can read and write the system clipboard:

~~~python
clipboard = saturn.Clipboard()
await clipboard.set("Copied from Saturn")
value = await clipboard.get()
~~~

## Key points of this chapter

Services need explicit registration, file operations can block or read large amounts of data, and asset paths should be based on the application file
location. For the full interfaces see [FilePicker](../api/FilePicker.md) and the
[Page guide](../page.md).
