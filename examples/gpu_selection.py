"""Select a startup GPU and inspect the actual backend/device.

python examples/gpu_selection.py --backend vulkan --gpu Intel
python examples/gpu_selection.py --backend vulkan --gpu 1
python examples/gpu_selection.py --backend opengl
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import saturn as st


def main(page: st.Page):
    page.window.width = 640
    page.window.height = 360
    renderer = page.renderer
    font_status = st.Text("Font cache: ready")
    def failed(e):
        page.add(st.Text(e.message), st.Text(e.error))
    def optimize(e):
        font_status.value = f"Font {e.operation}: {e.status} ({e.font}, {e.weight})"
        font_status.update()
    page.on_render_failed = failed
    page.on_render_ready = lambda e: print("Renderer ready:", e.backend, e.gpu_name)
    page.on_font_optimize = optimize
    page.add(st.Text(f"Backend: {renderer.name}", size=24),
             st.Text(f"Active GPU: {renderer.gpu_name}"),
             st.Text(f"Device index: {renderer.gpu_index}"),
             st.Text("Available devices in this backend:"),
             *[st.Text(f"{index}: {name}") for index, name in enumerate(renderer.gpus)],
             font_status)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("opengl", "vulkan"), default="vulkan")
    parser.add_argument("--gpu", help="Device name or nonnegative index; omitted uses the default")
    args = parser.parse_args()
    gpu = int(args.gpu) if args.gpu is not None and args.gpu.isdecimal() else args.gpu
    st.run(main, backend=st.Renderer(args.backend), gpu=gpu, title="GPU selection")
