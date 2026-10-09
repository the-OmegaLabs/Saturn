#pragma once
#include <functional>
#include <memory>
namespace saturn {
class Page;
class App {
public:
  explicit App(int w = 800, int h = 600);
  ~App();
  App(const App&) = delete;
  App& operator=(const App&) = delete;
  Page& page();
  int run(); // ① empty clear loop until quit
private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
};
using MainFn = std::function<void(Page&)>;
int run(MainFn main_fn, int w = 800, int h = 600);
}
