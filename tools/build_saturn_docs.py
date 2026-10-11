"""Generate source-backed Saturn API pages and a browsable index.

Run from any directory with: python tools/build_saturn_docs.py
The hand-written guides in docs/ are left untouched.
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
OUT = ROOT / "docs"
API = OUT / "api"

CATEGORIES = {
    "App and page": "App Renderer Render run run_thread ControlEvent Event HoverEvent KeyboardEvent PageResizeEvent PlatformBrightnessChangeEvent TextSelectionChangeEvent LayoutSizeChangeEvent RouteChangeEvent RenderFailedEvent RenderReadyEvent FontOptimizeEvent WindowEvent WindowEventType WindowResizeEdge Control Page Window",
    "Navigation and effects": "Subpage Shader ShaderEffect ShaderBuffer",
    "Input border styles": "NoInputBorder UnderlineInputBorder",
    "Expressive namespace": "Compose",
    "Layout and content": "Text Row Column Container Stack Divider Icon Image Card ListView GestureDetector ListItem",
    "Buttons and actions": "Button ElevatedButton FilledButton FilledTonalButton OutlinedButton TextButton IconButton ExpressiveButton ExpressiveIconButton SplitButton ButtonGroup ToggleButton ElevatedToggleButton FilledTonalToggleButton OutlinedToggleButton FloatingActionButton SmallFloatingActionButton MediumFloatingActionButton LargeFloatingActionButton ExtendedFloatingActionButton FloatingToolbar HorizontalFloatingToolbar VerticalFloatingToolbar FloatingActionButtonMenu FloatingActionButtonMenuItem",
    "Input and feedback": "TextField Checkbox Switch Radio RadioGroup Dropdown DropdownOption Option Slider AlertDialog DialogControl SnackBar ProgressBar ProgressRing LoadingIndicator WavyProgressIndicator LinearWavyProgressIndicator CircularWavyProgressIndicator",
    "Navigation controls": "NavigationRail NavigationRailDestination NavigationRailLabelType PopupMenuButton PopupMenuItem",
    "Additional widgets": "AnimatedSwitcher AnimatedSwitcherTransition VerticalDivider WindowDragArea",
    "File services": "FilePicker FilePickerFile FilePickerFileType FilePickerResultEvent FilePickerUploadEvent FilePickerUploadFile Clipboard",
    "Styles and types": "Colors Icons parse_color Alignment Animation AnimationCurve Border BorderRadius BorderSide BoxShadow Blur BlurTileMode BoxFit CrossAxisAlignment Duration FontWeight InputBorder NumbersOnlyInputFilter KeyboardType LabelPosition MainAxisAlignment MaterialExpressiveTheme Margin Offset OutlineInputBorder Padding Rotate Scale ScrollMode TextAlign Theme ThemeMode TextOverflow TextStyle Tooltip TooltipTriggerMode ButtonStyle ControlState BoxConstraints MouseCursor Ref RoundedRectangleBorder StadiumBorder CircleBorder ImageRepeat FilterQuality ClipBehavior BoxShape StrokeCap VisualDensity TextSelection TextAffinity InputFilter TextCapitalization SliderInteraction LinearGradient RadialGradient",
}

BOOK_CHAPTERS = [
    ("Saturn 是什么", "book/00-introduction.md"),
    ("安装与运行", "book/01-installation.md"),
    ("项目脚手架：第一个窗口", "getting-started.md"),
    ("Page、控件树与更新", "book/03-page-control-tree.md"),
    ("布局", "book/04-layout.md"),
    ("事件与状态", "book/05-events-state.md"),
    ("输入、表单与反馈", "book/06-inputs.md"),
    ("主题、颜色与字体", "book/07-theme.md"),
    ("列表、滚动与性能", "book/08-lists.md"),
    ("导航与原生子窗口", "book/09-navigation-windows.md"),
    ("动画与渲染后端", "book/10-animation-rendering.md"),
    ("Material 3 Expressive", "book/11-expressive.md"),
    ("文件服务与资源", "book/12-services-assets.md"),
    ("在浏览器中运行", "book/13-web.md"),
    ("测试、诊断与发布", "book/14-testing-packaging.md"),
    ("从 Flet 迁移", "book/15-flet-migration.md"),
    ("阅读 API 参考", "book/16-api-reference.md"),
    ("架构与扩展 Saturn", "book/17-architecture.md"),
]

REFERENCE_GUIDES = [
    ("Page 属性、事件与字体", "page.md"),
    ("原生桌面窗口", "window.md"),
    ("子窗口与路由", "subpages.md"),
    ("渲染器与 GPU 选择", "rendering.md"),
    ("Web 会话", "web.md"),
    ("GLSL 着色器", "shaders.md"),
    ("Material 3 Expressive", "expressive.md"),
    ("Compose 命名空间与验证", "compose.md"),
    ("Orb GLSL 示例", "orb.md"),
    ("窗口、Shader 与特效示例", "effects-demos.md"),
    ("截图画廊", "gallery.md"),
    ("Flet 功能映射", "flet-mapping.md"),
    ("控件参数比较", "control-parameters-comparison.md"),
    ("Page 属性与兼容性差异", "page-properties-comparison.md"),
    ("saturn.run 与 Flet.run", "run-comparison.md"),
]

DESCRIPTIONS = {
    "Subpage": "Owned native child window with Page controls, independent rendering and shared application routing; see the Subpage guide.",
    "Shader": "Built-in effects or custom GLSL fragment backgrounds on OpenGL and Vulkan; see the Shader guide.",
    "ShaderEffect": "Built-in procedural effects supported by OpenGL and Vulkan.",
    "ShaderBuffer": "One additive instanced GPU pass sampled by a Shader's final fragment; see the Shader guide.",
    "Compose": "Namespace for Saturn's Material 3 Expressive controls and theme; see the Compose guide for migration details.",
    "App": "Application object that manages windows, events, and rendering.",
    "Renderer": "Selects the software, OpenGL, or Vulkan backend.",
    "Render": "Compatibility alias for Renderer.",
    "run": "Starts a Saturn app and passes its Page to the entry point.",
    "RenderFailedEvent": "Reports a failed GPU startup request and recovery to software rendering.",
    "RenderReadyEvent": "Reports the actual backend and GPU after initialization or software recovery.",
    "FontOptimizeEvent": "Reports background font load/weight optimization start, completion or failure.",
    "ControlEvent": "Event data received by a control callback.",
    "KeyboardEvent": "Pressed key and modifier flags supplied to a Page keyboard handler.",
    "PageResizeEvent": "Logical client dimensions supplied to a Page resize handler.",
    "PlatformBrightnessChangeEvent": "System light/dark preference supplied to a Page brightness handler.",
    "WindowEvent": "Native desktop window state event with its owning Page.",
    "WindowEventType": "Kinds of native window state events.",
    "WindowResizeEdge": "Native edge or corner used to start resizing a window.",
    "Control": "Base class for visual controls, with size, state, and update methods.",
    "Page": "Application page that manages controls, themes, and dialogs.",
    "Window": "Native desktop window properties, events, and operating-system handles.",
    "Text": "Displays text with configurable size, weight, and color.",
    "Row": "Arranges child controls horizontally.",
    "Column": "Arranges child controls vertically.",
    "Container": "Adds spacing, background, borders, and other decoration to a child.",
    "Stack": "Places child controls in overlapping layers.",
    "Icon": "Displays a Material icon.",
    "Image": "Displays a local image or SVG.",
    "Card": "Content container with a surface and shadow.",
    "ListView": "Scrollable list of controls.",
    "GestureDetector": "Receives pointer and gesture events.",
    "Divider": "Draws a dividing line between adjacent content.",
    "ListItem": "Displays a row with a title, supporting text, and optional slots.",
    "Button": "Basic clickable button.",
    "ElevatedButton": "Button with a subtle shadow for ordinary actions.",
    "FilledButton": "Prominent button filled with the theme's primary color.",
    "FilledTonalButton": "Button filled with a softer container color.",
    "OutlinedButton": "Button whose outline emphasizes its boundary.",
    "TextButton": "Low emphasis button presented as text.",
    "IconButton": "Compact action button presented as an icon.",
    "ExpressiveButton": "Material Expressive button with changing size and shape.",
    "ExpressiveIconButton": "Icon button with Expressive size and shape changes.",
    "SplitButton": "Button with separate primary and secondary actions.",
    "ButtonGroup": "Arranges several buttons as one interactive group.",
    "ToggleButton": "Button that switches between selected and unselected states.",
    "ElevatedToggleButton": "Toggle button with an elevated surface.",
    "FilledTonalToggleButton": "Toggle button with a soft filled style.",
    "OutlinedToggleButton": "Toggle button with an outlined style.",
    "FloatingActionButton": "Floating button that highlights a page's primary action.",
    "SmallFloatingActionButton": "Small floating action button.",
    "MediumFloatingActionButton": "Medium floating action button.",
    "LargeFloatingActionButton": "Large floating action button.",
    "ExtendedFloatingActionButton": "Floating action button with an icon and text.",
    "FloatingToolbar": "Floating toolbar that holds actions in a capsule surface.",
    "HorizontalFloatingToolbar": "Floating toolbar with horizontally arranged actions.",
    "VerticalFloatingToolbar": "Floating toolbar with vertically arranged actions.",
    "FloatingActionButtonMenu": "Menu of actions expanded from a floating button.",
    "FloatingActionButtonMenuItem": "Clickable item in a floating action menu.",
    "TextField": "Editable text input field.",
    "Checkbox": "Input control that can be checked independently.",
    "Switch": "Sliding on/off toggle.",
    "Radio": "Single choice in a mutually exclusive group.",
    "RadioGroup": "Manages the selected value among Radio controls.",
    "Dropdown": "Selects a value from a list of options.",
    "Slider": "Selects a value in a range by dragging a thumb.",
    "AlertDialog": "Displays a modal dialog on the page.",
    "SnackBar": "Displays brief feedback about an action.",
    "ProgressBar": "Shows determinate or indeterminate progress as a horizontal bar.",
    "ProgressRing": "Shows determinate or indeterminate progress as a ring.",
    "LoadingIndicator": "Shows ongoing activity with an animated shape.",
    "WavyProgressIndicator": "Shows progress with a wave stroke.",
    "LinearWavyProgressIndicator": "Linear wavy progress indicator.",
    "CircularWavyProgressIndicator": "Circular wavy progress indicator.",
    "FilePicker": "Opens system file selection and save dialogs.",
    "Colors": "Collection of theme and fixed color names.",
    "Icons": "Collection of Material icon names.",
    "Theme": "Defines page colors and appearance.",
    "MaterialExpressiveTheme": "Material Expressive color theme.",
    "parse_color": "Parses a color name, hex value, or color object into RGBA values.",
    "DropdownOption": "Data option displayed by a Dropdown.",
    "Option": "Short alias for DropdownOption.",
    "FilePickerFile": "Information about one file returned by the file picker.",
    "FilePickerFileType": "Limits the types of files that can be selected.",
    "FilePickerResultEvent": "Result event from a file selection or save operation.",
    "FilePickerUploadEvent": "File upload progress or error event.",
    "FilePickerUploadFile": "Upload destination and request method for a file.",
    "Alignment": "Horizontal and vertical alignment of a child in a container.",
    "Animation": "Duration and curve for a property change animation.",
    "AnimationCurve": "How animation speed changes over time.",
    "Border": "Border settings for each of the four sides.",
    "BorderRadius": "Corner radii for each of the four corners.",
    "BorderSide": "Width and color of one border side.",
    "BoxFit": "How an image scales or crops within a space.",
    "BoxShadow": "Spread, blur, color, and offset of a control shadow.",
    "CrossAxisAlignment": "Alignment of children on the layout's cross axis.",
    "Duration": "Animation or wait time in milliseconds and other units.",
    "FontWeight": "Selects a text font weight.",
    "KeyboardType": "Preferred input keyboard type for a text field.",
    "LabelPosition": "Position of a selection control's label.",
    "MainAxisAlignment": "Arrangement on a Row or Column's main axis.",
    "Margin": "Space outside a control on each side.",
    "Offset": "Two-dimensional displacement and its hit-test behavior.",
    "Padding": "Space inside a control on each side.",
    "ScrollMode": "Selects scrolling behavior.",
    "OutlineInputBorder": "Outline appearance of a form input field.",
    "Rotate": "Rotation angle and center of a control.",
    "Scale": "Horizontal and vertical scale of a control.",
    "TextAlign": "Horizontal alignment of text within the available width.",
    "ThemeMode": "Selects light, dark, or system theme mode.",
    "TextOverflow": "How to handle text beyond the available space.",
    "TextStyle": "Combines text size, weight, color, spacing, and other styles.",
    "Tooltip": "Configures a hint shown on hover or long press.",
    "TooltipTriggerMode": "Interaction that triggers a tooltip.",
}

METHOD_DESCRIPTIONS = {
    ("Window", "center"): "Queue centering within the nearest monitor's work area.",
    ("Window", "wait_until_ready_to_show"): "Wait until earlier UI queue operations have completed.",
    ("Window", "to_front"): "Queue native window activation.",
    ("Window", "start_dragging"): "Begin native Windows caption dragging when movement is enabled.",
    ("Window", "start_resizing"): "Begin native Windows resizing at the requested edge.",
    "add": "Adds a child control to the end of a page or control list.",
    "all": "Creates the same setting for every side.",
    "center": "Creates a centered alignment value.",
    "clean": "Removes all regular controls from the page.",
    "client_size_for_outer": "Converts outer window dimensions to client area dimensions.",
    "close": "Closes a window or expanded menu.",
    "destroy": "Destroys the native window and releases resources.",
    "draw": "Requests a draw of the current page.",
    "focus": "Gives the control input focus.",
    "get_directory_path": "Opens the system directory picker.",
    "handle_event": "Handles an incoming control event.",
    "horizontal": "Sets the two horizontal values.",
    "insert": "Inserts a child control at a specified position.",
    "logical_point": "Converts physical coordinates to logical coordinates.",
    "mark_dirty": "Marks the interface for redrawing.",
    "none": "Creates settings with no visible border.",
    "only": "Sets values for specified sides individually.",
    "physical_size_for_logical": "Converts logical dimensions to physical pixels.",
    "pick_files": "Opens the system file picker.",
    "pointer_down": "Handles a pointer press.",
    "pointer_move": "Handles pointer movement.",
    "pointer_up": "Handles a pointer release.",
    "pop_dialog": "Closes the current dialog or snackbar.",
    "remove": "Removes a specified control from its container.",
    "remove_at": "Removes a child control by index.",
    "run_until_closed": "Processes window events until the window closes.",
    "save_file": "Opens the system save-file dialog.",
    "scroll_to": "Scrolls to a position or by a specified distance.",
    "show_dialog": "Shows a dialog or snackbar on the page.",
    "start": "Starts the application window and event handling.",
    "symmetric": "Sets symmetric horizontal and vertical values.",
    "toggle": "Switches between expanded and collapsed states.",
    "update": "Requests a redraw of this control and its changes.",
    "upload": "Uploads selected files to the given destination.",
    "vertical": "Sets the two vertical values.",
    "zero": "Creates a setting with zero on all four sides.",
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
        summary = detail[0] if detail else METHOD_DESCRIPTIONS.get(
            (obj.__name__, name), METHOD_DESCRIPTIONS.get(name, "Performs the corresponding operation."))
        rows.append(f"| {markdown_code(name + signature)} | {summary.replace('|', '\\|')} |")
    return rows


def parameter_rows(name: str, obj: object) -> list[str]:
    try:
        signature = inspect.signature(obj)
    except (TypeError, ValueError):
        return []
    rows = []
    for param in signature.parameters.values():
        if param.name in ("self", "cls") or param.name.startswith("_"):
            continue
        annotation = "—" if param.annotation is inspect.Signature.empty else str(param.annotation).strip("'")
        default = ("additional keyword arguments" if param.kind is inspect.Parameter.VAR_KEYWORD else
                   "additional positional arguments" if param.kind is inspect.Parameter.VAR_POSITIONAL else
                   "required" if param.default is inspect.Signature.empty else repr(param.default))
        label = param.name
        if param.kind is inspect.Parameter.VAR_POSITIONAL:
            label = "*" + label
        elif param.kind is inspect.Parameter.VAR_KEYWORD:
            label = "**" + label
        explanation = describe(name, param.name).replace("|", "\\|")
        if param.name in getattr(obj, "__unsupported_parameters__", set()):
            explanation = "Unsupported for non-default requests. " + explanation
        rows.append(f"| {markdown_code(label)} | {markdown_code(annotation)} | {markdown_code(default)} | {explanation} |")
    return rows


def page_for(name: str, category: str) -> str:
    obj = getattr(saturn, name)
    relative, line = source_info(obj)
    doc = (getattr(obj, "__doc__", None) or "").splitlines()
    summary = DESCRIPTIONS.get(name) or (doc[0] if doc else f"Public Saturn API for {name}.")
    lines = [f"# {name}", "", summary, "", "[← API index](./README.md)", ""]
    if relative:
        source = f"../../{relative}"
        lines += [f"Source: [{markdown_code(relative)}]({source})" + (f" (line {line})" if line else "") + ".", ""]

    if name in EXAMPLES:
        screenshot = f"../../.static/controls/{name}.png"
        snippet = textwrap.indent(EXAMPLES[name], "    ")
        lines += [
            "## Preview", "", f"![{name} control in the dark theme]({screenshot})", "",
            "## Example", "", "Run this code from the repository root to display the control shown above.", "",
            "```python", "import saturn", "", "", "def main(page: saturn.Page):",
            "    page.window.width = 720", "    page.window.height = 360",
            "    page.theme_mode = saturn.ThemeMode.DARK",
            "    page.bgcolor = saturn.Colors.SURFACE",
            "    page.padding = 40", snippet, "    page.update()", "",
            "", "saturn.run(main, backend=saturn.Renderer.SOFTWARE)",
            "```", "",
        ]

    if inspect.isclass(obj):
        bases = [base.__name__ for base in obj.__bases__ if base is not object and base.__name__ != name]
        if bases:
            links = [f"[{base}](./{base}.md)" if base in saturn.__all__ and base != name else markdown_code(base) for base in bases]
            lines += ["**Base class:** " + ", ".join(links), ""]
        if obj.__name__ != name:
            lines += [f"The public name `saturn.{name}` refers to the implementation class `{obj.__name__}`.", ""]
        if issubclass(obj, enum.Enum):
            members = list(obj.__members__.items())
            lines += ["## Members", ""]
            if len(members) > 80:
                lines += [f"There are {len(members)} names. The first 20 appear below; see the source for the full list.", ""]
                members = members[:20]
            lines += ["| Name | Value |", "| --- | --- |"]
            lines += [f"| {markdown_code(key)} | {markdown_code(item.value)} |" for key, item in members]
            lines.append("")
            if members:
                lines += [f"Use members by name, for example `saturn.{name}.{members[0][0]}`.", ""]
            return "\n".join(lines)
        elif name in ("Colors", "Icons"):
            names = [key for key in vars(obj) if key.isupper()]
            lines += ["## Available names", "", f"There are {len(names)} names. Examples: " + ", ".join(markdown_code(key) for key in names[:16]) + ".", "", "See the source above for the full list; color values resolve according to the theme." if name == "Colors" else "See the source above for the full icon list.", ""]
        else:
            if name == "Page":
                lines += ["## Renderer settings", "",
                          "`page.renderer.anti_aliasing` and `page.renderer.vsync` are boolean settings",
                          "that default to `True`. `page.renderer.context` exposes the active backend renderer.",
                          "`page.renderer.name` reports `software`, `opengl` or `vulkan`, or `None` before startup.",
                          "Read-only `.gpu_name`, `.gpu_index` and `.gpus` expose the actual device and available choices; select with `saturn.run(..., gpu=...)`.",
                          "`page.on_render_failed`, `.on_render_ready` and `.on_font_optimize` report startup recovery and background font work.",
                          "See [Renderer settings](../rendering.md) for backend behavior and threading rules.", ""]
                lines += ["See [Page fonts and events](../page.md) for font registration, typed callbacks, themes, and ownership.", ""]
                lines += ["## Automatic updates", "",
                          "`page.auto_update` is a boolean property that defaults to `True`. Set it to",
                          "`False` to pause implicit control redraws and animation frame scheduling. Call",
                          "`page.update()` or `page.repaint()` for an explicit frame; setting it back to",
                          "`True` requests one frame.", ""]
            if name == "Window":
                lines += ["See [Native desktop windows](../window.md) for property behavior, platform limits, handles, and close interception.", ""]
            if name in ("App", "Page", "Window"):
                lines += ["> `saturn.run()` usually creates and passes these objects; application code does not need to construct them directly.", ""]
            methods = method_rows(obj)
            if methods:
                lines += ["## Public methods", "", "| Method | Description |", "| --- | --- |", *methods, ""]
    try:
        public_signature = inspect.signature(obj)
        signature = str(public_signature.replace(parameters=[p for p in public_signature.parameters.values()
                                                               if not p.name.startswith("_")]))
    except (TypeError, ValueError):
        signature = "(...)"
    heading = "Constructor parameters" if inspect.isclass(obj) else "Call parameters"
    lines += [f"## {heading}", "", "```python", f"saturn.{name}{signature}", "```", ""]
    params = parameter_rows(name, obj)
    if params:
        lines += ["| Parameter | Type annotation | Default | Description |", "| --- | --- | --- | --- |", *params, ""]
        if inspect.isclass(obj) and "**base" in signature:
            lines += ["`**base` accepts [common Control constructor parameters](./Control.md#constructor-parameters), such as `width`, `height`, and `visible`.", ""]
    else:
        lines += ["No parameters are required.", ""]
    return "\n".join(lines)


def summary_content() -> str:
    """Build the mdBook table of contents from the public API catalog."""
    lines = ["# Summary", "", "[Saturn 使用手册](README.md)", ""]
    lines.extend(f"- [{title}]({path})" for title, path in BOOK_CHAPTERS)
    lines += ["", "# API 参考", "", "- [API index](api/README.md)"]
    for category, names in CATEGORIES.items():
        lines.extend(
            f"- [{category}: {name}](api/{name}.md)"
            for name in names.split()
        )
    lines += ["", "# 专题指南", ""]
    lines.extend(f"- [{title}]({path})" for title, path in REFERENCE_GUIDES)
    return "\n".join(lines) + "\n"


def main() -> None:
    API.mkdir(parents=True, exist_ok=True)
    listed = {name for names in CATEGORIES.values() for name in names.split()}
    public = set(saturn.__all__)
    if listed != public:
        raise SystemExit(f"Catalog mismatch: missing={sorted(public - listed)}, extra={sorted(listed - public)}")
    visual = set().union(*(set(CATEGORIES[key].split()) for key in
                           ("Layout and content", "Buttons and actions", "Input and feedback"))) - {"DropdownOption", "Option"}
    visual.discard("DialogControl")
    if set(EXAMPLES) != visual:
        raise SystemExit(f"Control examples mismatch: missing={sorted(visual - set(EXAMPLES))}, extra={sorted(set(EXAMPLES) - visual)}")
    missing_images = [name for name in EXAMPLES if not (ROOT / ".static" / "controls" / f"{name}.png").exists()]
    if missing_images:
        raise SystemExit(f"Control images missing: {missing_images}")
    for category, names in CATEGORIES.items():
        for name in names.split():
            (API / f"{name}.md").write_text(page_for(name, category), encoding="utf-8")
    lines = ["# Saturn API reference", "", "[← Saturn 使用手册](../README.md) · [Screenshot gallery](../gallery.md)", "", f"This reference covers the {len(public)} public symbols currently exported by saturn.__all__, with one Markdown page per symbol. Visual control pages include a summary, dark theme screenshot, runnable example, and constructor parameter descriptions. Other type and service pages document their actual interfaces.", ""]
    for category, names in CATEGORIES.items():
        lines += [f"## {category}", "", " · ".join(f"[{name}](./{name}.md)" for name in names.split()), ""]
    lines += ["## Relationship to the Flet knowledge base", "", "The categories follow the local `flet-skill/` reference, but this index lists only symbols actually exported by Saturn. Other controls, services, or properties in the Flet reference may not be implemented in Saturn.", ""]
    (API / "README.md").write_text("\n".join(lines), encoding="utf-8")
    (OUT / "SUMMARY.md").write_text(summary_content(), encoding="utf-8")
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
    print(f"Wrote {len(public)} API pages, index, and book summary to {API}")


if __name__ == "__main__":
    main()
