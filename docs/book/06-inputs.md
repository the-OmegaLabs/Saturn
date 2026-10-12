# Inputs, Forms, and Feedback

Saturn's input controls include TextField, Checkbox, Switch, Radio, RadioGroup,
Slider, and Dropdown. Input controls hold the current value and notify the application through callbacks.

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

Common parameters include:

- value: the initial or current text;
- label, hint_text: the label and placeholder hint;
- password: hide the input with dots;
- multiline, min_lines, max_lines: multi-line input;
- read_only: display but disallow editing;
- max_length: limit the length, -1 means unlimited;
- input_filter: filter input with a regular expression;
- autofocus: try to grab focus when the page opens.

Desktop input is handled by SDL and Saturn itself. keyboard_type supports only a limited set of desktop values;
mobile keyboards, autofill, and some Flet input decoration parameters have no corresponding implementation.

## Selection controls

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

Radios should be placed in a RadioGroup:

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

Dropdown uses Option or DropdownOption:

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

Dropdown's editable, filtering, and search features only cover the desktop scope Saturn currently implements;
when free-form text editing is needed, prefer TextField.

## Form validation

Saturn does not decide the validation strategy for your application. You can update `error` in on_change, or validate everything together on submit:

~~~python
def submit(event):
    if not name.value.strip():
        name.error = "Name is required"
        name.update()
        return
    name.error = None
    page.show_dialog(saturn.SnackBar("Submitted"))
~~~

Errors can be expressed through TextField's `error` parameter, a neighboring Text, or an AlertDialog.
When validation fails, don't rely on `disabled` as the only hint; let users see the specific reason.

## Dialogs and SnackBar

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

AlertDialog is a modal overlay; SnackBar is brief, non-blocking feedback:

~~~python
page.show_dialog(saturn.SnackBar("Saved", action="Undo", duration=3000))
~~~

After modifying an input value or error state in a callback, call input.update(); to open or close dialogs,
use page.show_dialog() and page.pop_dialog().

## Focus and keyboard

Controls can grab initial focus via autofocus, or call control.focus() inside an event.
The Page's on_keyboard_event receives global key presses; when a TextField has focus, it handles text,
selection, and submit first.

Setting page.disabled to True and calling page.update() clears focus and blocks mouse, keyboard, and IME events for controls and
overlays; to re-enable, set it to False and update the page.

## Key points of this chapter

Input controls are the source of state, callbacks are the validation and submission boundary, and AlertDialog and SnackBar are the feedback
boundary. For detailed parameters and current limitations see [TextField](../api/TextField.md),
[Dropdown](../api/Dropdown.md), and [Slider](../api/Slider.md).
