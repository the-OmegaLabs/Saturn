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
  impl_->page.layout(float(impl_->window.width()), float(impl_->window.height()));
  while (!impl_->window.poll_quit()) {
    int nw = 0, nh = 0;
    if (impl_->window.consume_resized(&nw, &nh) || impl_->page.layout_dirty()) {
      impl_->page.layout(float(impl_->window.width()), float(impl_->window.height()));
    }
    r.clear(Color{0x12, 0x12, 0x14, 0xff});
    impl_->page.paint(r);
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
