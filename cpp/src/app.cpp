#include "saturn/app.hpp"
#include "saturn/page.hpp"
#include "saturn/renderer.hpp"
#include "saturn/window.hpp"
#include "saturn/types.hpp"
#include "saturn/font.hpp"
#include "saturn/limits.hpp"
#include "saturn/demo_size.hpp"
#include <SDL3/SDL.h>
#include <cstdlib>
#include <cstring>
#include <stdexcept>
#include <string>
#include <vector>

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

namespace saturn {
namespace {
bool write_png_rgba(const char* path, int w, int h, const std::uint8_t* rgba) {
  if (!path || !rgba || w <= 0 || h <= 0) return false;
  std::size_t n = static_cast<std::size_t>(w) * static_cast<std::size_t>(h);
  if (n > kMaxScreenshotPixels) throw std::runtime_error("screenshot exceeds kMaxScreenshotPixels");
  if (std::strlen(path) > kMaxPathBytes) throw std::runtime_error("SATURN_SHOT path too long");
  return stbi_write_png(path, w, h, 4, rgba, w * 4) != 0;
}
} // namespace

struct App::Impl {
  Window window;
  Page page;
  bool demo_contract = false;
  Impl(int w, int h, bool contract) : window("Saturn", w, h), demo_contract(contract) {}
};
App::App(int w, int h, bool demo_contract)
    : impl_(std::make_unique<Impl>(w, h, demo_contract)) {}
App::~App() = default;
Page& App::page() { return impl_->page; }
int App::run() {
  auto& r = impl_->window.renderer();
  if (!impl_->page.title().empty())
    impl_->window.set_title(impl_->page.title());
  // Layout uses LOGICAL client (matches pointer coords). At 100% DPI this
  // equals drawable pixels; under HiDPI they diverge.
  impl_->page.layout(float(impl_->window.client_width()),
                     float(impl_->window.client_height()));

  const char* shot = std::getenv("SATURN_SHOT");
  int shot_after = 3;
  if (const char* frames = std::getenv("SATURN_SHOT_FRAMES")) {
    int v = std::atoi(frames);
    if (v > 0 && v < 10000) shot_after = v;
  }
  int frame = 0;

  while (!impl_->window.poll_quit()) {
    if (impl_->window.consume_resized(nullptr, nullptr) || impl_->page.layout_dirty()) {
      impl_->page.layout(float(impl_->window.client_width()),
                         float(impl_->window.client_height()));
    }
    for (const auto& pe : impl_->window.take_pointer_events()) {
      impl_->page.dispatch_pointer(pe);
    }
    r.clear(impl_->page.bgcolor());
    impl_->page.paint(r);

    if (shot && ++frame >= shot_after) {
      std::vector<std::uint8_t> rgba;
      int sw = 0, sh = 0;
      if (!r.read_pixels_rgba(&rgba, &sw, &sh))
        throw std::runtime_error("screenshot readback unsupported");
      // Contract arms ONLY via saturn_demo (explicit flag) or SATURN_DEMO_CONTRACT.
      // Never auto-arm from outer 960x800 or any coincidental size match.
      const bool demo_contract =
          impl_->demo_contract || (std::getenv("SATURN_DEMO_CONTRACT") != nullptr);
      if (demo_contract) {
        const int cw = impl_->window.client_width();
        const int ch = impl_->window.client_height();
        if (cw != kDemoClientWidth || ch != kDemoClientHeight) {
          throw std::runtime_error(
              "SATURN_SHOT demo contract mismatch: logical client " +
              std::to_string(cw) + "x" + std::to_string(ch) +
              " != kDemoClient " + std::to_string(kDemoClientWidth) + "x" +
              std::to_string(kDemoClientHeight) +
              " (SDL CreateWindow sizes client; Python DEMO_* are outer)");
        }
        // Pixel golden is 944x761 at scale=1. HiDPI (pixels != client) fails
        // loud until scale-aware golden is handled — not silently ignored.
        if (sw != kDemoGoldenPixelWidth || sh != kDemoGoldenPixelHeight) {
          throw std::runtime_error(
              "SATURN_SHOT demo contract mismatch: framebuffer pixels " +
              std::to_string(sw) + "x" + std::to_string(sh) +
              " != golden pixels " + std::to_string(kDemoGoldenPixelWidth) + "x" +
              std::to_string(kDemoGoldenPixelHeight) +
              " (at 100% DPI pixels==client 944x761; HiDPI needs scale handling)");
        }
      }
      if (!write_png_rgba(shot, sw, sh, rgba.data()))
        throw std::runtime_error("failed to write SATURN_SHOT png");
      return 0;
    }

    impl_->window.swap();
    SDL_Delay(16);
  }
  return 0;
}
int run(MainFn main_fn, int w, int h, bool demo_contract) {
  // Fail loud: demo/hello need TTF metrics (not 5x7 bitmap).
  set_default_font(Font::load_default());
  App app(w, h, demo_contract);
  if (main_fn) main_fn(app.page());
  return app.run();
}
}
