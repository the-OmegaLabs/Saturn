#include "saturn/app.hpp"
#include "saturn/page.hpp"
#include "saturn/renderer.hpp"
#include "saturn/window.hpp"
#include "saturn/types.hpp"
#include "saturn/font.hpp"
#include "saturn/limits.hpp"
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
  explicit Impl(int w, int h) : window("Saturn", w, h) {}
};
App::App(int w, int h) : impl_(std::make_unique<Impl>(w, h)) {}
App::~App() = default;
Page& App::page() { return impl_->page; }
int App::run() {
  auto& r = impl_->window.renderer();
  if (!impl_->page.title().empty())
    impl_->window.set_title(impl_->page.title());
  impl_->page.layout(float(impl_->window.width()), float(impl_->window.height()));

  const char* shot = std::getenv("SATURN_SHOT");
  int shot_after = 3;
  if (const char* frames = std::getenv("SATURN_SHOT_FRAMES")) {
    int v = std::atoi(frames);
    if (v > 0 && v < 10000) shot_after = v;
  }
  int frame = 0;

  while (!impl_->window.poll_quit()) {
    if (impl_->window.consume_resized(nullptr, nullptr) || impl_->page.layout_dirty()) {
      impl_->page.layout(float(impl_->window.width()), float(impl_->window.height()));
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
      if (!write_png_rgba(shot, sw, sh, rgba.data()))
        throw std::runtime_error("failed to write SATURN_SHOT png");
      return 0;
    }

    impl_->window.swap();
    SDL_Delay(16);
  }
  return 0;
}
int run(MainFn main_fn, int w, int h) {
  // Fail loud: demo/hello need TTF metrics (not 5x7 bitmap).
  set_default_font(Font::load_default());
  App app(w, h);
  if (main_fn) main_fn(app.page());
  return app.run();
}
}
