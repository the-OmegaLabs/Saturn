#include "saturn/app.hpp"
#include "saturn/colors.hpp"
#include "saturn/demo_size.hpp"
#include "saturn/control.hpp"
#include "saturn/page.hpp"
#include "saturn/types.hpp"
#include <memory>
#include <string>

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

// brand_header — logo Image 52x40 CONTAIN + PRIMARY tint.
std::unique_ptr<saturn::Row> brand_header(const char* title, const char* detail) {
  auto header = std::make_unique<saturn::Row>(12.f);
  header->set_cross_axis_alignment(saturn::CrossAxisAlignment::Center);
  saturn::ControlOptions logo_opt;
  logo_opt.width = 52.f;
  logo_opt.height = 40.f;
  auto logo = std::make_unique<saturn::Image>("saturn-logo-transparent.png", logo_opt);
  logo->set_tint(saturn::colors::kPrimary);
  header->add(std::move(logo));
  header->add(std::make_unique<saturn::Text>(
      title, saturn::colors::kOnSurface, 28.f));
  if (detail && detail[0]) {
    header->add(std::make_unique<saturn::Text>(
        detail, saturn::colors::kOnSurfaceVariant, 12.f));
  }
  return header;
}

} // namespace

int main() {
  return saturn::run(
      [](saturn::Page& page) {
        page.set_title("saturn demo");
        page.set_bgcolor(saturn::colors::kSurface);
        page.set_padding(24.f);
        page.set_spacing(16.f);

        page.add(brand_header("Saturn Demo", "v0.1.0"));

        auto status = std::make_unique<saturn::Text>(
            "interact with the controls below",
            saturn::colors::kOnSurfaceVariant, 13.f);
        saturn::Text* status_ptr = status.get();
        page.add(std::move(status));

        auto on_click = [status_ptr]() {
          status_ptr->set_value("last event: click");
        };

        // Inventory: Row spacing=8 — Elevated | Filled | Outlined | IconButton.
        auto btn_row = std::make_unique<saturn::Row>(8.f);
        btn_row->set_cross_axis_alignment(saturn::CrossAxisAlignment::Center);
        btn_row->add(std::make_unique<saturn::ElevatedButton>(
            "Elevated", on_click));  // default leading icons/add.png
        btn_row->add(std::make_unique<saturn::FilledButton>(
            "Filled", on_click));
        btn_row->add(std::make_unique<saturn::OutlinedButton>(
            "Outlined", on_click));
        // Material FAVORITE raster (assets/icons/favorite.png) — not Inter ♥.
        btn_row->add(std::make_unique<saturn::IconButton>(
            "icons/favorite.png", on_click));

        // Inventory: Row spacing=12 — TextField (frozen) + Checkbox("agree").
        auto check_row = std::make_unique<saturn::Row>(12.f);
        check_row->set_cross_axis_alignment(saturn::CrossAxisAlignment::Center);
        check_row->add(std::make_unique<saturn::Checkbox>(
            "agree", false, [status_ptr](bool v) {
              status_ptr->set_value(v ? "last event: checkbox on"
                                     : "last event: checkbox off");
            }));

        // Inventory: Row spacing=12 — Slider + Switch + ProgressRing.
        auto slider_row = std::make_unique<saturn::Row>(12.f);
        slider_row->set_cross_axis_alignment(saturn::CrossAxisAlignment::Center);
        slider_row->add(std::make_unique<saturn::Slider>(
            0.f, 100.f, 10, [status_ptr](float v) {
              status_ptr->set_value("last event: slider " +
                                   std::to_string(static_cast<int>(v + 0.5f)));
            }));
        slider_row->add(std::make_unique<saturn::Switch>(
            false, [status_ptr](bool v) {
              status_ptr->set_value(v ? "last event: switch on"
                                     : "last event: switch off");
            }));
        slider_row->add(std::make_unique<saturn::ProgressRing>(0.6f));

        auto left_body = std::make_unique<saturn::Column>(16.f);
        left_body->add(std::move(btn_row));
        left_body->add(std::move(check_row));
        left_body->add(std::move(slider_row));
        // Deferred: TextField, Dropdown, Dialog/SnackBar.
        left_body->add(std::make_unique<saturn::Text>(
            "TextField/Dropdown TBD", saturn::colors::kOnSurfaceVariant, 13.f));

        // ListView deferred until scroll buffer caps with reviewer.
        auto right_body = std::make_unique<saturn::Column>(4.f);
        right_body->add(std::make_unique<saturn::Text>(
            "ListView TBD", saturn::colors::kOnSurfaceVariant, 13.f));

        auto panels = std::make_unique<saturn::Row>(24.f);
        panels->set_cross_axis_alignment(saturn::CrossAxisAlignment::Start);
        panels->add(make_panel("Controls", std::move(left_body)));
        panels->add(make_panel("Scrollable list", std::move(right_body)));
        page.add(std::move(panels));
      },
      // LOGICAL CLIENT size (SDL CreateWindow) — not Python outer 960x800.
      // At 100% DPI this equals golden pixels 944x761; HiDPI diverges.
      saturn::kDemoClientWidth, saturn::kDemoClientHeight,
      /*demo_contract=*/true);
}
