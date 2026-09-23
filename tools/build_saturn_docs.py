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
from pathlib import Path

import saturn as ft


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
    "Button": "可响应点击的基础按钮。",
    "ExpressiveButton": "支持尺寸和形状变化的 Material Expressive 按钮。",
    "TextField": "可编辑的文本输入框。",
    "Dropdown": "从选项列表中选择一个值。",
    "AlertDialog": "在页面上显示模态对话框。",
    "SnackBar": "显示短暂的操作反馈。",
    "FilePicker": "调用系统文件选择与保存对话框。",
    "Colors": "颜色名称集合，包含主题色与固定颜色。",
    "Icons": "Material 图标名称集合。",
    "Theme": "定义页面颜色与外观的主题值。",
    "MaterialExpressiveTheme": "Material Expressive 配色主题。",
}

IMAGE_BY_CATEGORY = {
    "布局与内容": "layout-demo.png",
    "按钮与操作": "buttons-demo.png",
    "输入与反馈": "inputs-demo.png",
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
        summary = detail[0] if detail else "—"
        rows.append(f"| {markdown_code(name + signature)} | {summary.replace('|', '\\|')} |")
    return rows


def parameter_rows(obj: object) -> list[str]:
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
        rows.append(f"| {markdown_code(param.name)} | {markdown_code(annotation)} | {markdown_code(default)} |")
    return rows


def page_for(name: str, category: str) -> str:
    obj = getattr(ft, name)
    relative, line = source_info(obj)
    doc = (getattr(obj, "__doc__", None) or "").splitlines()
    summary = DESCRIPTIONS.get(name) or (doc[0] if doc else f"Saturn 的 {name} 公开 API。")
    lines = [f"# {name}", "", summary, "", "[← API 索引](./README.md)", ""]
    if relative:
        source = f"../../{relative}"
        lines += [f"源码：[\u0060{relative}\u0060]({source})" + (f"（第 {line} 行）" if line else "") + "。", ""]

    if inspect.isclass(obj):
        bases = [base.__name__ for base in obj.__bases__ if base is not object]
        if bases:
            links = [f"[{base}](./{base}.md)" if base in ft.__all__ and base != name else markdown_code(base) for base in bases]
            lines += ["**基类：** " + "、".join(links), ""]
        if obj.__name__ != name:
            lines += [f"公开名称 `ft.{name}` 指向实现类 `{obj.__name__}`。", ""]
        if issubclass(obj, enum.Enum):
            members = list(obj.__members__.items())
            lines += ["## 成员", ""]
            if len(members) > 80:
                lines += [f"共 {len(members)} 个名称。以下展示前 20 个；完整列表以源码为准。", ""]
                members = members[:20]
            lines += ["| 名称 | 值 |", "| --- | --- |"]
            lines += [f"| {markdown_code(key)} | {markdown_code(item.value)} |" for key, item in members]
            lines.append("")
        elif name in ("Colors", "Icons"):
            names = [key for key in vars(obj) if key.isupper()]
            lines += ["## 可用名称", "", f"共 {len(names)} 个名称。示例：" + "、".join(markdown_code(key) for key in names[:16]) + "。", "", "完整列表见上方源码；颜色值会根据主题解析。" if name == "Colors" else "完整图标列表见上方源码。", ""]
        else:
            try:
                signature = str(inspect.signature(obj))
                lines += ["## 构造", "", "```python", f"ft.{name}{signature}", "```", ""]
            except (TypeError, ValueError):
                pass
            if name in ("App", "Page", "Window"):
                lines += ["> 这些对象通常由 `ft.run()` 创建和传入，应用代码无需直接构造。", ""]
            params = parameter_rows(obj)
            if params:
                lines += ["### 参数", "", "| 参数 | 类型标注 | 默认值 |", "| --- | --- | --- |", *params, ""]
            attributes = own_attributes(obj)
            if attributes:
                events = [value for value in attributes if value.startswith("on_")]
                values = [value for value in attributes if not value.startswith("on_")]
                if values:
                    lines += ["## 本类属性", "", "、".join(markdown_code(item) for item in values) + "。", ""]
                if events:
                    lines += ["## 事件回调", "", "、".join(markdown_code(item) for item in events) + "。", ""]
            methods = method_rows(obj)
            if methods:
                lines += ["## 本类公开方法", "", "| 方法 | 说明 |", "| --- | --- |", *methods, ""]
            if "__init__" not in obj.__dict__:
                parent = next((base for base in obj.__mro__[1:] if "__init__" in base.__dict__), None)
                if parent and parent.__name__ in ft.__all__ and parent.__name__ != name:
                    lines += [f"构造参数继承自 [{parent.__name__}](./{parent.__name__}.md)。", ""]
    else:
        try:
            lines += ["## 调用", "", "```python", f"ft.{name}{inspect.signature(obj)}", "```", ""]
        except (TypeError, ValueError):
            pass
        params = parameter_rows(obj)
        if params:
            lines += ["| 参数 | 类型标注 | 默认值 |", "| --- | --- | --- |", *params, ""]

    screenshot = IMAGE_BY_CATEGORY.get(category)
    if screenshot and name in {"Row", "Column", "Container", "Stack", "Button", "FilledButton", "TextField", "Checkbox", "Switch", "Slider", "Dropdown"}:
        lines += ["## 效果预览", "", f"![{category} 展示](../../shots/{screenshot})", ""]
    lines += ["---", "", "本页依据仓库当前公开 API 与源码生成。继承成员请查阅基类；参数表中的 `**base` 会传给基类。", ""]
    return "\n".join(lines)


def main() -> None:
    API.mkdir(parents=True, exist_ok=True)
    listed = {name for names in CATEGORIES.values() for name in names.split()}
    public = set(ft.__all__)
    if listed != public:
        raise SystemExit(f"Catalog mismatch: missing={sorted(public - listed)}, extra={sorted(listed - public)}")
    for category, names in CATEGORIES.items():
        for name in names.split():
            (API / f"{name}.md").write_text(page_for(name, category), encoding="utf-8")
    lines = ["# Saturn API 索引", "", "[← 文档首页](../README.md) · [截图画廊](../gallery.md)", "", f"按仓库当前 `saturn.__all__` 整理，共 {len(public)} 个公开符号；一符号一篇 Markdown。签名、属性和枚举成员来自 Saturn 源码。", ""]
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
