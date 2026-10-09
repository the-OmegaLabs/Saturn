#pragma once
#include "types.hpp"
namespace saturn {
namespace colors {
// Material 3 baseline DARK tokens (saturn/colors.py BASELINE_DARK).
// Demo uses ThemeMode.DARK + Colors.SURFACE etc.
inline constexpr Color from_rgb(std::uint8_t r, std::uint8_t g, std::uint8_t b,
                                std::uint8_t a = 255) {
  return Color{r, g, b, a};
}
inline constexpr Color from_hex6(std::uint32_t rgb, std::uint8_t a = 255) {
  return Color{
    static_cast<std::uint8_t>((rgb >> 16) & 0xff),
    static_cast<std::uint8_t>((rgb >> 8) & 0xff),
    static_cast<std::uint8_t>(rgb & 0xff),
    a};
}

inline constexpr Color kPrimary = from_hex6(0xD0BCFF);
inline constexpr Color kOnPrimary = from_hex6(0x381E72);
inline constexpr Color kPrimaryContainer = from_hex6(0x4F378B);
inline constexpr Color kOnPrimaryContainer = from_hex6(0xEADDFF);
inline constexpr Color kSurface = from_hex6(0x141218);
inline constexpr Color kOnSurface = from_hex6(0xE6E0E9);
inline constexpr Color kOnSurfaceVariant = from_hex6(0xCAC4D0);
inline constexpr Color kSurfaceContainerLowest = from_hex6(0x0F0D13);
inline constexpr Color kSurfaceContainerLow = from_hex6(0x1D1B20);
inline constexpr Color kSurfaceContainer = from_hex6(0x211F26);
inline constexpr Color kSurfaceContainerHigh = from_hex6(0x2B2930);
inline constexpr Color kSurfaceContainerHighest = from_hex6(0x36343B);
inline constexpr Color kOutline = from_hex6(0x938F99);
inline constexpr Color kOutlineVariant = from_hex6(0x49454F);
inline constexpr Color kError = from_hex6(0xF2B8B5);
inline constexpr Color kSecondaryContainer = from_hex6(0x4A4458);
inline constexpr Color kOnSecondaryContainer = from_hex6(0xE8DEF8);
} // namespace colors
} // namespace saturn
