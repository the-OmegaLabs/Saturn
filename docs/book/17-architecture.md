# Architecture and Extending Saturn

Application development usually only needs Page, Control, and the public widgets. Understanding these layers helps
with troubleshooting, and also helps experienced developers contribute implementations to the project.

## The runtime layer

saturn.run creates an App in the application process, starts the pygame/SDL window and the chosen renderer,
then creates the Page and calls the entry callback. The App manages the UI event loop, the command queue, a background asyncio
loop, multiple subwindows, and the renderer lifecycle.

The main callback and control events are not SDL draw hooks. Ordinary code should modify control state and call
update; only renderer implementations and the platform adapter layer should use the GPU, SDL, or native handles directly.

## The control layer

Control provides layout sizing, visible and disabled states, transforms, updating, and lifecycle. Subclasses in widgets
define content, drawn geometry, child nodes, and input responses. Page hands the control tree to the layout system,
then hands the draw commands to the Software or GPU renderer.

The control tree has a single owner. Attaching and removing synchronizes the page and parent references; reusing the same
control instance in different windows causes ownership errors.

## The drawing layer

The Software renderer provides a drawing path that does not need an OpenGL context. OpenGL and Vulkan
use the GPU pipeline to handle geometry, textures, clipping, and some effects. Text, images, and SVG require
source textures or font rasterization, so a "GPU renderer" does not mean there is no CPU preparation work.

Shader is one of the public GPU drawing entry points, not a post-processing filter for all controls. Custom GLSL
requires a GPU renderer; Software only draws the fallback.

## Where to start making changes

- New public type: implement the control/type, export it from saturn.__init__, update the API categories;
- New constructor parameter: update the control implementation, parameter descriptions, and the relevant comparison tables;
- New control example: edit tools/control_examples.py and generate preview screenshots;
- Hand-written user guides: put them in docs/ or docs/book/, not in the generated docs/api pages;
- Renderer or event changes: add tests covering real behavior, and check the applicability across Software, OpenGL,
  and Vulkan.

The API documentation generator validates the public symbol catalog, the control example collection, images, and Markdown links.
Run it when modifying exported APIs to keep the documentation index and the source from drifting apart.

## The optional Web runtime

saturn.web reuses Page and a subset of the Control API, but has its own FastAPI app, session registry,
serialized scenes, and browser Canvas renderer. Desktop and Web are not the same drawing backend; the fact that a
Control works on desktop does not mean Web has its serialization and input adapters.

## Key points of this chapter

The public API is implemented jointly by the runtime, the control tree, and the renderer. When extending, keep the layers clean: leave
semantics in Control/Widget, put platform-specific operations in the appropriate adapter layer, and explain the final behavior with user-facing
guides.
