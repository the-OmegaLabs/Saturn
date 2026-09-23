# Flet mapping and scope

[← Documentation home](./README.md) · [API index](./api/README.md)

`flet-skill/` is a local Flet 1.x knowledge base for looking up Flet itself. `docs/` covers only the symbols Saturn exports in `saturn.__all__`. The similar categories help navigation, but the Saturn API pages and source define actual coverage.

| Familiar Flet concept | Saturn entry | Current use |
| --- | --- | --- |
| App entry point `run()` and `Page` | [run](./api/run.md), [Page](./api/Page.md) | Create windows and pages; add controls |
| `Row`, `Column`, `Container` | [Layout types](./api/README.md#layout-and-content) | Arrange and decorate controls |
| `Text`, `Icon`, `Image` | [Content types](./api/README.md#layout-and-content) | Display text, icons, and images |
| `Button` and variants | [Button types](./api/README.md#buttons-and-actions) | Ordinary and Expressive actions |
| Input and feedback | [Input and feedback](./api/README.md#input-and-feedback) | Text, selection, progress, and dialogs |
| Themes and types | [Styles and types](./api/README.md#styles-and-types) | Colors, enums, animations, and borders |
| `FilePicker` | [FilePicker](./api/FilePicker.md) | Select and save local files |

When migrating, first replace the import and run an example, then check constructor parameters, event data, and rendering results one by one. Saturn's `Control` constructor accepts extra Flet-style keywords, but these do not all produce visual or interactive effects. Check each control's implementation and screenshots.

Saturn currently targets local desktop apps. It does not provide Flet's full set of web and mobile features, platform services, or controls.
