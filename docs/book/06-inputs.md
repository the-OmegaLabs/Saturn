# 输入、表单与反馈

Saturn 的输入控件包括 TextField、Checkbox、Switch、Radio、RadioGroup、
Slider 和 Dropdown。输入控件保存当前值，并通过回调通知应用。

## TextField

~~~python
name = saturn.TextField(
    label="Project name",
    hint_text="Type a name",
    on_change=lambda e: print(e.data),
    on_submit=lambda e: submit(name.value),
    width=320,
)
page.add(name)
~~~

常用参数包括：

- value：初始或当前文本；
- label、hint_text：标签和占位提示；
- password：用圆点隐藏输入；
- multiline、min_lines、max_lines：多行输入；
- read_only：显示但禁止编辑；
- max_length：限制长度，-1 表示不限制；
- input_filter：使用正则过滤输入；
- autofocus：页面打开时尝试获取焦点。

桌面输入由 SDL 和 Saturn 自己处理。keyboard_type 只支持有限的桌面值；
移动端键盘、自动填充和部分 Flet 输入装饰参数没有对应实现。

## 选择控件

~~~python
agree = saturn.Checkbox("I agree", on_change=lambda e: print(agree.value))
enabled = saturn.Switch(label="Notifications", value=True)
volume = saturn.Slider(
    min=0,
    max=100,
    value=50,
    divisions=10,
    on_change=lambda e: print(volume.value),
)
page.add(agree, enabled, volume)
~~~

Radio 应该放在 RadioGroup 中：

~~~python
group = saturn.RadioGroup(
    value="python",
    on_change=lambda e: print(group.value),
    content=saturn.Column([
        saturn.Radio("Python", value="python"),
        saturn.Radio("Rust", value="rust"),
    ]),
)
page.add(group)
~~~

Dropdown 使用 Option 或 DropdownOption：

~~~python
format_field = saturn.Dropdown(
    label="Format",
    options=[
        saturn.Option("pdf", text="PDF"),
        saturn.Option("csv", text="CSV"),
    ],
    on_select=lambda e: print(e.data),
    width=240,
)
page.add(format_field)
~~~

Dropdown 的 editable、过滤和搜索功能只覆盖 Saturn 当前实现的桌面范围；
需要自由编辑文本时，优先使用 TextField。

## 表单校验

Saturn 不会替应用决定验证策略。可以在 on_change 中更新 error，或在提交
时统一验证：

~~~python
def submit(event):
    if not name.value.strip():
        name.error = "Name is required"
        name.update()
        return
    name.error = None
    page.show_dialog(saturn.SnackBar("Submitted"))
~~~

错误可以通过 TextField 的 error 参数、旁边的 Text 或 AlertDialog 表达。
校验失败时不要依赖 disabled 作为唯一提示；让用户看到具体原因。

## 对话框和 SnackBar

~~~python
dialog = saturn.AlertDialog(
    title=saturn.Text("Delete project?"),
    content=saturn.Text("This action cannot be undone."),
    actions=[
        saturn.TextButton("Cancel", on_click=lambda e: page.pop_dialog()),
        saturn.FilledButton("Delete", on_click=delete),
    ],
)


def ask_delete(event):
    page.show_dialog(dialog)
~~~

AlertDialog 是模态覆盖层；SnackBar 是短暂的非阻塞反馈：

~~~python
page.show_dialog(saturn.SnackBar("Saved", action="Undo", duration=3000))
~~~

在回调中修改输入值或错误状态后，调用 input.update()；打开或关闭对话框
使用 page.show_dialog() 和 page.pop_dialog()。

## 焦点和键盘

控件可以通过 autofocus 获取初始焦点，也可以在事件中调用 control.focus()。
Page 的 on_keyboard_event 收到全局按键；TextField 获得焦点时优先处理文本、
选择和提交。

将 page.disabled 设为 True 并调用 page.update()，会清除焦点并阻止控件和
覆盖层的鼠标、键盘和输入法事件；重新启用时设为 False 并更新页面。

## 本章要点

输入控件是状态源，回调是校验和提交边界，AlertDialog 和 SnackBar 是反馈
边界。详细参数与当前限制见 [TextField](../api/TextField.md)、
[Dropdown](../api/Dropdown.md) 和 [Slider](../api/Slider.md)。
