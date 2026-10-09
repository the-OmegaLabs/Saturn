#pragma once
#include "types.hpp"
#include <memory>
#include <vector>
namespace saturn {
class Page;
// Phase 3 stub. Parent owns children via unique_ptr.
class Control {
  friend class Page;
public:
  explicit Control(ControlOptions opt = {});
  virtual ~Control() = default;
  Control(const Control&) = delete;
  Control& operator=(const Control&) = delete;
  void set_options(ControlOptions opt);
  const ControlOptions& options() const;
  virtual Size intrinsic(OptionalSize max_w, OptionalSize max_h) const;
protected:
  void attach(Page* page, Control* parent) { page_ = page; parent_ = parent; }
  ControlOptions opt_;
  Page* page_ = nullptr;
  Control* parent_ = nullptr;
  std::vector<std::unique_ptr<Control>> children_; // owned
};
}
