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
  int w, h;
  explicit Impl(int w, int h) : window("Saturn", w, h), w(w), h(h) {}
};
App::App(int w, int h) : impl_(std::make_unique<Impl>(w, h)) {}
App::~App() = default;
Page& App::page() { return impl_->page; }
int App::run() {
  auto& r = impl_->window.renderer();
  impl_->page.layout(float(impl_->w), float(impl_->h));
  while (!impl_->window.poll_quit()) {
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
