#include "saturn/app.hpp"
#include "saturn/colors.hpp"
#include "saturn/demo_size.hpp"
#include "saturn/control.hpp"
#include "saturn/page.hpp"
#include "saturn/types.hpp"
#include <memory>
#include <string>
#include <vector>

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

// Brand mark stays vector-sharp at any DPI, contained in a 52x40 logical box.
std::unique_ptr<saturn::Row> brand_header(const char* title, const char* detail) {
  auto header = std::make_unique<saturn::Row>(12.f);
  header->set_cross_axis_alignment(saturn::CrossAxisAlignment::Center);
  saturn::ControlOptions logo_opt;
  logo_opt.width = 52.f;
  logo_opt.height = 40.f;
  auto logo = std::make_unique<saturn::SaturnLogo>(saturn::colors::kPrimary,logo_opt);
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

        auto on_click = [status_ptr, n = std::make_shared<int>(0)]() {
          // Shared counter belongs to all four callback copies.
          status_ptr->set_value("last event: click #" + std::to_string(++*n));
        };

        // Inventory: Row spacing=8 — Elevated | Filled | Outlined | IconButton.
        auto btn_row = std::make_unique<saturn::Row>(8.f);
        btn_row->set_cross_axis_alignment(saturn::CrossAxisAlignment::Center);
        // Elevated default icon path is empty; pass ADD explicitly for demo.
        btn_row->add(std::make_unique<saturn::ElevatedButton>(
            "Elevated", on_click, "icons/add.png"));
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
        check_row->add(std::make_unique<saturn::TextField>(
            "Name", [status_ptr](const std::string& value) {
              status_ptr->set_value("name='" + value + "'");
            }, [status_ptr](const std::string& value) {
              status_ptr->set_value("submitted '" + value + "'");
            }));
        check_row->add(std::make_unique<saturn::Checkbox>(
            "agree", false, [status_ptr](bool v) {
              status_ptr->set_value(v ? "agree=true" : "agree=false");
            }));

        // Inventory: Row spacing=12 — Slider + Switch + ProgressRing.
        auto slider_row = std::make_unique<saturn::Row>(12.f);
        slider_row->set_cross_axis_alignment(saturn::CrossAxisAlignment::Center);
        slider_row->add(std::make_unique<saturn::Slider>(
            0.f, 100.f, 10, [status_ptr](float v) {
              status_ptr->set_value("slider=" +
                                   std::to_string(static_cast<int>(v + 0.5f)));
            }));
        slider_row->add(std::make_unique<saturn::Switch>(
            false, [status_ptr](bool v) {
              status_ptr->set_value(v ? "switch=true" : "switch=false");
            }));
        slider_row->add(std::make_unique<saturn::ProgressRing>(0.6f));

        // Inventory: Row spacing=12 — Dropdown + Image (140×70).
        auto drop_row = std::make_unique<saturn::Row>(12.f);
        drop_row->set_cross_axis_alignment(saturn::CrossAxisAlignment::Center);
        saturn::ControlOptions drop_opt;
        drop_opt.width = 180.f;
        std::vector<saturn::DropdownOption> opts = {
            {"a", "Alpha"}, {"b", "Beta"}, {"g", "Gamma"},
        };
        drop_row->add(std::make_unique<saturn::Dropdown>(
            "dropdown...", std::move(opts),
            [status_ptr](const std::string& key) {
              status_ptr->set_value("select=" + key);
            },
            drop_opt));
        saturn::ControlOptions img_opt;
        img_opt.width = 140.f;
        img_opt.height = 70.f;
        // Inventory: Python Image border_radius=8
        drop_row->add(std::make_unique<saturn::Image>("test_img.png", img_opt, 8.f));

        // Inventory: Row spacing=8 — Dialog + SnackBar (Elevated = Python Button).
        auto dlg_row = std::make_unique<saturn::Row>(8.f);
        dlg_row->set_cross_axis_alignment(saturn::CrossAxisAlignment::Center);
        saturn::Page* page_ptr = &page;
        dlg_row->add(std::make_unique<saturn::ElevatedButton>(
            "Dialog", [page_ptr]() {
              std::vector<std::unique_ptr<saturn::Control>> actions;
              actions.push_back(std::make_unique<saturn::TextButton>(
                  "Cancel", [page_ptr]() { page_ptr->pop_dialog(); }));
              actions.push_back(std::make_unique<saturn::FilledButton>(
                  "Delete", [page_ptr]() { page_ptr->pop_dialog(); }));
              page_ptr->show_dialog(std::make_unique<saturn::AlertDialog>(
                  "Confirm", "Delete this item permanently?",
                  std::move(actions)));
            }));
        dlg_row->add(std::make_unique<saturn::ElevatedButton>(
            "SnackBar", [page_ptr]() {
              page_ptr->show_dialog(std::make_unique<saturn::SnackBar>(
                  "Saved!", "Undo",
                  std::function<void()>{},
                  3000));
            }));

        auto left_body = std::make_unique<saturn::Column>(16.f);
        left_body->add(std::move(btn_row));
        left_body->add(std::move(check_row));
        left_body->add(std::move(slider_row));
        left_body->add(std::move(drop_row));
        left_body->add(std::move(dlg_row));
        auto right_body = std::make_unique<saturn::Column>(4.f);
        saturn::ControlOptions list_opt;
        list_opt.width = 400.f;
        list_opt.height = 260.f;
        auto list = std::make_unique<saturn::ListView>(4.f, list_opt);
        for (int i = 0; i < 30; ++i) {
          auto item = std::make_unique<saturn::Container>();
          item->set_padding(8);
          item->set_corner_radius(6);
          item->set_bgcolor(i % 2 ? saturn::colors::kSurfaceContainerLow :
                                   saturn::colors::kSurfaceContainer);
          item->add(std::make_unique<saturn::Text>(
              "list item " + std::to_string(i), saturn::colors::kOnSurface, 13.f));
          list->add(std::move(item));
        }
        right_body->add(std::move(list));

        auto panels = std::make_unique<saturn::Row>(24.f);
        panels->set_cross_axis_alignment(saturn::CrossAxisAlignment::Center);
        panels->add(make_panel("Controls", std::move(left_body)));
        panels->add(make_panel("Scrollable list", std::move(right_body)));
        page.add(std::move(panels));
      },
      // LOGICAL CLIENT size (SDL CreateWindow) — not Python outer 960x800.
      // At 100% DPI this equals golden pixels 944x761; HiDPI diverges.
      saturn::kDemoClientWidth, saturn::kDemoClientHeight,
      /*demo_contract=*/true);
}
