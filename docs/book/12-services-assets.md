# 文件服务与资源

Saturn 的服务通过 Page 显式注册。FilePicker 使用系统对话框选择文件、
目录或保存路径；资源路径则由你的应用负责管理。

## 注册 FilePicker

~~~python
picker = saturn.FilePicker(on_result=self.file_picked)
page.services.append(picker)
page.update()
~~~

服务加入 page.services 后才拥有 Page。删除服务并更新页面会清除它的所有权。

## 选择文件

FilePicker 的操作是异步的：

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

也可以通过 on_result 处理结果：

~~~python
def file_picked(event: saturn.FilePickerResultEvent):
    for file in event.files:
        print(file.name, file.size, file.path)
~~~

FilePickerFile 提供 id、name、size、path 和可选的 bytes。设置 with_data=True
会把文件内容读入内存，只适合可控大小的文件。

## 目录和保存

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

upload() 在当前桌面服务中没有实现；应用需要自己把选择到的 path 交给
HTTP 客户端或其他上传层。

## 图片和字体

Image 可以读取本地路径或 SVG。发布应用时不要假设当前工作目录，使用
Path(__file__).parent 构造资源路径：

~~~python
from pathlib import Path

asset = Path(__file__).parent / "assets" / "logo.png"
page.add(saturn.Image(str(asset), width=180, height=80))
~~~

字体也建议使用绝对路径或基于模块文件的路径。相对路径在开发环境中方便，
但从快捷方式、打包程序或服务启动时，工作目录可能不同。

## Clipboard

Clipboard 是异步服务，可以读写系统剪贴板：

~~~python
clipboard = saturn.Clipboard()
await clipboard.set("Copied from Saturn")
value = await clipboard.get()
~~~

## 本章要点

服务需要显式注册，文件操作可能阻塞或读入大量数据，资源路径应以应用文件
位置为基础。完整接口见 [FilePicker](../api/FilePicker.md) 和
[Page 指南](../page.md)。
