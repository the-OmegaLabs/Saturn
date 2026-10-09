#include "saturn/app.hpp"
#include "saturn/page.hpp"
#include "saturn/renderer.hpp"
#include "saturn/window.hpp"
#include "saturn/types.hpp"
#include "saturn/font.hpp"
#include <SDL3/SDL.h>
namespace saturn {
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
  impl_->page.layout(float(impl_->window.width()), float(impl_->window.height()));
  while (!impl_->window.poll_quit()) {
    if (impl_->window.consume_resized(nullptr, nullptr) || impl_->page.layout_dirty()) {
      impl_->page.layout(float(impl_->window.width()), float(impl_->window.height()));
    }
    for (const auto& pe : impl_->window.take_pointer_events()) {
      impl_->page.dispatch_pointer(pe);
    }
    r.clear(Color{0x12, 0x12, 0x14, 0xff});
    impl_->page.paint(r);
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
