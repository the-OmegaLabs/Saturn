# The Saturn Handbook

This handbook is for Python developers who want to build applications with Saturn, organized in an order similar to
[The Rust Book](https://doc.rust-lang.org/book/): first open a
window, then understand the Page and the control tree, and then gradually add layout, events, state, input,
theme, navigation, and rendering.

Saturn's concepts and naming draw on the [Flet documentation](https://flet.dev/docs/), but Saturn
is an independent Python desktop UI framework. The examples only use APIs actually exported by this repository. When you encounter a
control with the same name as a Flet control, defer to Saturn's implementation and the [API reference](./api/README.md).

> Saturn is currently in the alpha stage; the public API and feature coverage may still change. The handbook explains
> feature boundaries and does not automatically treat names from the Flet documentation as capabilities Saturn has implemented.

## Where to start

If this is your first time using Saturn, start with [Installation and Running](./book/01-installation.md).
When the dependencies are already set up, go straight to [Project scaffold: the first window](./getting-started.md),
then continue in the chapter order below.

## The Saturn Handbook

### Getting started

1. [What is Saturn](./book/00-introduction.md)
2. [Installation and Running](./book/01-installation.md)
3. [Project scaffold: the first window](./getting-started.md)
4. [Page, the Control Tree, and Updates](./book/03-page-control-tree.md)

### Building interfaces

5. [Layout: Row, Column, Stack, and Container](./book/04-layout.md)
6. [Events and State](./book/05-events-state.md)
7. [Inputs, Forms, and Feedback](./book/06-inputs.md)
8. [Theme, Colors, and Fonts](./book/07-theme.md)
9. [Lists, Scrolling, and Performance](./book/08-lists.md)

### Building applications

10. [Navigation and Native Subwindows](./book/09-navigation-windows.md)
11. [Animation and Render Backends](./book/10-animation-rendering.md)
12. [Material 3 Expressive](./book/11-expressive.md)
13. [File Services and Assets](./book/12-services-assets.md)
14. [Running in the Browser](./book/13-web.md)
15. [Testing, Diagnostics, and Release](./book/14-testing-packaging.md)

### Migration and reference

16. [Migrating from Flet](./book/15-flet-migration.md)
17. [Reading the API Reference](./book/16-api-reference.md)
18. [Architecture and Extending Saturn](./book/17-architecture.md)

Every chapter tries to provide copy-paste-runnable code. Chapters only rely on concepts introduced earlier; when you need the full
constructor signatures, properties, and methods, jump to the API reference.

## Common entry points

| Goal | Documentation |
| --- | --- |
| Open a window in five minutes | [Project scaffold](./getting-started.md) |
| Find a control or type | [API index](./api/README.md) |
| View screenshots and examples | [Gallery](./gallery.md) |
| Configure native windows | [Native windows](./window.md) |
| Choose a backend or GPU | [Renderer settings](./rendering.md) |
| Create an Expressive UI | [Compose](./compose.md) |
| Share browser sessions | [Web sessions](./web.md) |
| Write GLSL backgrounds | [Shaders](./shaders.md) |
| Review Flet differences | [Flet mapping](./flet-mapping.md) |
| Understand the platform split | [Platform adapters](./platform-adapters.md) |
| Assess the Linux desktop roadmap | [Linux desktop roadmap](./linux-desktop-roadmap.md) |

## Reading and generating locally

These chapters are plain Markdown and can be read directly on GitHub or in an editor.
SUMMARY.md is the mdBook table of contents file.

Run the following command to regenerate the source-driven API pages and the catalog:

~~~powershell
python tools/build_saturn_docs.py
~~~

The generator does not overwrite the hand-written chapters of this handbook.
