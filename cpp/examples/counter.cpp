#include "saturn/app.hpp"
#include "saturn/colors.hpp"
#include "saturn/control.hpp"
#include "saturn/page.hpp"
#include <memory>
#include <string>

int main() {
  return saturn::run([](saturn::Page& page) {
    page.set_title("Saturn Counter");
    page.set_padding(24.f);
    auto column = std::make_unique<saturn::Column>(16.f);
    saturn::ControlOptions logo_size;
    logo_size.width = 104.f;
    logo_size.height = 84.f;
    column->add(std::make_unique<saturn::SaturnLogo>(saturn::colors::kPrimary,logo_size));
    auto text = std::make_unique<saturn::Text>("Count: 0");
    // Non-owning observer; Page -> Column owns Text throughout callback lifetime.
    saturn::Text* output = text.get();
    column->add(std::move(text));
    column->add(std::make_unique<saturn::FilledButton>(
        "Increment",[output,count = 0]() mutable {
          output->set_value("Count: "+std::to_string(++count));
        }));
    page.add(std::move(column));
  },640,480);
}
