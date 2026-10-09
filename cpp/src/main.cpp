#include "saturn/app.hpp"
#include "saturn/page.hpp"
#include "saturn/control.hpp"
#include "saturn/types.hpp"
#include <memory>
int main() {
  return saturn::run([](saturn::Page& page) {
    page.set_title("Saturn C++ hello");
    saturn::ControlOptions opt;
    opt.width = 240.f;
    opt.height = 120.f;
    page.add(std::make_unique<saturn::ColorBox>(
      saturn::Color{0x4f, 0x46, 0xe5, 0xff}, opt));
  });
}
