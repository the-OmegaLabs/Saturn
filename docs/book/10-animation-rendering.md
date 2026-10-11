# 动画与渲染后端

Saturn 的动画可以通过 animate_* 属性描述，也可以使用控件和 Expressive
控件内置的状态动画。绘制后端由 saturn.run 的 backend 参数选择。

## 属性动画

控件支持 opacity、size、position、align、margin、rotation、scale 和 offset
的动画配置：

~~~python
panel = saturn.Container(
    saturn.Text("Animated"),
    width=240,
    height=120,
    bgcolor=saturn.Colors.PRIMARY_CONTAINER,
    animate_opacity=saturn.Animation(
        duration=saturn.Duration(milliseconds=250),
        curve=saturn.AnimationCurve.EASE_OUT,
    ),
)
page.add(panel)

panel.opacity = 0.3
panel.update()
~~~

动画发生在目标值改变后。Duration 可以使用 milliseconds、seconds 等字段；
AnimationCurve 决定插值速度。动画完成后可使用 on_animation_end。

旋转、缩放和 offset 既影响绘制也影响命中测试，除非对应类型关闭
transform_hit_tests。GPU 旋转裁剪使用保守的轴对齐范围。

## 选择后端

~~~python
saturn.run(main, backend=saturn.Renderer.SOFTWARE)
saturn.run(main, backend=saturn.Renderer.OPENGL)
saturn.run(main, backend=saturn.Renderer.VULKAN)
~~~

OpenGL 是支持最完整的 GPU 后端；Software 便于在没有 GPU 或需要稳定诊断
时运行；Vulkan 仍是实验性后端。运行中的实际后端从
page.renderer.name 读取：

~~~python
def main(page):
    print(page.renderer.name)
~~~

renderer.anti_aliasing 和 renderer.vsync 都是布尔设置，默认开启。更改它们
会排队到 UI 线程并可能触发重新布局或交换链重建。

## GPU 选择和回退

~~~python
saturn.run(main, backend=saturn.Renderer.VULKAN, gpu="Intel")
saturn.run(main, backend=saturn.Renderer.VULKAN, gpu=1)
~~~

gpu 可以是设备名称、唯一子串或索引。实际设备从 gpu_name、gpu_index 和
gpus 读取。选择无效或初始化失败时，应用可能回退到软件后端：

~~~python
def report(event):
    print(event.backend, event.error)


page.on_render_failed = report
page.on_render_ready = lambda event: print(event.backend, event.fallback)
~~~

回退是启动恢复机制，不会在运行期间替换一个已经失败的着色器或任意绘制
调用。应用应该为 Software 后端准备可见的 fallback 行为。

## 着色器

Shader 可以使用内置 ShaderEffect，也可以传入 GLSL 字符串或 Path。GPU 后端
执行自定义片段；Software 后端绘制 fallback_color。详细的 uniform、include、
缓冲区和错误处理见[着色器章节](../shaders.md)。

## 本章要点

动画改变的是控件状态，renderer 决定状态如何绘制。先用 Software 验证布局
和事件，再用 OpenGL 或 Vulkan 验证 GPU 效果。不要把 UI 线程当作耗时计算线程。
