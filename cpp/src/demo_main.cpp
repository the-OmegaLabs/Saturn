#include "saturn/app.hpp"
#include "saturn/colors.hpp"
#include "saturn/control.hpp"
#include "saturn/page.hpp"
#include "saturn/types.hpp"
#include <memory>

namespace {

std::unique_ptr<saturn::Container> make_panel(
    const char* title, std::unique_ptr<saturn::Control> body) {
  saturn::ControlOptions opt;
  opt.width = 440.f;
  auto panel = std::make_unique<saturn::Container>(opt);
  panel->set_bgcolor(saturn::colors::kSurfaceContainerLow);
  panel->set_padding(20.f);
  panel->set_corner_radius(16.f);
  auto col = std::make_unique<saturn::Column>(16.f);
  col->add(std::make_unique<saturn::Text>(
      title, saturn::colors::kOnSurface, 18.f));
  if (body) col->add(std::move(body));
  panel->add(std::move(col));
  return panel;
}

} // namespace

int main() {
  return saturn::run(
      [](saturn::Page& page) {
        page.set_title("saturn demo");
        page.set_bgcolor(saturn::colors::kSurface);
        page.set_padding(24.f);
        page.set_spacing(16.f);

        auto header = std::make_unique<saturn::Row>(12.f);
        header->set_cross_axis_alignment(saturn::CrossAxisAlignment::Center);
        header->add(std::make_unique<saturn::Text>(
            "Saturn Demo", saturn::colors::kOnSurface, 28.f));
        header->add(std::make_unique<saturn::Text>(
            "C++ skeleton", saturn::colors::kOnSurfaceVariant, 12.f));
        page.add(std::move(header));

        auto status = std::make_unique<saturn::Text>(
            "interact with the controls below",
            saturn::colors::kOnSurfaceVariant, 13.f);
        saturn::Text* status_ptr = status.get();
        page.add(std::move(status));

        auto btn_row = std::make_unique<saturn::Row>(8.f);
        btn_row->add(std::make_unique<saturn::FilledButton>(
            "Filled", [status_ptr]() {
              status_ptr->set_value("last event: click");
            }));
        btn_row->add(std::make_unique<saturn::FilledButton>(
            "Placeholder", [status_ptr]() {
              status_ptr->set_value("last event: placeholder");
            }));

        auto left_body = std::make_unique<saturn::Column>(16.f);
        left_body->add(std::move(btn_row));
        left_body->add(std::make_unique<saturn::Text>(
            "TextField / Checkbox / Slider TBD",
            saturn::colors::kOnSurfaceVariant, 13.f));
        left_body->add(std::make_unique<saturn::Text>(
            "Dropdown / Image / Dialog TBD",
            saturn::colors::kOnSurfaceVariant, 13.f));

        auto right_body = std::make_unique<saturn::Column>(8.f);
        right_body->add(std::make_unique<saturn::Text>(
            "ListView TBD", saturn::colors::kOnSurfaceVariant, 13.f));

        auto panels = std::make_unique<saturn::Row>(24.f);
        panels->set_cross_axis_alignment(saturn::CrossAxisAlignment::Start);
        panels->add(make_panel("Controls", std::move(left_body)));
        panels->add(make_panel("Scrollable list", std::move(right_body)));
        page.add(std::move(panels));
      },
      // Drawable/client contract (not Python outer 960x800) — matches golden.
      saturn::kDemoDrawableWidth, saturn::kDemoDrawableHeight);
}
