#pragma once
#include <cstddef>
namespace saturn {
inline constexpr std::size_t kMaxTextBytes = 1u << 20;
inline constexpr std::size_t kMaxEventQueue = 4096;
inline constexpr std::size_t kMaxLayoutDim = 1u << 15;
inline constexpr std::size_t kMaxChildren = 1u << 14;
inline constexpr std::size_t kMaxPathBytes = 4096;
}
