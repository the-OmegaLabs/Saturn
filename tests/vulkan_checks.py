"""Vulkan backend self-check, including a real hidden swapchain when available."""
import sys
from unittest.mock import patch

sys.path.insert(0, ".")

import pygame
import vulkan as vk

from saturn.app import Render
from saturn.renderer.software import SoftwareRenderer
from saturn.renderer.vulkan import (
    VulkanRenderer, VulkanUnavailableError, _VulkanSwapchain)


def check_render_enum():
    assert Render.VULKAN.value == "vulkan"


def check_surface_format_selection():
    renderer = object.__new__(VulkanRenderer)
    formats = [
        vk.VkSurfaceFormatKHR(
            format=vk.VK_FORMAT_R8G8B8A8_SRGB,
            colorSpace=vk.VK_COLOR_SPACE_SRGB_NONLINEAR_KHR),
        vk.VkSurfaceFormatKHR(
            format=vk.VK_FORMAT_B8G8R8A8_UNORM,
            colorSpace=vk.VK_COLOR_SPACE_SRGB_NONLINEAR_KHR),
    ]
    selected = renderer._choose_surface_format(formats)
    assert selected.format == vk.VK_FORMAT_B8G8R8A8_UNORM


def check_hidden_swapchain():
    pygame.init()
    window = None
    renderer = None
    try:
        window = pygame.Window(
            "Saturn Vulkan self-check", size=(96, 64),
            vulkan=True, hidden=True, resizable=True)
        renderer = VulkanRenderer(window)
        image = pygame.Surface((8, 8), pygame.SRCALPHA)
        image.fill((255, 255, 255, 255))
        red = pygame.Surface((8, 8), pygame.SRCALPHA)
        red.fill((255, 0, 0, 255))
        green = pygame.Surface((8, 8), pygame.SRCALPHA)
        green.fill((0, 255, 0, 255))
        # The Vulkan backend must render geometry and textured quads itself.
        # Any inherited CPU full-frame path makes this check fail.
        with (patch.object(SoftwareRenderer, "clear",
                           side_effect=AssertionError("CPU clear")),
              patch.object(SoftwareRenderer, "fill_rect",
                           side_effect=AssertionError("CPU rectangle")),
              patch.object(SoftwareRenderer, "blit_scaled",
                           side_effect=AssertionError("CPU texture")),
              patch.object(_VulkanSwapchain, "flip",
                           side_effect=AssertionError("CPU frame upload"))):
            renderer.clear((15, 25, 35, 255))
            renderer.fill_rect(8, 8, 48, 28, (220, 90, 40, 255), radius=6)
            renderer.blit_scaled(image, 55, 10, 12, 12)
            renderer.blit_cached_scaled(red, 71, 10, 8, 8)
            renderer.blit_cached_scaled(green, 81, 10, 8, 8)
            renderer.flip()
        frame = renderer.screenshot()
        assert frame.get_size() == (96, 64)
        for point, expected in (((2, 2), (15, 25, 35)),
                                ((20, 20), (220, 90, 40)),
                                ((60, 15), (255, 255, 255)),
                                ((74, 13), (255, 0, 0)),
                                ((84, 13), (0, 255, 0))):
            actual = frame.get_at(point)
            assert all(abs(actual[i] - expected[i]) <= 3 for i in range(3)), \
                (point, actual, expected)
        # Flat triangle edges (diagonal lines and arcs) need multisampling;
        # SDF antialiasing alone only covers rounded rectangles and circles.
        if renderer._gpu_samples != vk.VK_SAMPLE_COUNT_1_BIT:
            renderer.clear((255, 255, 255, 255))
            renderer.line(8.2, 11.4, 87.6, 52.8,
                          (195, 38, 82, 255), width=1.25)
            edge_frame = renderer.screenshot()
            blended_edges = sum(
                1 for y in range(64) for x in range(96)
                if (195 < edge_frame.get_at((x, y)).r < 255 and
                    38 < edge_frame.get_at((x, y)).g < 255))
            assert blended_edges >= 20, blended_edges
            renderer.clear((255, 255, 255, 255))
            renderer.arc(48, 32, 23, 0.2, 5.5,
                         (195, 38, 82, 255), width=1.5)
            arc_frame = renderer.screenshot()
            blended_arc_edges = sum(
                1 for y in range(64) for x in range(96)
                if (195 < arc_frame.get_at((x, y)).r < 255 and
                    38 < arc_frame.get_at((x, y)).g < 255))
            assert blended_arc_edges >= 20, blended_arc_edges
        assert renderer._swapchain_images
    except (pygame.error, VulkanUnavailableError) as error:
        print(f"VULKAN DEVICE CHECK SKIPPED: {error}")
    finally:
        if renderer is not None:
            renderer.close()
        if window is not None:
            window.destroy()
        pygame.quit()


if __name__ == "__main__":
    check_render_enum()
    check_surface_format_selection()
    check_hidden_swapchain()
    print("ALL VULKAN TESTS PASS")
