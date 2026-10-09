#include "saturn/app.hpp"
#include "saturn/page.hpp"
#include "saturn/renderer.hpp"
#include "saturn/window.hpp"
#include "saturn/types.hpp"
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
  while (!impl_->window.poll_quit()) {
    r.clear(Color{0x12, 0x12, 0x14, 0xff});
    // Phase-2 smoke: one filled rect (hello chrome). Widgets come in phase 4.
    r.fill_rect(Rect{40, 40, 240, 120}, Color{0x4f, 0x46, 0xe5, 0xff}, 0);
    impl_->window.swap();
    SDL_Delay(16);
  }
  return 0;
}
int run(MainFn main_fn, int w, int h) {
  App app(w, h);
  if (main_fn) main_fn(app.page());
  return app.run();
}
}
