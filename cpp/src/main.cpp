#include "saturn/app.hpp"
#include "saturn/page.hpp"
#include "saturn/control.hpp"
#include "saturn/types.hpp"
#include <memory>
int main() {
  return saturn::run([](saturn::Page& page) {
    page.set_title("Saturn C++ hello");
    auto message = std::make_unique<saturn::Text>("Hello from Saturn");
    saturn::Text* message_ptr = message.get();
    page.add(std::move(message));
    page.add(std::make_unique<saturn::FilledButton>("Click me", [message_ptr]() {
      message_ptr->set_value("It works.");
    }));
  });
}
