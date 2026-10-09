#pragma once
#include <functional>
#include <memory>
namespace saturn {
class Page;
class App {
public:
  // `w`,`h` = logical client size (SDL CreateWindow). `demo_contract` arms the
  // SATURN_SHOT size check (also armed by SATURN_DEMO_CONTRACT env). Do NOT
  // infer contract from window dimensions alone.
  explicit App(int w = 800, int h = 600, bool demo_contract = false);
  ~App();
  App(const App&) = delete;
  App& operator=(const App&) = delete;
  Page& page();
  int run();
private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
};
using MainFn = std::function<void(Page&)>;
int run(MainFn main_fn, int w = 800, int h = 600, bool demo_contract = false);
}
