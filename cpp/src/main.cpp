#include "saturn/app.hpp"
#include "saturn/page.hpp"
#include "saturn/control.hpp"
#include "saturn/types.hpp"
#include <memory>
int main() {
  return saturn::run([](saturn::Page& page) {
    page.set_title("Saturn C++ hello");
    page.add(std::make_unique<saturn::Text>("Hello from Saturn"));
    page.add(std::make_unique<saturn::FilledButton>("Click me", [&page]() {
      // Replace first child text if present via update path: add status text once.
      page.add(std::make_unique<saturn::Text>("It works."));
      page.update();
    }));
  });
}
