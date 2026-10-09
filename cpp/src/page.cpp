#include "saturn/page.hpp"
#include "saturn/limits.hpp"
#include <stdexcept>
namespace saturn {
Page::Page() : Control({}) {}
void Page::set_title(std::string title) {
  if (title.size() > kMaxTextBytes) title.resize(kMaxTextBytes);
  title_ = std::move(title);
}
const std::string& Page::title() const { return title_; }
void Page::add(std::unique_ptr<Control> child) {
  if (!child) return;
  if (children_.size() >= kMaxChildren) throw std::runtime_error("too many children");
  child->attach(this, this);
  children_.push_back(std::move(child));
  layout_dirty_ = true;
}
void Page::update() { layout_dirty_ = true; }
}
