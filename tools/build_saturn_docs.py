"""Generate source-backed Saturn API pages and a browsable index.

Run from any directory with: python tools/build_saturn_docs.py
The hand-written guides in saturn-docs/ are left untouched.
"""

from __future__ import annotations

import ast
import dataclasses
import enum
import inspect
import re
import textwrap
from pathlib import Path

import saturn
from control_examples import EXAMPLES
from parameter_descriptions import describe


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "saturn-docs"
API = OUT / "api"

CATEGORIES = {
    "应用与页面": "App Render run ControlEvent Control Page Window",
    "布局与内容": "Text Row Column Container Stack Divider Icon Image Card ListView GestureDetector ListItem",
    "按钮与操作": "Button ElevatedButton FilledButton FilledTonalButton OutlinedButton TextButton IconButton ExpressiveButton ExpressiveIconButton SplitButton ButtonGroup ToggleButton ElevatedToggleButton FilledTonalToggleButton OutlinedToggleButton FloatingActionButton SmallFloatingActionButton MediumFloatingActionButton LargeFloatingActionButton ExtendedFloatingActionButton FloatingToolbar HorizontalFloatingToolbar VerticalFloatingToolbar FloatingActionButtonMenu FloatingActionButtonMenuItem",
    "输入与反馈": "TextField Checkbox Switch Radio RadioGroup Dropdown DropdownOption Option Slider AlertDialog SnackBar ProgressBar ProgressRing LoadingIndicator WavyProgressIndicator LinearWavyProgressIndicator CircularWavyProgressIndicator",
    "文件服务": "FilePicker FilePickerFile FilePickerFileType FilePickerResultEvent FilePickerUploadEvent FilePickerUploadFile",
    "样式与类型": "Colors Icons parse_color Alignment Animation AnimationCurve Border BorderRadius BorderSide BoxShadow BoxFit CrossAxisAlignment Duration FontWeight KeyboardType LabelPosition MainAxisAlignment MaterialExpressiveTheme Margin Offset OutlineInputBorder Padding Rotate Scale ScrollMode TextAlign Theme ThemeMode TextOverflow TextStyle Tooltip TooltipTriggerMode",
}

DESCRIPTIONS = {
    "App": "管理窗口、事件循环和绘制后端的应用对象。",
    "Render": "选择软件、OpenGL 或 Vulkan 绘制后端。",
    "run": "启动 Saturn 应用并把 Page 交给入口函数。",
    "ControlEvent": "控件回调收到的事件数据。",
    "Control": "所有可视控件的基类，提供尺寸、状态和更新方法。",
    "Page": "应用页面，管理控件树、主题和对话框。",
    "Window": "原生窗口的尺寸、标题和状态。",
    "Text": "显示文本并设置字号、字重和颜色。",
    "Row": "横向排列子控件。",
    "Column": "纵向排列子控件。",
    "Container": "为子控件添加间距、背景、边框等装饰。",
    "Stack": "按层叠顺序摆放子控件。",
    "Icon": "显示 Material 图标。",
    "Image": "显示本地图片或 SVG。",
    "Card": "带有表面和阴影的内容容器。",
    "ListView": "可滚动的控件列表。",
    "GestureDetector": "接收指针和手势事件。",
    "Divider": "在相邻内容之间绘制一条分隔线。",
    "ListItem": "展示一行带标题、辅助文字和前后插槽的列表内容。",
    "Button": "可响应点击的基础按钮。",
    "ElevatedButton": "带有轻微阴影的按钮，适合普通操作。",
    "FilledButton": "使用主题主色填充的高强调按钮。",
    "FilledTonalButton": "使用柔和容器色填充的按钮。",
    "OutlinedButton": "使用描边强调边界的按钮。",
    "TextButton": "以文字呈现的低强调按钮。",
    "IconButton": "以图标呈现的紧凑操作按钮。",
    "ExpressiveButton": "支持尺寸和形状变化的 Material Expressive 按钮。",
    "ExpressiveIconButton": "支持 Expressive 尺寸和形状变化的图标按钮。",
    "SplitButton": "把主操作和副操作分开的按钮。",
    "ButtonGroup": "把多个按钮作为一个交互组排列。",
    "ToggleButton": "可在选中与未选中状态间切换的按钮。",
    "ElevatedToggleButton": "带有抬升表面的切换按钮。",
    "FilledTonalToggleButton": "柔和填充样式的切换按钮。",
    "OutlinedToggleButton": "描边样式的切换按钮。",
    "FloatingActionButton": "用于突出页面主要操作的浮动按钮。",
    "SmallFloatingActionButton": "小尺寸浮动操作按钮。",
    "MediumFloatingActionButton": "中尺寸浮动操作按钮。",
    "LargeFloatingActionButton": "大尺寸浮动操作按钮。",
    "ExtendedFloatingActionButton": "同时显示图标与文字的浮动操作按钮。",
    "FloatingToolbar": "以胶囊形表面容纳一组操作的浮动工具栏。",
    "HorizontalFloatingToolbar": "横向排列操作的浮动工具栏。",
    "VerticalFloatingToolbar": "纵向排列操作的浮动工具栏。",
    "FloatingActionButtonMenu": "从浮动按钮展开多项操作的菜单。",
    "FloatingActionButtonMenuItem": "浮动操作菜单中的一个可点击项目。",
    "TextField": "可编辑的文本输入框。",
    "Checkbox": "允许独立勾选或取消勾选的输入控件。",
    "Switch": "用于开关状态的滑动切换控件。",
    "Radio": "一组互斥选项中的单个单选按钮。",
    "RadioGroup": "管理多个 Radio 的单选值。",
    "Dropdown": "从选项列表中选择一个值。",
    "Slider": "通过拖动滑块选择范围内的数值。",
    "AlertDialog": "在页面上显示模态对话框。",
    "SnackBar": "显示短暂的操作反馈。",
    "ProgressBar": "以水平线条显示已知或不确定进度。",
    "ProgressRing": "以圆环显示已知或不确定进度。",
    "LoadingIndicator": "以动态形状展示正在进行的操作。",
    "WavyProgressIndicator": "以波浪线条展示进度。",
    "LinearWavyProgressIndicator": "线性的波浪进度指示器。",
    "CircularWavyProgressIndicator": "环形的波浪进度指示器。",
    "FilePicker": "调用系统文件选择与保存对话框。",
    "Colors": "颜色名称集合，包含主题色与固定颜色。",
    "Icons": "Material 图标名称集合。",
    "Theme": "定义页面颜色与外观的主题值。",
    "MaterialExpressiveTheme": "Material Expressive 配色主题。",
    "parse_color": "把颜色名称、十六进制值或颜色对象解析为 RGBA 数值。",
    "DropdownOption": "下拉框的一个数据选项，由 Dropdown 显示。",
    "Option": "DropdownOption 的简写名称，用来定义下拉选项。",
    "FilePickerFile": "文件选择器返回的单个文件信息。",
    "FilePickerFileType": "限定文件选择器可选文件的类型。",
    "FilePickerResultEvent": "文件选择或保存操作完成时传入的结果事件。",
    "FilePickerUploadEvent": "文件上传进度与错误信息事件。",
    "FilePickerUploadFile": "上传文件时使用的目标地址与请求方式。",
    "Alignment": "定义子控件在容器内的水平和垂直对齐位置。",
    "Animation": "定义属性变化动画的时长和曲线。",
    "AnimationCurve": "选择动画速度随时间变化的曲线。",
    "Border": "分别定义四个方向的边框。",
    "BorderRadius": "分别定义四个角的圆角半径。",
    "BorderSide": "定义一条边框的宽度和颜色。",
    "BoxFit": "选择图片在给定空间中的缩放与裁切方式。",
    "BoxShadow": "定义控件阴影的扩展、模糊、颜色和偏移。",
    "CrossAxisAlignment": "设置布局交叉轴上的子控件对齐方式。",
    "Duration": "以毫秒等形式表示动画或等待时长。",
    "FontWeight": "选择文字的字重。",
    "KeyboardType": "声明文本框适合的输入键盘类型。",
    "LabelPosition": "设置选择控件标签相对主体的位置。",
    "MainAxisAlignment": "设置 Row 或 Column 主轴上的排列方式。",
    "Margin": "定义控件外侧四个方向的留白。",
    "Offset": "定义二维位移及其命中测试行为。",
    "Padding": "定义控件内侧四个方向的留白。",
    "ScrollMode": "选择滚动行为模式。",
    "OutlineInputBorder": "配置表单输入框的描边外观。",
    "Rotate": "定义控件的旋转角度和旋转中心。",
    "Scale": "定义控件沿水平和垂直方向的缩放。",
    "TextAlign": "选择文本在可用宽度内的水平对齐方式。",
    "ThemeMode": "选择浅色、深色或跟随系统的主题模式。",
    "TextOverflow": "选择文本超过可用空间时的处理方式。",
    "TextStyle": "组合文字尺寸、字重、颜色和间距等样式。",
    "Tooltip": "配置控件悬停或长按时显示的提示内容。",
    "TooltipTriggerMode": "选择触发工具提示的交互方式。",
}

METHOD_DESCRIPTIONS = {
    "add": "在页面或控件列表末尾加入子控件。",
    "all": "用同一个值创建各方向一致的配置。",
    "center": "创建位于中心位置的对齐值。",
    "clean": "移除页面中的全部普通控件。",
    "client_size_for_outer": "根据窗口外框尺寸换算客户区域尺寸。",
    "close": "关闭窗口或展开的菜单。",
    "destroy": "销毁原生窗口并释放资源。",
    "draw": "请求绘制当前页面内容。",
    "focus": "使控件获得输入焦点。",
    "get_directory_path": "打开系统目录选择对话框。",
    "handle_event": "处理传入的控件事件。",
    "horizontal": "设置水平方向的两个值。",
    "insert": "在指定位置插入子控件。",
    "logical_point": "把物理坐标换算为逻辑坐标。",
    "mark_dirty": "标记界面需要重新绘制。",
    "none": "创建没有可见边框的配置。",
    "only": "分别设置指定方向的值。",
    "physical_size_for_logical": "把逻辑尺寸换算为物理像素尺寸。",
    "pick_files": "打开系统文件选择对话框。",
    "pointer_down": "处理指针按下事件。",
    "pointer_move": "处理指针移动事件。",
    "pointer_up": "处理指针松开事件。",
    "pop_dialog": "关闭当前对话框或提示条。",
    "remove": "从容器中移除指定控件。",
    "remove_at": "按索引移除子控件。",
    "run_until_closed": "持续处理窗口事件，直到窗口关闭。",
    "save_file": "打开系统文件保存对话框。",
    "scroll_to": "滚动到指定位置或按给定距离滚动。",
    "show_dialog": "在页面上显示对话框或提示条。",
    "start": "启动应用窗口与事件处理。",
    "symmetric": "分别为水平和垂直方向设置对称值。",
    "toggle": "切换展开与收起状态。",
    "update": "请求重绘本控件及其变化。",
    "upload": "将指定文件上传到给定地址。",
    "vertical": "设置垂直方向的两个值。",
    "zero": "创建四个方向均为零的配置。",
}

def markdown_code(value: object) -> str:
    return "`" + str(value).replace("`", "\\`") + "`"


def source_info(obj: object):
    target = obj
    if inspect.isclass(obj):
        target = obj
    path = inspect.getsourcefile(target)
    if not path:
        return None, None
    relative = Path(path).resolve().relative_to(ROOT).as_posix()
    try:
        line = inspect.getsourcelines(target)[1]
    except (OSError, TypeError):
        line = None
    return relative, line


def class_ast(obj: type):
    path = inspect.getsourcefile(obj)
    if not path:
        return None
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    return next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == obj.__name__), None)


def own_attributes(obj: type) -> list[str]:
    node = class_ast(obj)
    if node is None:
        return []
    result = set()
    for statement in node.body:
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)) and statement.name == "__init__":
            for child in ast.walk(statement):
                if isinstance(child, (ast.Assign, ast.AnnAssign)):
                    targets = child.targets if isinstance(child, ast.Assign) else [child.target]
                    for target in targets:
                        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self" and not target.attr.startswith("_"):
                            result.add(target.attr)
    for name, value in obj.__dict__.items():
        if isinstance(value, property) and not name.startswith("_"):
            result.add(name)
    if dataclasses.is_dataclass(obj):
        result.update(field.name for field in dataclasses.fields(obj) if not field.name.startswith("_"))
    return sorted(result)


def method_rows(obj: type) -> list[str]:
    rows = []
    for name, member in obj.__dict__.items():
        if name.startswith("_") or isinstance(member, property):
            continue
        if isinstance(member, (staticmethod, classmethod)):
            member = member.__func__
        if not inspect.isfunction(member):
            continue
        try:
            signature = str(inspect.signature(member))
        except (TypeError, ValueError):
            signature = "(...)"
        detail = (inspect.getdoc(member) or "").splitlines()
        summary = detail[0] if detail else METHOD_DESCRIPTIONS.get(name, "执行该方法对应的操作。")
        rows.append(f"| {markdown_code(name + signature)} | {summary.replace('|', '\\|')} |")
    return rows


def parameter_rows(name: str, obj: object) -> list[str]:
    try:
        signature = inspect.signature(obj)
    except (TypeError, ValueError):
        return []
    rows = []
    for param in signature.parameters.values():
        if param.name in ("self", "cls"):
            continue
        annotation = "—" if param.annotation is inspect.Signature.empty else str(param.annotation).strip("'")
        default = ("额外关键字参数" if param.kind is inspect.Parameter.VAR_KEYWORD else
                   "额外位置参数" if param.kind is inspect.Parameter.VAR_POSITIONAL else
                   "必填" if param.default is inspect.Signature.empty else repr(param.default))
        label = param.name
        if param.kind is inspect.Parameter.VAR_POSITIONAL:
            label = "*" + label
        elif param.kind is inspect.Parameter.VAR_KEYWORD:
            label = "**" + label
        explanation = describe(name, param.name).replace("|", "\\|")
        rows.append(f"| {markdown_code(label)} | {markdown_code(annotation)} | {markdown_code(default)} | {explanation} |")
    return rows


def page_for(name: str, category: str) -> str:
    obj = getattr(saturn, name)
    relative, line = source_info(obj)
    doc = (getattr(obj, "__doc__", None) or "").splitlines()
    summary = DESCRIPTIONS.get(name) or (doc[0] if doc else f"Saturn 的 {name} 公开 API。")
    lines = [f"# {name}", "", summary, "", "[← API 索引](./README.md)", ""]
    if relative:
        source = f"../../{relative}"
        lines += [f"源码：[{markdown_code(relative)}]({source})" + (f"（第 {line} 行）" if line else "") + "。", ""]

    if name in EXAMPLES:
        screenshot = f"../images/controls/{name}.png"
        snippet = textwrap.indent(EXAMPLES[name], "    ")
        lines += [
            "## 效果图", "", f"![{name} 控件的深色主题效果]({screenshot})", "",
            "## 示例代码", "", "以下代码可从仓库根目录运行，呈现上图中的控件。", "",
            "```python", "import saturn", "", "", "def main(page: saturn.Page):",
            "    page.theme_mode = saturn.ThemeMode.DARK",
            "    page.bgcolor = saturn.Colors.SURFACE",
            "    page.padding = 40", snippet, "    page.update()", "",
            "", "saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)",
            "```", "",
        ]

    if inspect.isclass(obj):
        bases = [base.__name__ for base in obj.__bases__ if base is not object and base.__name__ != name]
        if bases:
            links = [f"[{base}](./{base}.md)" if base in saturn.__all__ and base != name else markdown_code(base) for base in bases]
            lines += ["**基类：** " + "、".join(links), ""]
        if obj.__name__ != name:
            lines += [f"公开名称 `saturn.{name}` 指向实现类 `{obj.__name__}`。", ""]
        if issubclass(obj, enum.Enum):
            members = list(obj.__members__.items())
            lines += ["## 成员", ""]
            if len(members) > 80:
                lines += [f"共 {len(members)} 个名称。以下展示前 20 个；完整列表以源码为准。", ""]
                members = members[:20]
            lines += ["| 名称 | 值 |", "| --- | --- |"]
            lines += [f"| {markdown_code(key)} | {markdown_code(item.value)} |" for key, item in members]
            lines.append("")
            if members:
                lines += [f"在代码中通过成员名称使用，例如 `saturn.{name}.{members[0][0]}`。", ""]
            return "\n".join(lines)
        elif name in ("Colors", "Icons"):
            names = [key for key in vars(obj) if key.isupper()]
            lines += ["## 可用名称", "", f"共 {len(names)} 个名称。示例：" + "、".join(markdown_code(key) for key in names[:16]) + "。", "", "完整列表见上方源码；颜色值会根据主题解析。" if name == "Colors" else "完整图标列表见上方源码。", ""]
        else:
            if name in ("App", "Page", "Window"):
                lines += ["> 这些对象通常由 `saturn.run()` 创建和传入，应用代码无需直接构造。", ""]
            methods = method_rows(obj)
            if methods:
                lines += ["## 本类公开方法", "", "| 方法 | 说明 |", "| --- | --- |", *methods, ""]
    try:
        signature = str(inspect.signature(obj))
    except (TypeError, ValueError):
        signature = "(...)"
    heading = "构造参数" if inspect.isclass(obj) else "调用参数"
    lines += [f"## {heading}", "", "```python", f"saturn.{name}{signature}", "```", ""]
    params = parameter_rows(name, obj)
    if params:
        lines += ["| 参数 | 类型标注 | 默认值 | 作用 |", "| --- | --- | --- | --- |", *params, ""]
        if inspect.isclass(obj) and "**base" in signature:
            lines += ["`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。", ""]
    else:
        lines += ["无需传入参数。", ""]
    return "\n".join(lines)


def main() -> None:
    API.mkdir(parents=True, exist_ok=True)
    listed = {name for names in CATEGORIES.values() for name in names.split()}
    public = set(saturn.__all__)
    if listed != public:
        raise SystemExit(f"Catalog mismatch: missing={sorted(public - listed)}, extra={sorted(listed - public)}")
    visual = set().union(*(set(CATEGORIES[key].split()) for key in
                           ("布局与内容", "按钮与操作", "输入与反馈"))) - {"DropdownOption", "Option"}
    if set(EXAMPLES) != visual:
        raise SystemExit(f"Control examples mismatch: missing={sorted(visual - set(EXAMPLES))}, extra={sorted(set(EXAMPLES) - visual)}")
    missing_images = [name for name in EXAMPLES if not (OUT / "images" / "controls" / f"{name}.png").exists()]
    if missing_images:
        raise SystemExit(f"Control images missing: {missing_images}")
    for category, names in CATEGORIES.items():
        for name in names.split():
            (API / f"{name}.md").write_text(page_for(name, category), encoding="utf-8")
    lines = ["# Saturn API 索引", "", "[← 文档首页](../README.md) · [截图画廊](../gallery.md)", "", f"按仓库当前 `saturn.__all__` 整理，共 {len(public)} 个公开符号；一符号一篇 Markdown。可视控件页依次展示简介、深色效果图、完整示例和逐项说明的构造参数。非可视类型与服务页记录其实际接口。", ""]
    for category, names in CATEGORIES.items():
        lines += [f"## {category}", "", " · ".join(f"[{name}](./{name}.md)" for name in names.split()), ""]
    lines += ["## 与 Flet 知识库的关系", "", "分类方式参考仓库本地 `flet-skill/`，但这里仅记录 Saturn 实际导出的符号。Flet 知识库列出的其他控件、服务或属性，不代表 Saturn 已实现。", ""]
    (API / "README.md").write_text("\n".join(lines), encoding="utf-8")
    broken = []
    for page in OUT.rglob("*.md"):
        body = page.read_text(encoding="utf-8")
        targets = re.findall(r"!?\[[^]]*\]\(([^)]+)\)", body)
        targets += re.findall(r'<img\s+[^>]*src="([^"]+)"', body)
        for target in targets:
            if "://" in target or target.startswith("#"):
                continue
            destination = (page.parent / target.split("#", 1)[0]).resolve()
            if not destination.exists():
                broken.append(f"{page.relative_to(ROOT)} -> {target}")
    if broken:
        raise SystemExit("Broken documentation links:\n" + "\n".join(broken))
    print(f"Wrote {len(public)} API pages and index to {API}")


if __name__ == "__main__":
    main()
