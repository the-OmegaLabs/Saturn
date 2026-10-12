# Migrating from Flet

Saturn's API design was inspired by Flet, and many entry points share similar names. When migrating, you can reuse
parts of the application structure, but you cannot assume that all controls, parameters, and runtimes are fully equivalent.

## Swap the entry point first, then verify behavior

The familiar simplified entry point can usually be written like this:

~~~python
import saturn


def main(page: saturn.Page):
    page.add(saturn.Text("Hello"))


saturn.run(main)
~~~

APIs such as Page, Text, Row, Column, Container, and the button family overlap. Check each one:

1. Confirm the name appears in Saturn.__all__;
2. Compare against Saturn's constructor signature and the parameter comparison table;
3. Run the actual event and drawing paths; "construction succeeds" alone is not proof of support;
4. Search for platform services, mobile behavior, routing, lifecycle, and unimplemented properties.

## Page callback migration

Saturn page event callbacks receive event objects. Use event.page to get the Page:

~~~python
def resized(event):
    print(event.width, event.height, event.page.title)


page.on_resize = resized
~~~

If old code passes the Page itself as the argument, change the access to event.page, or use the fields
on PageResizeEvent and KeyboardEvent directly.

## Explicit updates

Controls are usually mutable objects. After modifying a property, call update:

~~~python
label.value = "Updated"
label.update()
~~~

Call page.update() after directly modifying the page's controls list. Most common control callbacks support
a single event argument or a zero-argument function.

## The Compose extension

Material Expressive related types live in saturn.Compose. New code can write explicitly:

~~~python
page.add(saturn.Compose.FilledButton("Save"))
~~~

Standard controls are still imported from saturn. Compose does not mean Flutter Compose; it is Saturn's
Material 3 Expressive control grouping.

## Runtime differences

- saturn.run starts a local desktop window, defaulting to OpenGL; Flet's web/mobile runtime
  is different.
- Saturn is currently validated mainly on Windows, with limited platform services and accessibility coverage.
- Saturn's FilePicker is a local file/directory/save dialog; upload is currently unsupported.
- Some ListView parameters exist, but behaviors such as lazy layout and reverse scrolling need to be checked item by item.
- saturn.web is an optional Canvas/WebSocket runtime, not equivalent to full Flet Web.
- WebGL shaders, browser history, the Flet View stack, and full mobile services are not Saturn features.

## Checking migration boundaries

- [Flet mapping](../flet-mapping.md): conceptual and public name mapping;
- [Parameter comparison](../control-parameters-comparison.md): implemented, missing, and explicitly unsupported parameters;
- [Page differences](../page-properties-comparison.md): events, theme, media, and lifecycle;
- [Compose verification](../compose.md): shared control construction tests and feature gaps.

## Key points of this chapter

Migrate one small but complete user path first, then decide whether to migrate the whole application. Successful construction is not evidence of
behavioral compatibility; UI-critical input, callbacks, scrolling, and visual details should all be tested for real in Saturn.
