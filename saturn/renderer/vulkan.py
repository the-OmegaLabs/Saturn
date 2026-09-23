"""Vulkan GPU rendering backend.

Widgets produce batched vertices and sampled textures. Vulkan rasterizes them
directly into the swapchain; the original CPU presenter remains below only
for shared instance/device setup and legacy compatibility helpers.
"""
from __future__ import annotations

import ctypes
import ctypes.util
from array import array
from collections import OrderedDict
import hashlib
import math
import os
from pathlib import Path
import struct

import pygame
import vulkan as vk

from ..colors import parse_color
from .base import Renderer
from .software import SCALE, SoftwareRenderer


class VulkanUnavailableError(RuntimeError):
    """Raised when the host cannot create a usable Vulkan swapchain."""


def _sdl_library() -> ctypes.CDLL:
    """Load the same SDL library pygame uses."""
    package = Path(pygame.__file__).resolve().parent
    candidates = [package / "SDL2.dll"]
    for root in (package, package.parent / "pygame_ce.libs",
                 package.parent / "pygame.libs"):
        if root.is_dir():
            candidates.extend(root.glob("*SDL2*.so*"))
            candidates.extend(root.glob("*SDL2*.dylib"))
    found = ctypes.util.find_library("SDL2")
    if found:
        candidates.append(found)
    for candidate in candidates:
        try:
            return ctypes.CDLL(str(candidate))
        except OSError:
            pass
    raise VulkanUnavailableError("could not load pygame's SDL2 library")


def _handle_value(handle) -> int:
    return int(vk.ffi.cast("uintptr_t", handle))


class _VulkanSwapchain(SoftwareRenderer):
    """Original CPU presentation implementation and Vulkan bootstrap helpers."""

    scale = float(SCALE)

    def __init__(self, window, *, logical_size=None, pixel_ratio: float = 1.0):
        # Vulkan SDL windows have no pygame display Surface, so initialize the
        # inherited off-screen rasterizer explicitly.
        Renderer._init_effect_stacks(self)
        self.window = window
        self.pixel_ratio = max(1.0, float(pixel_ratio))
        self._aa_scale = 1 if self.pixel_ratio >= 1.5 else SCALE
        self.scale = self._aa_scale * self.pixel_ratio
        size = tuple(max(1, int(value)) for value in window.size)
        self.screen = pygame.Surface(size, pygame.SRCALPHA, 32)
        self._buf = pygame.Surface(
            (size[0] * self._aa_scale, size[1] * self._aa_scale),
            pygame.SRCALPHA, 32)
        self._clip: list[tuple] = []
        self._apply_clip()

        self._closed = False
        self._sdl = None
        self._sdl_window = None
        self._instance = None
        self._surface = None
        self._physical_device = None
        self._device = None
        self._graphics_queue = None
        self._present_queue = None
        self._command_pool = None
        self._command_buffer = None
        self._image_available = None
        self._render_finished = None
        self._in_flight = None
        self._swapchain = None
        self._swapchain_images = []
        self._image_initialized: list[bool] = []
        self._staging_buffer = None
        self._staging_memory = None
        self._staging_mapped = None
        self._staging_size = 0
        self._extent = size
        self._surface_format = None

        try:
            self._create_instance_and_surface()
            self._select_physical_device()
            self._create_device()
            self._load_extension_functions()
            self._create_commands_and_sync()
            self._create_swapchain()
        except Exception:
            self.close()
            raise

    # -- SDL / Vulkan bootstrap -----------------------------------------
    def _create_instance_and_surface(self):
        self._sdl = _sdl_library()
        self._sdl.SDL_GetWindowFromID.argtypes = [ctypes.c_uint32]
        self._sdl.SDL_GetWindowFromID.restype = ctypes.c_void_p
        self._sdl_window = self._sdl.SDL_GetWindowFromID(self.window.id)
        if not self._sdl_window:
            raise VulkanUnavailableError("SDL could not resolve the Vulkan window")

        self._sdl.SDL_Vulkan_GetInstanceExtensions.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_char_p),
        ]
        self._sdl.SDL_Vulkan_GetInstanceExtensions.restype = ctypes.c_int
        count = ctypes.c_uint32()
        if not self._sdl.SDL_Vulkan_GetInstanceExtensions(
                self._sdl_window, ctypes.byref(count), None):
            raise VulkanUnavailableError("SDL could not query Vulkan extensions")
        names = (ctypes.c_char_p * count.value)()
        if not self._sdl.SDL_Vulkan_GetInstanceExtensions(
                self._sdl_window, ctypes.byref(count), names):
            raise VulkanUnavailableError("SDL could not enumerate Vulkan extensions")
        extensions = [name.decode("ascii") for name in names]
        available = {
            (item.extensionName.decode("ascii")
             if isinstance(item.extensionName, bytes)
             else str(item.extensionName))
            for item in vk.vkEnumerateInstanceExtensionProperties(None)
        }
        instance_flags = 0
        portability = vk.VK_KHR_PORTABILITY_ENUMERATION_EXTENSION_NAME
        if portability in available and portability not in extensions:
            extensions.append(portability)
            instance_flags |= vk.VK_INSTANCE_CREATE_ENUMERATE_PORTABILITY_BIT_KHR

        application = vk.VkApplicationInfo(
            pApplicationName="Saturn",
            applicationVersion=vk.VK_MAKE_VERSION(0, 1, 0),
            pEngineName="Saturn",
            engineVersion=vk.VK_MAKE_VERSION(0, 1, 0),
            apiVersion=vk.VK_API_VERSION_1_0,
        )
        create_info = vk.VkInstanceCreateInfo(
            flags=instance_flags,
            pApplicationInfo=application,
            enabledExtensionCount=len(extensions),
            ppEnabledExtensionNames=extensions,
        )
        try:
            self._instance = vk.vkCreateInstance(create_info, None)
        except Exception as error:
            raise VulkanUnavailableError(
                f"could not create a Vulkan instance: {error}") from error

        self._sdl.SDL_Vulkan_CreateSurface.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        self._sdl.SDL_Vulkan_CreateSurface.restype = ctypes.c_int
        surface = ctypes.c_void_p()
        if not self._sdl.SDL_Vulkan_CreateSurface(
                self._sdl_window, ctypes.c_void_p(_handle_value(self._instance)),
                ctypes.byref(surface)):
            raise VulkanUnavailableError("SDL could not create the Vulkan surface")
        self._surface = vk.ffi.cast("VkSurfaceKHR", surface.value)

        self._destroy_surface = vk.vkGetInstanceProcAddr(
            self._instance, "vkDestroySurfaceKHR")
        self._get_surface_support = vk.vkGetInstanceProcAddr(
            self._instance, "vkGetPhysicalDeviceSurfaceSupportKHR")
        self._get_surface_capabilities = vk.vkGetInstanceProcAddr(
            self._instance, "vkGetPhysicalDeviceSurfaceCapabilitiesKHR")
        self._get_surface_formats = vk.vkGetInstanceProcAddr(
            self._instance, "vkGetPhysicalDeviceSurfaceFormatsKHR")
        self._get_present_modes = vk.vkGetInstanceProcAddr(
            self._instance, "vkGetPhysicalDeviceSurfacePresentModesKHR")

    def _select_physical_device(self):
        candidates = []
        for device in vk.vkEnumeratePhysicalDevices(self._instance):
            extensions = {
                (item.extensionName.decode("ascii")
                 if isinstance(item.extensionName, bytes)
                 else str(item.extensionName))
                for item in vk.vkEnumerateDeviceExtensionProperties(device, None)
            }
            if vk.VK_KHR_SWAPCHAIN_EXTENSION_NAME not in extensions:
                continue
            graphics = None
            present = None
            for index, family in enumerate(
                    vk.vkGetPhysicalDeviceQueueFamilyProperties(device)):
                if family.queueCount and family.queueFlags & vk.VK_QUEUE_GRAPHICS_BIT:
                    graphics = index if graphics is None else graphics
                if family.queueCount and self._get_surface_support(
                        device, index, self._surface):
                    present = index if present is None else present
                if graphics == index and present == index:
                    break
            if graphics is None or present is None:
                continue
            if not len(self._get_surface_formats(device, self._surface)):
                continue
            if not len(self._get_present_modes(device, self._surface)):
                continue
            properties = vk.vkGetPhysicalDeviceProperties(device)
            rank = {
                vk.VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU: 0,
                vk.VK_PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU: 1,
            }.get(properties.deviceType, 2)
            candidates.append((rank, device, graphics, present, extensions))

        if not candidates:
            raise VulkanUnavailableError(
                "no Vulkan device supports graphics, presentation and VK_KHR_swapchain")
        (_, self._physical_device, self._graphics_family, self._present_family,
         self._device_extensions) = \
            min(candidates, key=lambda item: item[0])

    def _create_device(self):
        families = sorted({self._graphics_family, self._present_family})
        queue_infos = [
            vk.VkDeviceQueueCreateInfo(
                queueFamilyIndex=family,
                queueCount=1,
                pQueuePriorities=[1.0],
            )
            for family in families
        ]
        enabled_extensions = [vk.VK_KHR_SWAPCHAIN_EXTENSION_NAME]
        portability = vk.VK_KHR_PORTABILITY_SUBSET_EXTENSION_NAME
        if portability in self._device_extensions:
            enabled_extensions.append(portability)
        create_info = vk.VkDeviceCreateInfo(
            queueCreateInfoCount=len(queue_infos),
            pQueueCreateInfos=queue_infos,
            enabledExtensionCount=len(enabled_extensions),
            ppEnabledExtensionNames=enabled_extensions,
        )
        self._device = vk.vkCreateDevice(self._physical_device, create_info, None)
        self._graphics_queue = vk.vkGetDeviceQueue(
            self._device, self._graphics_family, 0)
        self._present_queue = vk.vkGetDeviceQueue(
            self._device, self._present_family, 0)

    def _load_extension_functions(self):
        self._create_swapchain_fn = vk.vkGetDeviceProcAddr(
            self._device, "vkCreateSwapchainKHR")
        self._destroy_swapchain_fn = vk.vkGetDeviceProcAddr(
            self._device, "vkDestroySwapchainKHR")
        self._get_swapchain_images = vk.vkGetDeviceProcAddr(
            self._device, "vkGetSwapchainImagesKHR")
        self._acquire_next_image = vk.vkGetDeviceProcAddr(
            self._device, "vkAcquireNextImageKHR")
        self._queue_present = vk.vkGetDeviceProcAddr(
            self._device, "vkQueuePresentKHR")

    def _create_commands_and_sync(self):
        pool_info = vk.VkCommandPoolCreateInfo(
            flags=vk.VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT,
            queueFamilyIndex=self._graphics_family,
        )
        self._command_pool = vk.vkCreateCommandPool(self._device, pool_info, None)
        allocate_info = vk.VkCommandBufferAllocateInfo(
            commandPool=self._command_pool,
            level=vk.VK_COMMAND_BUFFER_LEVEL_PRIMARY,
            commandBufferCount=1,
        )
        self._command_buffer = vk.vkAllocateCommandBuffers(
            self._device, allocate_info)[0]
        semaphore_info = vk.VkSemaphoreCreateInfo()
        self._image_available = vk.vkCreateSemaphore(
            self._device, semaphore_info, None)
        self._render_finished = vk.vkCreateSemaphore(
            self._device, semaphore_info, None)
        self._in_flight = vk.vkCreateFence(
            self._device,
            vk.VkFenceCreateInfo(flags=vk.VK_FENCE_CREATE_SIGNALED_BIT), None)

    # -- swapchain -------------------------------------------------------
    def _choose_surface_format(self, formats):
        preferred = (
            vk.VK_FORMAT_B8G8R8A8_UNORM,
            vk.VK_FORMAT_B8G8R8A8_SRGB,
            vk.VK_FORMAT_R8G8B8A8_UNORM,
            vk.VK_FORMAT_R8G8B8A8_SRGB,
        )
        if len(formats) == 1 and formats[0].format == vk.VK_FORMAT_UNDEFINED:
            return vk.VkSurfaceFormatKHR(
                format=vk.VK_FORMAT_B8G8R8A8_UNORM,
                colorSpace=formats[0].colorSpace)
        for wanted in preferred:
            for item in formats:
                if item.format == wanted:
                    return vk.VkSurfaceFormatKHR(
                        format=item.format, colorSpace=item.colorSpace)
        raise VulkanUnavailableError(
            "surface exposes no supported 32-bit BGRA/RGBA format")

    @staticmethod
    def _choose_composite_alpha(capabilities):
        for mode in (
            vk.VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR,
            vk.VK_COMPOSITE_ALPHA_PRE_MULTIPLIED_BIT_KHR,
            vk.VK_COMPOSITE_ALPHA_POST_MULTIPLIED_BIT_KHR,
            vk.VK_COMPOSITE_ALPHA_INHERIT_BIT_KHR,
        ):
            if capabilities.supportedCompositeAlpha & mode:
                return mode
        raise VulkanUnavailableError("surface exposes no composite-alpha mode")

    def _choose_extent(self, capabilities):
        if capabilities.currentExtent.width != 0xFFFFFFFF:
            return capabilities.currentExtent
        width, height = self.screen.get_size()
        return vk.VkExtent2D(
            width=max(capabilities.minImageExtent.width,
                      min(width, capabilities.maxImageExtent.width)),
            height=max(capabilities.minImageExtent.height,
                       min(height, capabilities.maxImageExtent.height)),
        )

    def _create_swapchain(self):
        capabilities = self._get_surface_capabilities(
            self._physical_device, self._surface)
        if not capabilities.supportedUsageFlags & vk.VK_IMAGE_USAGE_TRANSFER_DST_BIT:
            raise VulkanUnavailableError(
                "the Vulkan surface does not support transfer-destination images")
        formats = self._get_surface_formats(self._physical_device, self._surface)
        self._surface_format = self._choose_surface_format(formats)
        extent = self._choose_extent(capabilities)
        self._extent = (int(extent.width), int(extent.height))

        image_count = capabilities.minImageCount + 1
        if capabilities.maxImageCount:
            image_count = min(image_count, capabilities.maxImageCount)
        families = [self._graphics_family, self._present_family]
        separate = self._graphics_family != self._present_family
        create_info = vk.VkSwapchainCreateInfoKHR(
            surface=self._surface,
            minImageCount=image_count,
            imageFormat=self._surface_format.format,
            imageColorSpace=self._surface_format.colorSpace,
            imageExtent=extent,
            imageArrayLayers=1,
            imageUsage=vk.VK_IMAGE_USAGE_TRANSFER_DST_BIT,
            imageSharingMode=(vk.VK_SHARING_MODE_CONCURRENT if separate
                              else vk.VK_SHARING_MODE_EXCLUSIVE),
            queueFamilyIndexCount=2 if separate else 0,
            pQueueFamilyIndices=families if separate else None,
            preTransform=capabilities.currentTransform,
            compositeAlpha=self._choose_composite_alpha(capabilities),
            presentMode=vk.VK_PRESENT_MODE_FIFO_KHR,
            clipped=vk.VK_TRUE,
            oldSwapchain=None,
        )
        self._swapchain = self._create_swapchain_fn(
            self._device, create_info, None)
        self._swapchain_images = list(self._get_swapchain_images(
            self._device, self._swapchain))
        self._image_initialized = [False] * len(self._swapchain_images)
        self._create_staging_buffer(self._extent[0] * self._extent[1] * 4)

    def _destroy_swapchain_resources(self):
        if self._device is None:
            return
        if self._staging_mapped is not None:
            vk.vkUnmapMemory(self._device, self._staging_memory)
            self._staging_mapped = None
        if self._staging_buffer is not None:
            vk.vkDestroyBuffer(self._device, self._staging_buffer, None)
            self._staging_buffer = None
        if self._staging_memory is not None:
            vk.vkFreeMemory(self._device, self._staging_memory, None)
            self._staging_memory = None
        self._staging_size = 0
        self._swapchain_images = []
        self._image_initialized = []
        if self._swapchain is not None:
            self._destroy_swapchain_fn(self._device, self._swapchain, None)
            self._swapchain = None

    def _recreate_swapchain(self):
        if self._closed or self._device is None:
            return
        vk.vkDeviceWaitIdle(self._device)
        self._destroy_swapchain_resources()
        self._create_swapchain()

    def _memory_type(self, bits, required_flags):
        properties = vk.vkGetPhysicalDeviceMemoryProperties(self._physical_device)
        for index in range(properties.memoryTypeCount):
            flags = properties.memoryTypes[index].propertyFlags
            if bits & (1 << index) and flags & required_flags == required_flags:
                return index
        raise VulkanUnavailableError("no compatible host-visible Vulkan memory type")

    def _create_staging_buffer(self, size):
        self._staging_size = max(4, int(size))
        info = vk.VkBufferCreateInfo(
            size=self._staging_size,
            usage=vk.VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
            sharingMode=vk.VK_SHARING_MODE_EXCLUSIVE,
        )
        self._staging_buffer = vk.vkCreateBuffer(self._device, info, None)
        requirements = vk.vkGetBufferMemoryRequirements(
            self._device, self._staging_buffer)
        flags = (vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
                 vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)
        allocation = vk.VkMemoryAllocateInfo(
            allocationSize=requirements.size,
            memoryTypeIndex=self._memory_type(requirements.memoryTypeBits, flags),
        )
        self._staging_memory = vk.vkAllocateMemory(
            self._device, allocation, None)
        vk.vkBindBufferMemory(
            self._device, self._staging_buffer, self._staging_memory, 0)
        # Host-coherent staging memory can stay mapped until swapchain teardown.
        # Avoid a map/unmap driver round trip on every presented frame.
        self._staging_mapped = vk.vkMapMemory(
            self._device, self._staging_memory, 0, self._staging_size, 0)

    # -- upload and present ---------------------------------------------
    def _frame_bytes(self) -> bytes:
        frame = self.screenshot()
        if frame.get_size() != self._extent:
            frame = pygame.transform.smoothscale(frame, self._extent)
        if self._surface_format.format in (
                vk.VK_FORMAT_B8G8R8A8_UNORM, vk.VK_FORMAT_B8G8R8A8_SRGB):
            return pygame.image.tobytes(frame, "BGRA")
        if self._surface_format.format in (
                vk.VK_FORMAT_R8G8B8A8_UNORM, vk.VK_FORMAT_R8G8B8A8_SRGB):
            return pygame.image.tobytes(frame, "RGBA")
        raise VulkanUnavailableError(
            f"unsupported Vulkan surface format {self._surface_format.format}")

    def _record_copy(self, image_index):
        command = self._command_buffer
        vk.vkBeginCommandBuffer(
            command,
            vk.VkCommandBufferBeginInfo(
                flags=vk.VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT))
        old_layout = (vk.VK_IMAGE_LAYOUT_PRESENT_SRC_KHR
                      if self._image_initialized[image_index]
                      else vk.VK_IMAGE_LAYOUT_UNDEFINED)
        subresource = vk.VkImageSubresourceRange(
            aspectMask=vk.VK_IMAGE_ASPECT_COLOR_BIT,
            baseMipLevel=0, levelCount=1,
            baseArrayLayer=0, layerCount=1,
        )
        to_transfer = vk.VkImageMemoryBarrier(
            srcAccessMask=0,
            dstAccessMask=vk.VK_ACCESS_TRANSFER_WRITE_BIT,
            oldLayout=old_layout,
            newLayout=vk.VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
            srcQueueFamilyIndex=vk.VK_QUEUE_FAMILY_IGNORED,
            dstQueueFamilyIndex=vk.VK_QUEUE_FAMILY_IGNORED,
            image=self._swapchain_images[image_index],
            subresourceRange=subresource,
        )
        vk.vkCmdPipelineBarrier(
            command,
            vk.VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
            vk.VK_PIPELINE_STAGE_TRANSFER_BIT,
            0, 0, None, 0, None, 1, [to_transfer],
        )
        copy = vk.VkBufferImageCopy(
            bufferOffset=0,
            bufferRowLength=0,
            bufferImageHeight=0,
            imageSubresource=vk.VkImageSubresourceLayers(
                aspectMask=vk.VK_IMAGE_ASPECT_COLOR_BIT,
                mipLevel=0, baseArrayLayer=0, layerCount=1),
            imageOffset=vk.VkOffset3D(x=0, y=0, z=0),
            imageExtent=vk.VkExtent3D(
                width=self._extent[0], height=self._extent[1], depth=1),
        )
        vk.vkCmdCopyBufferToImage(
            command, self._staging_buffer,
            self._swapchain_images[image_index],
            vk.VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, [copy])
        to_present = vk.VkImageMemoryBarrier(
            srcAccessMask=vk.VK_ACCESS_TRANSFER_WRITE_BIT,
            dstAccessMask=0,
            oldLayout=vk.VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
            newLayout=vk.VK_IMAGE_LAYOUT_PRESENT_SRC_KHR,
            srcQueueFamilyIndex=vk.VK_QUEUE_FAMILY_IGNORED,
            dstQueueFamilyIndex=vk.VK_QUEUE_FAMILY_IGNORED,
            image=self._swapchain_images[image_index],
            subresourceRange=subresource,
        )
        vk.vkCmdPipelineBarrier(
            command,
            vk.VK_PIPELINE_STAGE_TRANSFER_BIT,
            vk.VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,
            0, 0, None, 0, None, 1, [to_present],
        )
        vk.vkEndCommandBuffer(command)
        self._image_initialized[image_index] = True

    def flip(self):
        if self._closed:
            return
        vk.vkWaitForFences(
            self._device, 1, [self._in_flight], vk.VK_TRUE, vk.UINT64_MAX)
        try:
            image_index = self._acquire_next_image(
                self._device, self._swapchain, vk.UINT64_MAX,
                self._image_available, None)
        except vk.VkErrorOutOfDateKhr:
            self._recreate_swapchain()
            return
        except vk.VkSuboptimalKhr:
            # The extension wrapper discards the valid image index returned
            # with VK_SUBOPTIMAL_KHR. Consume its signaled acquire semaphore
            # before rebuilding so it is never reused while signaled.
            consume = vk.VkSubmitInfo(
                pWaitSemaphores=[self._image_available],
                pWaitDstStageMask=[vk.VK_PIPELINE_STAGE_TRANSFER_BIT],
            )
            vk.vkQueueSubmit(self._graphics_queue, 1, [consume], None)
            self._recreate_swapchain()
            return

        data = self._frame_bytes()
        if len(data) > self._staging_size:
            self._recreate_swapchain()
            data = self._frame_bytes()
        self._staging_mapped[:len(data)] = data

        vk.vkResetFences(self._device, 1, [self._in_flight])
        vk.vkResetCommandBuffer(self._command_buffer, 0)
        self._record_copy(image_index)
        submit = vk.VkSubmitInfo(
            pWaitSemaphores=[self._image_available],
            pWaitDstStageMask=[vk.VK_PIPELINE_STAGE_TRANSFER_BIT],
            pCommandBuffers=[self._command_buffer],
            pSignalSemaphores=[self._render_finished],
        )
        vk.vkQueueSubmit(
            self._graphics_queue, 1, [submit], self._in_flight)
        present = vk.VkPresentInfoKHR(
            pWaitSemaphores=[self._render_finished],
            pSwapchains=[self._swapchain],
            pImageIndices=[image_index],
        )
        try:
            self._queue_present(self._present_queue, present)
        except (vk.VkErrorOutOfDateKhr, vk.VkSuboptimalKhr):
            self._recreate_swapchain()
        if os.environ.get("SATURN_SHOT"):
            pygame.image.save(self.screenshot(), os.environ["SATURN_SHOT"])

    def on_resize(self, width, height, *, pixel_size=None,
                  pixel_ratio: float | None = None):
        width, height = max(1, int(width)), max(1, int(height))
        ratio = (max(1.0, float(pixel_ratio)) if pixel_ratio is not None
                 else self.pixel_ratio)
        aa_scale = 1 if ratio >= 1.5 else SCALE
        target = tuple(pixel_size) if pixel_size is not None else (width, height)
        target = tuple(max(1, int(value)) for value in target)
        size_changed = self.screen.get_size() != target
        if not size_changed and ratio == self.pixel_ratio:
            return
        self.pixel_ratio = ratio
        self._aa_scale = aa_scale
        self.scale = aa_scale * ratio
        if size_changed:
            self.screen = pygame.Surface(target, pygame.SRCALPHA, 32)
        buffer_size = (target[0] * aa_scale, target[1] * aa_scale)
        if self._buf.get_size() != buffer_size:
            self._buf = pygame.Surface(buffer_size, pygame.SRCALPHA, 32)
        self._apply_clip()
        if size_changed and self._swapchain is not None:
            self._recreate_swapchain()

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._device is not None:
            try:
                vk.vkDeviceWaitIdle(self._device)
            except Exception:
                pass
            self._destroy_swapchain_resources()
            for handle, destroy in (
                (self._in_flight, vk.vkDestroyFence),
                (self._render_finished, vk.vkDestroySemaphore),
                (self._image_available, vk.vkDestroySemaphore),
                (self._command_pool, vk.vkDestroyCommandPool),
            ):
                if handle is not None:
                    destroy(self._device, handle, None)
            vk.vkDestroyDevice(self._device, None)
            self._device = None
        if self._surface is not None and self._instance is not None:
            self._destroy_surface(self._instance, self._surface, None)
            self._surface = None
        if self._instance is not None:
            vk.vkDestroyInstance(self._instance, None)
            self._instance = None


class VulkanRenderer(_VulkanSwapchain):
    """Vulkan GPU renderer for Saturn's shapes, images and text surfaces.

    Draw calls become vertices in a host-visible buffer. Consecutive calls
    using the same texture and scissor are batched into one vkCmdDraw. The
    widget geometry and texture sampling are rasterized by Vulkan, with no
    full-frame CPU pygame surface or swapchain upload in the normal path.
    """

    _VERTEX_FLOATS = 25
    _VERTEX_STRIDE = _VERTEX_FLOATS * 4
    native_texture_scaling = True
    native_shape_overlay = True
    native_state_layer = True

    def __init__(self, window, *, logical_size=None, pixel_ratio: float = 1.0):
        self._gpu_views = []
        self._gpu_framebuffers = []
        self._gpu_msaa_image = None
        self._gpu_msaa_memory = None
        self._gpu_msaa_view = None
        self._gpu_samples = None
        self._gpu_render_pass = None
        self._gpu_pipeline = None
        self._gpu_pipeline_format = None
        self._gpu_keep_pipeline = False
        self._gpu_descriptor_layout = None
        self._gpu_pipeline_layout = None
        self._gpu_descriptor_pool = None
        self._gpu_sampler = None
        self._gpu_vertex_buffer = None
        self._gpu_vertex_memory = None
        self._gpu_vertex_mapped = None
        self._gpu_vertex_capacity = 0
        self._gpu_upload_buffer = None
        self._gpu_upload_memory = None
        self._gpu_upload_mapped = None
        self._gpu_upload_capacity = 0
        self._pending_textures = []
        self._gpu_capture_buffer = None
        self._gpu_capture_memory = None
        self._gpu_capture_mapped = None
        self._gpu_capture_capacity = 0
        self._gpu_capture_pending = False
        self._gpu_capture_supported = False
        self._gpu_white = None
        self._gpu_tex_cache = OrderedDict()
        self._gpu_immutable_cache = OrderedDict()
        self._atlas_pages = OrderedDict()
        self._atlas_next_id = 0
        self._atlas_size = (1024, 1024)
        self._atlas_limit = 16
        self._gpu_initialized_images = set()
        self._vertices = array("f")
        self._draws = []
        self._clip_gpu = []
        self._clear_color = (0.0, 0.0, 0.0, 1.0)
        self._logical_size = tuple(logical_size or window.size)
        self._pixel_size = tuple(window.size)
        super().__init__(window, logical_size=logical_size,
                         pixel_ratio=pixel_ratio)
        # Keep text/image rasterization at 2x, then scale by the GPU sampler.
        self.scale = SCALE * self.pixel_ratio
        self._gpu_white = self._upload_texture(
            pygame.Surface((1, 1), pygame.SRCALPHA, 32),
            pixels=b"\xff\xff\xff\xff")

    def _create_gpu_globals(self):
        binding = vk.VkDescriptorSetLayoutBinding(
            binding=0, descriptorType=vk.VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
            descriptorCount=1, stageFlags=vk.VK_SHADER_STAGE_FRAGMENT_BIT)
        self._gpu_descriptor_layout = vk.vkCreateDescriptorSetLayout(
            self._device, vk.VkDescriptorSetLayoutCreateInfo(
                bindingCount=1, pBindings=[binding]), None)
        self._gpu_pipeline_layout = vk.vkCreatePipelineLayout(
            self._device, vk.VkPipelineLayoutCreateInfo(
                setLayoutCount=1, pSetLayouts=[self._gpu_descriptor_layout]),
            None)
        self._gpu_descriptor_pool = vk.vkCreateDescriptorPool(
            self._device, vk.VkDescriptorPoolCreateInfo(
                flags=vk.VK_DESCRIPTOR_POOL_CREATE_FREE_DESCRIPTOR_SET_BIT,
                maxSets=1400, poolSizeCount=1,
                pPoolSizes=[vk.VkDescriptorPoolSize(
                    type=vk.VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
                    descriptorCount=1400)]), None)
        self._gpu_sampler = vk.vkCreateSampler(
            self._device, vk.VkSamplerCreateInfo(
                magFilter=vk.VK_FILTER_LINEAR, minFilter=vk.VK_FILTER_LINEAR,
                mipmapMode=vk.VK_SAMPLER_MIPMAP_MODE_NEAREST,
                addressModeU=vk.VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE,
                addressModeV=vk.VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE,
                addressModeW=vk.VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE,
                maxAnisotropy=1.0, maxLod=0.0), None)

    def _create_swapchain(self):
        capabilities = self._get_surface_capabilities(
            self._physical_device, self._surface)
        if not capabilities.supportedUsageFlags & vk.VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT:
            raise VulkanUnavailableError(
                "the Vulkan surface does not support color-attachment rendering")
        self._gpu_capture_supported = bool(
            capabilities.supportedUsageFlags & vk.VK_IMAGE_USAGE_TRANSFER_SRC_BIT)
        formats = self._get_surface_formats(self._physical_device, self._surface)
        self._surface_format = self._choose_surface_format(formats)
        extent = self._choose_extent(capabilities)
        self._extent = (int(extent.width), int(extent.height))
        image_count = capabilities.minImageCount + 1
        if capabilities.maxImageCount:
            image_count = min(image_count, capabilities.maxImageCount)
        families = [self._graphics_family, self._present_family]
        separate = self._graphics_family != self._present_family
        info = vk.VkSwapchainCreateInfoKHR(
            surface=self._surface, minImageCount=image_count,
            imageFormat=self._surface_format.format,
            imageColorSpace=self._surface_format.colorSpace,
            imageExtent=extent, imageArrayLayers=1,
            imageUsage=(vk.VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT |
                        (vk.VK_IMAGE_USAGE_TRANSFER_SRC_BIT
                         if self._gpu_capture_supported else 0)),
            imageSharingMode=(vk.VK_SHARING_MODE_CONCURRENT if separate
                              else vk.VK_SHARING_MODE_EXCLUSIVE),
            queueFamilyIndexCount=2 if separate else 0,
            pQueueFamilyIndices=families if separate else None,
            preTransform=capabilities.currentTransform,
            compositeAlpha=self._choose_composite_alpha(capabilities),
            presentMode=vk.VK_PRESENT_MODE_FIFO_KHR, clipped=vk.VK_TRUE,
            oldSwapchain=None)
        self._swapchain = self._create_swapchain_fn(self._device, info, None)
        self._swapchain_images = list(self._get_swapchain_images(
            self._device, self._swapchain))
        if self._gpu_descriptor_layout is None:
            self._create_gpu_globals()
        selected_samples = self._choose_sample_count()
        if (self._gpu_pipeline is not None and
                (self._gpu_pipeline_format != self._surface_format.format or
                 self._gpu_samples != selected_samples)):
            self._destroy_gpu_pipeline()
        self._gpu_samples = selected_samples
        if self._gpu_pipeline is None:
            self._create_gpu_render_pass()
            self._create_gpu_pipeline()
            self._gpu_pipeline_format = self._surface_format.format
        if self._gpu_samples != vk.VK_SAMPLE_COUNT_1_BIT:
            self._create_msaa_attachment()
        self._gpu_views = [vk.vkCreateImageView(
            self._device, vk.VkImageViewCreateInfo(
                image=image, viewType=vk.VK_IMAGE_VIEW_TYPE_2D,
                format=self._surface_format.format,
                subresourceRange=vk.VkImageSubresourceRange(
                    aspectMask=vk.VK_IMAGE_ASPECT_COLOR_BIT,
                    baseMipLevel=0, levelCount=1,
                    baseArrayLayer=0, layerCount=1)), None)
            for image in self._swapchain_images]
        self._gpu_framebuffers = [vk.vkCreateFramebuffer(
            self._device, vk.VkFramebufferCreateInfo(
                renderPass=self._gpu_render_pass,
                attachmentCount=(2 if self._gpu_msaa_view is not None else 1),
                pAttachments=([self._gpu_msaa_view, view]
                              if self._gpu_msaa_view is not None else [view]),
                width=self._extent[0],
                height=self._extent[1], layers=1), None)
            for view in self._gpu_views]

    def _choose_sample_count(self):
        limits = vk.vkGetPhysicalDeviceProperties(
            self._physical_device).limits
        supported = limits.framebufferColorSampleCounts
        try:
            image_props = vk.vkGetPhysicalDeviceImageFormatProperties(
                self._physical_device, self._surface_format.format,
                vk.VK_IMAGE_TYPE_2D, vk.VK_IMAGE_TILING_OPTIMAL,
                vk.VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT, 0)
            supported &= image_props.sampleCounts
        except vk.VkErrorFormatNotSupported:
            return vk.VK_SAMPLE_COUNT_1_BIT
        except AttributeError:
            # Old Vulkan Python wrappers may omit this optional query.
            pass
        for count in (vk.VK_SAMPLE_COUNT_4_BIT,
                      vk.VK_SAMPLE_COUNT_2_BIT,
                      vk.VK_SAMPLE_COUNT_1_BIT):
            if supported & count:
                return count
        return vk.VK_SAMPLE_COUNT_1_BIT

    def _create_msaa_attachment(self):
        width, height = self._extent
        image = vk.vkCreateImage(self._device, vk.VkImageCreateInfo(
            imageType=vk.VK_IMAGE_TYPE_2D,
            format=self._surface_format.format,
            extent=vk.VkExtent3D(width=width, height=height, depth=1),
            mipLevels=1, arrayLayers=1, samples=self._gpu_samples,
            tiling=vk.VK_IMAGE_TILING_OPTIMAL,
            usage=vk.VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT,
            sharingMode=vk.VK_SHARING_MODE_EXCLUSIVE,
            initialLayout=vk.VK_IMAGE_LAYOUT_UNDEFINED), None)
        requirements = vk.vkGetImageMemoryRequirements(self._device, image)
        memory = vk.vkAllocateMemory(
            self._device, vk.VkMemoryAllocateInfo(
                allocationSize=requirements.size,
                memoryTypeIndex=self._memory_type(
                    requirements.memoryTypeBits,
                    vk.VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT)), None)
        vk.vkBindImageMemory(self._device, image, memory, 0)
        view = vk.vkCreateImageView(self._device,
            vk.VkImageViewCreateInfo(
                image=image, viewType=vk.VK_IMAGE_VIEW_TYPE_2D,
                format=self._surface_format.format,
                subresourceRange=vk.VkImageSubresourceRange(
                    aspectMask=vk.VK_IMAGE_ASPECT_COLOR_BIT,
                    baseMipLevel=0, levelCount=1,
                    baseArrayLayer=0, layerCount=1)), None)
        self._gpu_msaa_image = image
        self._gpu_msaa_memory = memory
        self._gpu_msaa_view = view

    def _choose_extent(self, capabilities):
        if capabilities.currentExtent.width != 0xFFFFFFFF:
            return capabilities.currentExtent
        width, height = self._pixel_size
        return vk.VkExtent2D(
            width=max(capabilities.minImageExtent.width,
                      min(width, capabilities.maxImageExtent.width)),
            height=max(capabilities.minImageExtent.height,
                       min(height, capabilities.maxImageExtent.height)))

    def _create_gpu_render_pass(self):
        multisampled = self._gpu_samples != vk.VK_SAMPLE_COUNT_1_BIT
        color_attachment = vk.VkAttachmentDescription(
            format=self._surface_format.format,
            samples=self._gpu_samples,
            loadOp=vk.VK_ATTACHMENT_LOAD_OP_CLEAR,
            storeOp=(vk.VK_ATTACHMENT_STORE_OP_DONT_CARE if multisampled
                     else vk.VK_ATTACHMENT_STORE_OP_STORE),
            stencilLoadOp=vk.VK_ATTACHMENT_LOAD_OP_DONT_CARE,
            stencilStoreOp=vk.VK_ATTACHMENT_STORE_OP_DONT_CARE,
            initialLayout=vk.VK_IMAGE_LAYOUT_UNDEFINED,
            finalLayout=(vk.VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL
                         if multisampled else vk.VK_IMAGE_LAYOUT_PRESENT_SRC_KHR))
        attachments = [color_attachment]
        reference = vk.VkAttachmentReference(
            attachment=0, layout=vk.VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL)
        if multisampled:
            attachments.append(vk.VkAttachmentDescription(
                format=self._surface_format.format,
                samples=vk.VK_SAMPLE_COUNT_1_BIT,
                loadOp=vk.VK_ATTACHMENT_LOAD_OP_DONT_CARE,
                storeOp=vk.VK_ATTACHMENT_STORE_OP_STORE,
                stencilLoadOp=vk.VK_ATTACHMENT_LOAD_OP_DONT_CARE,
                stencilStoreOp=vk.VK_ATTACHMENT_STORE_OP_DONT_CARE,
                initialLayout=vk.VK_IMAGE_LAYOUT_UNDEFINED,
                finalLayout=vk.VK_IMAGE_LAYOUT_PRESENT_SRC_KHR))
            resolve = vk.VkAttachmentReference(
                attachment=1,
                layout=vk.VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL)
            subpass = vk.VkSubpassDescription(
                pipelineBindPoint=vk.VK_PIPELINE_BIND_POINT_GRAPHICS,
                colorAttachmentCount=1, pColorAttachments=[reference],
                pResolveAttachments=[resolve])
        else:
            subpass = vk.VkSubpassDescription(
                pipelineBindPoint=vk.VK_PIPELINE_BIND_POINT_GRAPHICS,
                colorAttachmentCount=1, pColorAttachments=[reference])
        dependency = vk.VkSubpassDependency(
            srcSubpass=vk.VK_SUBPASS_EXTERNAL, dstSubpass=0,
            srcStageMask=vk.VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
            dstStageMask=vk.VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
            dstAccessMask=vk.VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT)
        self._gpu_render_pass = vk.vkCreateRenderPass(
            self._device, vk.VkRenderPassCreateInfo(
                attachmentCount=len(attachments), pAttachments=attachments,
                subpassCount=1, pSubpasses=[subpass],
                dependencyCount=1, pDependencies=[dependency]), None)

    def _create_gpu_pipeline(self):
        directory = Path(__file__).resolve().parent
        shaders = []
        for name, stage in (("vert", vk.VK_SHADER_STAGE_VERTEX_BIT),
                            ("frag", vk.VK_SHADER_STAGE_FRAGMENT_BIT)):
            code = (directory / f"vulkan_{name}.spv").read_bytes()
            module = vk.vkCreateShaderModule(
                self._device, vk.VkShaderModuleCreateInfo(
                    codeSize=len(code), pCode=code), None)
            shaders.append((module, stage))
        try:
            stages = [vk.VkPipelineShaderStageCreateInfo(
                stage=stage, module=module, pName="main")
                for module, stage in shaders]
            binding = vk.VkVertexInputBindingDescription(
                binding=0, stride=self._VERTEX_STRIDE,
                inputRate=vk.VK_VERTEX_INPUT_RATE_VERTEX)
            attrs = [vk.VkVertexInputAttributeDescription(
                location=location, binding=0, format=fmt, offset=offset)
                for location, fmt, offset in (
                    (0, vk.VK_FORMAT_R32G32_SFLOAT, 0),
                    (1, vk.VK_FORMAT_R32G32_SFLOAT, 8),
                    (2, vk.VK_FORMAT_R32G32_SFLOAT, 16),
                    (3, vk.VK_FORMAT_R32_SFLOAT, 24),
                    (4, vk.VK_FORMAT_R32_SFLOAT, 28),
                    (5, vk.VK_FORMAT_R32G32B32A32_SFLOAT, 32),
                    (6, vk.VK_FORMAT_R32G32B32A32_SFLOAT, 48),
                    (7, vk.VK_FORMAT_R32_SFLOAT, 64),
                    (8, vk.VK_FORMAT_R32G32B32A32_SFLOAT, 68),
                    (9, vk.VK_FORMAT_R32G32B32A32_SFLOAT, 84))]
            vertex_input = vk.VkPipelineVertexInputStateCreateInfo(
                vertexBindingDescriptionCount=1,
                pVertexBindingDescriptions=[binding],
                vertexAttributeDescriptionCount=len(attrs),
                pVertexAttributeDescriptions=attrs)
            assembly = vk.VkPipelineInputAssemblyStateCreateInfo(
                topology=vk.VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST)
            viewport_state = vk.VkPipelineViewportStateCreateInfo(
                viewportCount=1, scissorCount=1)
            raster = vk.VkPipelineRasterizationStateCreateInfo(
                polygonMode=vk.VK_POLYGON_MODE_FILL,
                cullMode=vk.VK_CULL_MODE_NONE,
                frontFace=vk.VK_FRONT_FACE_COUNTER_CLOCKWISE,
                lineWidth=1.0)
            multisample = vk.VkPipelineMultisampleStateCreateInfo(
                rasterizationSamples=self._gpu_samples)
            blend_attachment = vk.VkPipelineColorBlendAttachmentState(
                blendEnable=vk.VK_TRUE,
                srcColorBlendFactor=vk.VK_BLEND_FACTOR_SRC_ALPHA,
                dstColorBlendFactor=vk.VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA,
                colorBlendOp=vk.VK_BLEND_OP_ADD,
                srcAlphaBlendFactor=vk.VK_BLEND_FACTOR_ONE,
                dstAlphaBlendFactor=vk.VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA,
                alphaBlendOp=vk.VK_BLEND_OP_ADD,
                colorWriteMask=(vk.VK_COLOR_COMPONENT_R_BIT |
                                vk.VK_COLOR_COMPONENT_G_BIT |
                                vk.VK_COLOR_COMPONENT_B_BIT |
                                vk.VK_COLOR_COMPONENT_A_BIT))
            blend = vk.VkPipelineColorBlendStateCreateInfo(
                attachmentCount=1, pAttachments=[blend_attachment])
            dynamic = vk.VkPipelineDynamicStateCreateInfo(
                dynamicStateCount=2, pDynamicStates=[
                    vk.VK_DYNAMIC_STATE_VIEWPORT, vk.VK_DYNAMIC_STATE_SCISSOR])
            pipeline_info = vk.VkGraphicsPipelineCreateInfo(
                stageCount=2, pStages=stages,
                pVertexInputState=vertex_input,
                pInputAssemblyState=assembly,
                pViewportState=viewport_state,
                pRasterizationState=raster,
                pMultisampleState=multisample,
                pColorBlendState=blend,
                pDynamicState=dynamic,
                layout=self._gpu_pipeline_layout,
                renderPass=self._gpu_render_pass, subpass=0)
            self._gpu_pipeline = vk.vkCreateGraphicsPipelines(
                self._device, None, 1, [pipeline_info], None)[0]
        finally:
            for module, _ in shaders:
                vk.vkDestroyShaderModule(self._device, module, None)

    def _destroy_swapchain_resources(self):
        if self._device is None:
            return
        for framebuffer in self._gpu_framebuffers:
            vk.vkDestroyFramebuffer(self._device, framebuffer, None)
        self._gpu_framebuffers.clear()
        if self._gpu_msaa_view is not None:
            vk.vkDestroyImageView(self._device, self._gpu_msaa_view, None)
            self._gpu_msaa_view = None
        if self._gpu_msaa_image is not None:
            vk.vkDestroyImage(self._device, self._gpu_msaa_image, None)
            self._gpu_msaa_image = None
        if self._gpu_msaa_memory is not None:
            vk.vkFreeMemory(self._device, self._gpu_msaa_memory, None)
            self._gpu_msaa_memory = None
        for view in self._gpu_views:
            vk.vkDestroyImageView(self._device, view, None)
        self._gpu_views.clear()
        if not self._gpu_keep_pipeline:
            self._destroy_gpu_pipeline()
        super()._destroy_swapchain_resources()

    def _destroy_gpu_pipeline(self):
        if self._gpu_pipeline is not None:
            vk.vkDestroyPipeline(self._device, self._gpu_pipeline, None)
            self._gpu_pipeline = None
        if self._gpu_render_pass is not None:
            vk.vkDestroyRenderPass(self._device, self._gpu_render_pass, None)
            self._gpu_render_pass = None
        self._gpu_pipeline_format = None

    def _recreate_swapchain(self):
        self._gpu_keep_pipeline = True
        try:
            super()._recreate_swapchain()
        finally:
            self._gpu_keep_pipeline = False

    def _create_gpu_buffer(self, size, usage, properties):
        buffer = vk.vkCreateBuffer(self._device, vk.VkBufferCreateInfo(
            size=max(4, size), usage=usage,
            sharingMode=vk.VK_SHARING_MODE_EXCLUSIVE), None)
        requirements = vk.vkGetBufferMemoryRequirements(self._device, buffer)
        memory = vk.vkAllocateMemory(self._device, vk.VkMemoryAllocateInfo(
            allocationSize=requirements.size,
            memoryTypeIndex=self._memory_type(
                requirements.memoryTypeBits, properties)), None)
        vk.vkBindBufferMemory(self._device, buffer, memory, 0)
        return buffer, memory

    def _ensure_vertex_buffer(self, size):
        if size <= self._gpu_vertex_capacity:
            return
        # flip() waits for the preceding frame before modifying this buffer.
        if self._gpu_vertex_mapped is not None:
            vk.vkUnmapMemory(self._device, self._gpu_vertex_memory)
            vk.vkDestroyBuffer(self._device, self._gpu_vertex_buffer, None)
            vk.vkFreeMemory(self._device, self._gpu_vertex_memory, None)
        self._gpu_vertex_capacity = max(64 * 1024, size * 2)
        props = (vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
                 vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)
        self._gpu_vertex_buffer, self._gpu_vertex_memory = \
            self._create_gpu_buffer(self._gpu_vertex_capacity,
                                    vk.VK_BUFFER_USAGE_VERTEX_BUFFER_BIT, props)
        self._gpu_vertex_mapped = vk.vkMapMemory(
            self._device, self._gpu_vertex_memory, 0,
            self._gpu_vertex_capacity, 0)

    def _ensure_capture_buffer(self):
        size = self._extent[0] * self._extent[1] * 4
        if size <= self._gpu_capture_capacity:
            return
        if self._gpu_capture_mapped is not None:
            vk.vkUnmapMemory(self._device, self._gpu_capture_memory)
            vk.vkDestroyBuffer(self._device, self._gpu_capture_buffer, None)
            vk.vkFreeMemory(self._device, self._gpu_capture_memory, None)
        props = (vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
                 vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)
        self._gpu_capture_buffer, self._gpu_capture_memory = \
            self._create_gpu_buffer(size,
                                    vk.VK_BUFFER_USAGE_TRANSFER_DST_BIT, props)
        self._gpu_capture_capacity = size
        self._gpu_capture_mapped = vk.vkMapMemory(
            self._device, self._gpu_capture_memory, 0, size, 0)

    def _ensure_upload_buffer(self, size):
        if size <= self._gpu_upload_capacity:
            return
        if self._gpu_upload_mapped is not None:
            vk.vkUnmapMemory(self._device, self._gpu_upload_memory)
            vk.vkDestroyBuffer(self._device, self._gpu_upload_buffer, None)
            vk.vkFreeMemory(self._device, self._gpu_upload_memory, None)
        self._gpu_upload_capacity = max(64 * 1024, size * 2)
        props = (vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
                 vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)
        self._gpu_upload_buffer, self._gpu_upload_memory = \
            self._create_gpu_buffer(self._gpu_upload_capacity,
                                    vk.VK_BUFFER_USAGE_TRANSFER_SRC_BIT, props)
        self._gpu_upload_mapped = vk.vkMapMemory(
            self._device, self._gpu_upload_memory, 0,
            self._gpu_upload_capacity, 0)

    def _create_texture_resource(self, width, height):
        image = vk.vkCreateImage(self._device, vk.VkImageCreateInfo(
            imageType=vk.VK_IMAGE_TYPE_2D,
            format=vk.VK_FORMAT_R8G8B8A8_UNORM,
            extent=vk.VkExtent3D(width=width, height=height, depth=1),
            mipLevels=1, arrayLayers=1,
            samples=vk.VK_SAMPLE_COUNT_1_BIT,
            tiling=vk.VK_IMAGE_TILING_OPTIMAL,
            usage=(vk.VK_IMAGE_USAGE_TRANSFER_DST_BIT |
                   vk.VK_IMAGE_USAGE_SAMPLED_BIT),
            sharingMode=vk.VK_SHARING_MODE_EXCLUSIVE,
            initialLayout=vk.VK_IMAGE_LAYOUT_UNDEFINED), None)
        requirements = vk.vkGetImageMemoryRequirements(self._device, image)
        image_memory = vk.vkAllocateMemory(
            self._device, vk.VkMemoryAllocateInfo(
                allocationSize=requirements.size,
                memoryTypeIndex=self._memory_type(
                    requirements.memoryTypeBits,
                    vk.VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT)), None)
        vk.vkBindImageMemory(self._device, image, image_memory, 0)
        subresource = vk.VkImageSubresourceRange(
            aspectMask=vk.VK_IMAGE_ASPECT_COLOR_BIT,
            baseMipLevel=0, levelCount=1, baseArrayLayer=0, layerCount=1)
        view = vk.vkCreateImageView(self._device, vk.VkImageViewCreateInfo(
            image=image, viewType=vk.VK_IMAGE_VIEW_TYPE_2D,
            format=vk.VK_FORMAT_R8G8B8A8_UNORM,
            subresourceRange=subresource), None)
        descriptor = vk.vkAllocateDescriptorSets(
            self._device, vk.VkDescriptorSetAllocateInfo(
                descriptorPool=self._gpu_descriptor_pool,
                descriptorSetCount=1,
                pSetLayouts=[self._gpu_descriptor_layout]))[0]
        info = vk.VkDescriptorImageInfo(
            sampler=self._gpu_sampler, imageView=view,
            imageLayout=vk.VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL)
        vk.vkUpdateDescriptorSets(self._device, 1,
            [vk.VkWriteDescriptorSet(
                dstSet=descriptor, dstBinding=0, descriptorCount=1,
                descriptorType=vk.VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
                pImageInfo=[info])], 0, None)
        return (image, image_memory, view, descriptor)

    def _upload_texture(self, surface, *, pixels=None):
        width, height = surface.get_size()
        pixels = pixels if pixels is not None else pygame.image.tobytes(
            surface, "RGBA")
        if len(pixels) != width * height * 4:
            raise ValueError("texture data must be RGBA8")
        texture = self._create_texture_resource(width, height)
        self._pending_textures.append(
            (texture[0], 0, 0, width, height, pixels))
        return texture

    def _record_texture_uploads(self, command):
        if not self._pending_textures:
            return
        unique_images = OrderedDict(
            (id(image), image) for image, _, _, _, _, _
            in self._pending_textures)
        barriers = []
        for image_id, image in unique_images.items():
            initialized = image_id in self._gpu_initialized_images
            barriers.append(vk.VkImageMemoryBarrier(
                srcAccessMask=(vk.VK_ACCESS_SHADER_READ_BIT
                               if initialized else 0),
                dstAccessMask=vk.VK_ACCESS_TRANSFER_WRITE_BIT,
                oldLayout=(vk.VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL
                           if initialized else vk.VK_IMAGE_LAYOUT_UNDEFINED),
                newLayout=vk.VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                srcQueueFamilyIndex=vk.VK_QUEUE_FAMILY_IGNORED,
                dstQueueFamilyIndex=vk.VK_QUEUE_FAMILY_IGNORED,
                image=image,
                subresourceRange=vk.VkImageSubresourceRange(
                    aspectMask=vk.VK_IMAGE_ASPECT_COLOR_BIT,
                    baseMipLevel=0, levelCount=1,
                    baseArrayLayer=0, layerCount=1)))
        vk.vkCmdPipelineBarrier(
            command, vk.VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
            vk.VK_PIPELINE_STAGE_TRANSFER_BIT,
            0, 0, None, 0, None, len(barriers), barriers)
        offset = 0
        for image, x, y, width, height, pixels in self._pending_textures:
            region = vk.VkBufferImageCopy(
                bufferOffset=offset, bufferRowLength=0,
                bufferImageHeight=0,
                imageSubresource=vk.VkImageSubresourceLayers(
                    aspectMask=vk.VK_IMAGE_ASPECT_COLOR_BIT,
                    mipLevel=0, baseArrayLayer=0, layerCount=1),
                imageOffset=vk.VkOffset3D(x=x, y=y, z=0),
                imageExtent=vk.VkExtent3D(
                    width=width, height=height, depth=1))
            vk.vkCmdCopyBufferToImage(
                command, self._gpu_upload_buffer, image,
                vk.VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, [region])
            offset += len(pixels)
        for barrier in barriers:
            barrier.srcAccessMask = vk.VK_ACCESS_TRANSFER_WRITE_BIT
            barrier.dstAccessMask = vk.VK_ACCESS_SHADER_READ_BIT
            barrier.oldLayout = vk.VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL
            barrier.newLayout = vk.VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL
        vk.vkCmdPipelineBarrier(
            command, vk.VK_PIPELINE_STAGE_TRANSFER_BIT,
            vk.VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT,
            0, 0, None, 0, None, len(barriers), barriers)
        self._gpu_initialized_images.update(unique_images)

    def _release_texture(self, texture):
        image, memory, view, descriptor = texture
        self._gpu_initialized_images.discard(id(image))
        vk.vkFreeDescriptorSets(self._device, self._gpu_descriptor_pool,
                                1, [descriptor])
        vk.vkDestroyImageView(self._device, view, None)
        vk.vkDestroyImage(self._device, image, None)
        vk.vkFreeMemory(self._device, memory, None)

    # -- Immediate drawing API: vertices are submitted at flip() ----------
    def _ndc(self, x, y):
        return (2.0 * x * self.pixel_ratio / self._pixel_size[0] - 1.0,
                2.0 * y * self.pixel_ratio / self._pixel_size[1] - 1.0)

    def _append_triangles(self, points, uvs, half, radius, border_width,
                          color, border_color, mode, texture,
                          state_radii=(0, 0, 0, 0),
                          state_info=(0, 0, 0, 0)):
        if not points:
            return
        first = len(self._vertices) // self._VERTEX_FLOATS
        rgba = self._effect_color(color)
        brgba = self._effect_color(border_color)
        common = (float(half[0]), float(half[1]), float(radius),
                  float(border_width), *(c / 255.0 for c in rgba),
                  *(c / 255.0 for c in brgba), float(mode),
                  *(float(v) for v in state_radii),
                  *(float(v) for v in state_info))
        for (x, y), (u, v) in zip(points, uvs):
            self._vertices.extend((*self._ndc(x, y), u, v, *common))
        count = len(points)
        clip = self._clip_gpu[-1] if self._clip_gpu else (
            0, 0, self._pixel_size[0], self._pixel_size[1])
        if self._draws and self._draws[-1][2] is texture and \
                self._draws[-1][3] == clip:
            self._draws[-1][1] += count
        else:
            self._draws.append([first, count, texture, clip])

    def _append_quad(self, x, y, width, height, color, *, radius=0.0,
                     border_width=0.0, border_color=(0, 0, 0, 0),
                     texture=None, textured=False,
                     uv_bounds=(0.0, 0.0, 1.0, 1.0),
                     state_radii=None, state_info=None):
        if width <= 0 or height <= 0:
            return
        x, y = self._translate(x, y)
        texture = texture or self._gpu_white
        # The one-pixel fringe is needed for smooth SDF coverage at edges.
        pad = 0.0 if textured else 1.0 / self.pixel_ratio
        x0, y0 = x - pad, y - pad
        x1, y1 = x + width + pad, y + height + pad
        points = ((x0, y0), (x1, y0), (x1, y1),
                  (x0, y0), (x1, y1), (x0, y1))
        if textured:
            u0, v0, u1, v1 = uv_bounds
            uvs = ((u0, v0), (u1, v0), (u1, v1),
                   (u0, v0), (u1, v1), (u0, v1))
        else:
            uvs = tuple(((px - x) / width, (py - y) / height)
                        for px, py in points)
        self._append_triangles(
            points, uvs, (width / 2, height / 2), radius,
            border_width, color, border_color,
            (2.0 if state_radii is not None else
             1.0 if textured else 0.0), texture,
            state_radii or (0, 0, 0, 0),
            state_info or (0, 0, 0, 0))

    def clear(self, color):
        if (len(self._gpu_tex_cache) > 600 or
                len(self._gpu_immutable_cache) > 600):
            # A texture may still be referenced by the previous submitted
            # frame. Retire it only after that frame has finished.
            vk.vkDeviceWaitIdle(self._device)
            while len(self._gpu_tex_cache) > 500:
                _, texture = self._gpu_tex_cache.popitem(last=False)
                self._release_texture(texture)
            while len(self._gpu_immutable_cache) > 500:
                _, (_, texture, _, page_id) = \
                    self._gpu_immutable_cache.popitem(last=False)
                if page_id is None:
                    self._release_texture(texture)
        self._vertices = array("f")
        self._draws = []
        self._clear_color = tuple(c / 255.0 for c in parse_color(color))

    def fill_rect(self, x, y, w, h, color, radius=0):
        self._append_quad(x, y, w, h, color, radius=radius)

    def overlay_rect(self, x, y, w, h, color, radius=0):
        self.fill_rect(x, y, w, h, color, radius)

    def state_layer(self, x, y, w, h, color, radii, hover, pressed,
                    ripple_x, ripple_y, ripple_radius):
        """GPU-rasterize an asymmetric rounded hover/press ripple."""
        self._append_quad(
            x, y, w, h, color, border_width=hover,
            state_radii=radii,
            state_info=(ripple_x - x, ripple_y - y,
                        ripple_radius, pressed))

    def stroke_rect(self, x, y, w, h, color, width=1, radius=0):
        self._append_quad(x, y, w, h, (0, 0, 0, 0),
                          radius=radius, border_width=width,
                          border_color=color)

    def line(self, x1, y1, x2, y2, color, width=1):
        if x1 == x2:
            self._append_quad(x1 - width / 2, min(y1, y2),
                              width, abs(y2 - y1) or width, color)
            return
        if y1 == y2:
            self._append_quad(min(x1, x2), y1 - width / 2,
                              abs(x2 - x1) or width, width, color)
            return
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        nx, ny = -dy / length * width / 2, dx / length * width / 2
        tx, ty = self._translation_stack[-1]
        points = tuple((px + tx, py + ty) for px, py in (
            (x1 + nx, y1 + ny), (x2 + nx, y2 + ny),
            (x2 - nx, y2 - ny), (x1 + nx, y1 + ny),
            (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)))
        self._append_triangles(points, ((0, 0),) * 6,
                               (1, 1), -1, 0, color,
                               (0, 0, 0, 0), 0, self._gpu_white)

    def circle(self, x, y, radius, color, fill=True):
        self._append_quad(x - radius, y - radius,
                          radius * 2, radius * 2,
                          color if fill else (0, 0, 0, 0),
                          radius=radius,
                          border_width=0 if fill else max(1.0, radius / 8),
                          border_color=(0, 0, 0, 0) if fill else color)

    def arc(self, x, y, radius, start_angle, end_angle, color, width=1):
        if radius <= 0 or width <= 0 or end_angle <= start_angle:
            return
        x, y = self._translate(x, y)
        sweep = end_angle - start_angle
        segments = max(8, int(abs(sweep) * radius / 3))
        inner = max(0.0, radius - width)
        points = []
        for index in range(segments):
            a0 = start_angle + sweep * index / segments
            a1 = start_angle + sweep * (index + 1) / segments
            outer0 = (x + math.cos(a0) * radius,
                      y + math.sin(a0) * radius)
            outer1 = (x + math.cos(a1) * radius,
                      y + math.sin(a1) * radius)
            inner0 = (x + math.cos(a0) * inner,
                      y + math.sin(a0) * inner)
            inner1 = (x + math.cos(a1) * inner,
                      y + math.sin(a1) * inner)
            points.extend((outer0, outer1, inner1,
                           outer0, inner1, inner0))
        self._append_triangles(points, ((0, 0),) * len(points),
                               (1, 1), -1, 0, color,
                               (0, 0, 0, 0), 0, self._gpu_white)

    def _texture_for_surface(self, surface, *, immutable=False):
        if immutable:
            key = id(surface)
            entry = self._gpu_immutable_cache.get(key)
            if entry is not None and entry[0] is surface:
                self._gpu_immutable_cache.move_to_end(key)
                if entry[3] is not None:
                    self._atlas_pages.move_to_end(entry[3])
                return entry[1], entry[2]
            width, height = surface.get_size()
            if width + 2 <= self._atlas_size[0] // 2 and \
                    height + 2 <= self._atlas_size[1] // 2:
                region = self._atlas_place(surface, key)
            else:
                region = None
            if region is not None:
                texture, uv, page_id = region
            else:
                texture = self._upload_texture(surface)
                uv, page_id = (0.0, 0.0, 1.0, 1.0), None
            self._gpu_immutable_cache[key] = (surface, texture, uv, page_id)
            return texture, uv
        raw = pygame.image.tobytes(surface, "RGBA")
        key = (surface.get_size(), hashlib.blake2b(
            raw, digest_size=12).digest())
        texture = self._gpu_tex_cache.get(key)
        if texture is None:
            texture = self._upload_texture(surface, pixels=raw)
            self._gpu_tex_cache[key] = texture
        self._gpu_tex_cache.move_to_end(key)
        return texture, (0.0, 0.0, 1.0, 1.0)

    def _atlas_place(self, surface, cache_key):
        width, height = surface.get_size()
        padded_w, padded_h = width + 2, height + 2
        page_w, page_h = self._atlas_size
        for page_id, page in reversed(self._atlas_pages.items()):
            x, y, row_h = page["x"], page["y"], page["row_h"]
            if x + padded_w > page_w:
                x, y, row_h = 0, y + row_h, 0
            if y + padded_h > page_h:
                continue
            page["x"] = x + padded_w
            page["y"] = y
            page["row_h"] = max(row_h, padded_h)
            page["keys"].add(cache_key)
            self._atlas_pages.move_to_end(page_id)
            padded = pygame.Surface((padded_w, padded_h), pygame.SRCALPHA, 32)
            padded.fill((0, 0, 0, 0))
            padded.blit(surface, (1, 1))
            self._pending_textures.append((
                page["texture"][0], x, y, padded_w, padded_h,
                pygame.image.tobytes(padded, "RGBA")))
            uv = ((x + 1) / page_w, (y + 1) / page_h,
                  (x + 1 + width) / page_w,
                  (y + 1 + height) / page_h)
            return page["texture"], uv, page_id

        if len(self._atlas_pages) >= self._atlas_limit:
            evicted = False
            for page_id, page in list(self._atlas_pages.items()):
                texture = page["texture"]
                if any(draw[2] is texture for draw in self._draws):
                    continue
                if any(upload[0] is texture[0]
                       for upload in self._pending_textures):
                    continue
                vk.vkDeviceWaitIdle(self._device)
                for key in page["keys"]:
                    entry = self._gpu_immutable_cache.get(key)
                    if entry is not None and entry[3] == page_id:
                        del self._gpu_immutable_cache[key]
                self._release_texture(texture)
                del self._atlas_pages[page_id]
                evicted = True
                break
            if not evicted:
                return None
        page_id = self._atlas_next_id
        self._atlas_next_id += 1
        self._atlas_pages[page_id] = {
            "texture": self._create_texture_resource(page_w, page_h),
            "x": 0, "y": 0, "row_h": 0, "keys": set()}
        return self._atlas_place(surface, cache_key)

    def blit(self, surface, x, y, alpha=1.0):
        scale = self.scale
        self.blit_scaled(surface, x, y,
                         surface.get_width() / scale,
                         surface.get_height() / scale, alpha)

    def blit_cached(self, surface, x, y, alpha=1.0):
        scale = self.scale
        self.blit_cached_scaled(surface, x, y,
                                surface.get_width() / scale,
                                surface.get_height() / scale, alpha)

    def blit_scaled(self, surface, x, y, width, height, alpha=1.0):
        texture, uv = self._texture_for_surface(surface)
        self._append_quad(x, y, width, height,
                          (255, 255, 255,
                           max(0, min(255, round(alpha * 255)))),
                          texture=texture, uv_bounds=uv, textured=True)

    def blit_cached_scaled(self, surface, x, y, width, height, alpha=1.0):
        texture, uv = self._texture_for_surface(surface, immutable=True)
        self._append_quad(x, y, width, height,
                          (255, 255, 255,
                           max(0, min(255, round(alpha * 255)))),
                          texture=texture, uv_bounds=uv, textured=True)

    def clip_push(self, x, y, w, h):
        x, y = self._translate(x, y)
        scale = self.pixel_ratio
        x0, y0 = round(x * scale), round(y * scale)
        x1, y1 = round((x + w) * scale), round((y + h) * scale)
        if self._clip_gpu:
            px, py, pw, ph = self._clip_gpu[-1]
            x0, y0 = max(x0, px), max(y0, py)
            x1, y1 = min(x1, px + pw), min(y1, py + ph)
        x0 = max(0, min(self._pixel_size[0], x0))
        y0 = max(0, min(self._pixel_size[1], y0))
        x1 = max(x0, min(self._pixel_size[0], x1))
        y1 = max(y0, min(self._pixel_size[1], y1))
        self._clip_gpu.append((x0, y0, x1 - x0, y1 - y0))

    def clip_pop(self):
        self._clip_gpu.pop()

    def _record_gpu_draw(self, image_index):
        command = self._command_buffer
        vk.vkBeginCommandBuffer(command, vk.VkCommandBufferBeginInfo(
            flags=vk.VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT))
        self._record_texture_uploads(command)
        clear = vk.VkClearValue(color=vk.VkClearColorValue(
            float32=self._clear_color))
        area = vk.VkRect2D(
            offset=vk.VkOffset2D(x=0, y=0),
            extent=vk.VkExtent2D(width=self._extent[0],
                                 height=self._extent[1]))
        begin = vk.VkRenderPassBeginInfo(
            renderPass=self._gpu_render_pass,
            framebuffer=self._gpu_framebuffers[image_index],
            renderArea=area,
            clearValueCount=(2 if self._gpu_msaa_view is not None else 1),
            pClearValues=([clear, clear] if self._gpu_msaa_view is not None
                          else [clear]))
        vk.vkCmdBeginRenderPass(
            command, begin, vk.VK_SUBPASS_CONTENTS_INLINE)
        vk.vkCmdBindPipeline(
            command, vk.VK_PIPELINE_BIND_POINT_GRAPHICS,
            self._gpu_pipeline)
        vk.vkCmdSetViewport(command, 0, 1, [vk.VkViewport(
            x=0.0, y=0.0, width=float(self._extent[0]),
            height=float(self._extent[1]), minDepth=0.0, maxDepth=1.0)])
        if self._draws:
            vk.vkCmdBindVertexBuffers(command, 0, 1,
                                      [self._gpu_vertex_buffer], [0])
        for first, count, texture, (x, y, w, h) in self._draws:
            if w <= 0 or h <= 0:
                continue
            vk.vkCmdSetScissor(command, 0, 1, [vk.VkRect2D(
                offset=vk.VkOffset2D(x=x, y=y),
                extent=vk.VkExtent2D(width=w, height=h))])
            vk.vkCmdBindDescriptorSets(
                command, vk.VK_PIPELINE_BIND_POINT_GRAPHICS,
                self._gpu_pipeline_layout, 0, 1,
                [texture[3]], 0, None)
            vk.vkCmdDraw(command, count, 1, first, 0)
        vk.vkCmdEndRenderPass(command)
        if self._gpu_capture_pending:
            image = self._swapchain_images[image_index]
            subresource = vk.VkImageSubresourceRange(
                aspectMask=vk.VK_IMAGE_ASPECT_COLOR_BIT,
                baseMipLevel=0, levelCount=1,
                baseArrayLayer=0, layerCount=1)
            to_copy = vk.VkImageMemoryBarrier(
                srcAccessMask=vk.VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,
                dstAccessMask=vk.VK_ACCESS_TRANSFER_READ_BIT,
                oldLayout=vk.VK_IMAGE_LAYOUT_PRESENT_SRC_KHR,
                newLayout=vk.VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
                srcQueueFamilyIndex=vk.VK_QUEUE_FAMILY_IGNORED,
                dstQueueFamilyIndex=vk.VK_QUEUE_FAMILY_IGNORED,
                image=image, subresourceRange=subresource)
            vk.vkCmdPipelineBarrier(
                command, vk.VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
                vk.VK_PIPELINE_STAGE_TRANSFER_BIT,
                0, 0, None, 0, None, 1, [to_copy])
            region = vk.VkBufferImageCopy(
                bufferOffset=0, bufferRowLength=0, bufferImageHeight=0,
                imageSubresource=vk.VkImageSubresourceLayers(
                    aspectMask=vk.VK_IMAGE_ASPECT_COLOR_BIT,
                    mipLevel=0, baseArrayLayer=0, layerCount=1),
                imageOffset=vk.VkOffset3D(x=0, y=0, z=0),
                imageExtent=vk.VkExtent3D(
                    width=self._extent[0], height=self._extent[1], depth=1))
            vk.vkCmdCopyImageToBuffer(
                command, image, vk.VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
                self._gpu_capture_buffer, 1, [region])
            to_present = vk.VkImageMemoryBarrier(
                srcAccessMask=vk.VK_ACCESS_TRANSFER_READ_BIT,
                dstAccessMask=0,
                oldLayout=vk.VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
                newLayout=vk.VK_IMAGE_LAYOUT_PRESENT_SRC_KHR,
                srcQueueFamilyIndex=vk.VK_QUEUE_FAMILY_IGNORED,
                dstQueueFamilyIndex=vk.VK_QUEUE_FAMILY_IGNORED,
                image=image, subresourceRange=subresource)
            vk.vkCmdPipelineBarrier(
                command, vk.VK_PIPELINE_STAGE_TRANSFER_BIT,
                vk.VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,
                0, 0, None, 0, None, 1, [to_present])
        vk.vkEndCommandBuffer(command)

    def flip(self):
        if self._closed:
            return
        shot_path = os.environ.get("SATURN_SHOT")
        capture_for_shot = bool(shot_path and not self._gpu_capture_pending)
        vk.vkWaitForFences(
            self._device, 1, [self._in_flight], vk.VK_TRUE, vk.UINT64_MAX)
        try:
            image_index = self._acquire_next_image(
                self._device, self._swapchain, vk.UINT64_MAX,
                self._image_available, None)
        except vk.VkErrorOutOfDateKhr:
            self._recreate_swapchain()
            return
        except vk.VkSuboptimalKhr:
            consume = vk.VkSubmitInfo(
                pWaitSemaphores=[self._image_available],
                pWaitDstStageMask=[
                    vk.VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT])
            vk.vkQueueSubmit(self._graphics_queue, 1, [consume], None)
            self._recreate_swapchain()
            return
        data = self._vertices.tobytes()
        if data:
            self._ensure_vertex_buffer(len(data))
            self._gpu_vertex_mapped[:len(data)] = data
        if self._pending_textures:
            upload_size = sum(len(item[5]) for item in self._pending_textures)
            self._ensure_upload_buffer(upload_size)
            offset = 0
            for _, _, _, _, _, pixels in self._pending_textures:
                self._gpu_upload_mapped[offset:offset + len(pixels)] = pixels
                offset += len(pixels)
        if capture_for_shot and self._gpu_capture_supported:
            self._ensure_capture_buffer()
            self._gpu_capture_pending = True
        vk.vkResetFences(self._device, 1, [self._in_flight])
        vk.vkResetCommandBuffer(self._command_buffer, 0)
        self._record_gpu_draw(image_index)
        submit = vk.VkSubmitInfo(
            pWaitSemaphores=[self._image_available],
            pWaitDstStageMask=[
                vk.VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT],
            pCommandBuffers=[self._command_buffer],
            pSignalSemaphores=[self._render_finished])
        vk.vkQueueSubmit(self._graphics_queue, 1,
                         [submit], self._in_flight)
        self._pending_textures.clear()
        present = vk.VkPresentInfoKHR(
            pWaitSemaphores=[self._render_finished],
            pSwapchains=[self._swapchain],
            pImageIndices=[image_index])
        try:
            self._queue_present(self._present_queue, present)
        except (vk.VkErrorOutOfDateKhr, vk.VkSuboptimalKhr):
            self._recreate_swapchain()
        if capture_for_shot and self._gpu_capture_supported:
            vk.vkWaitForFences(
                self._device, 1, [self._in_flight], vk.VK_TRUE,
                vk.UINT64_MAX)
            try:
                pygame.image.save(self._capture_surface(), shot_path)
            finally:
                self._gpu_capture_pending = False

    def _capture_surface(self):
        length = self._extent[0] * self._extent[1] * 4
        data = bytes(self._gpu_capture_mapped[:length])
        fmt = ("BGRA" if self._surface_format.format in (
            vk.VK_FORMAT_B8G8R8A8_UNORM,
            vk.VK_FORMAT_B8G8R8A8_SRGB) else "RGBA")
        return pygame.image.frombytes(data, self._extent, fmt)

    def screenshot(self):
        """Capture the current command stream from the GPU on demand."""
        if not self._gpu_capture_supported:
            raise VulkanUnavailableError(
                "this Vulkan surface does not support screenshot readback")
        vk.vkWaitForFences(
            self._device, 1, [self._in_flight], vk.VK_TRUE, vk.UINT64_MAX)
        self._ensure_capture_buffer()
        self._gpu_capture_pending = True
        try:
            self.flip()
            vk.vkWaitForFences(
                self._device, 1, [self._in_flight], vk.VK_TRUE,
                vk.UINT64_MAX)
            return self._capture_surface()
        finally:
            self._gpu_capture_pending = False

    def on_resize(self, width, height, *, pixel_size=None,
                  pixel_ratio: float | None = None):
        self._logical_size = (max(1, int(width)), max(1, int(height)))
        target = (tuple(max(1, int(v)) for v in pixel_size)
                  if pixel_size is not None else self._logical_size)
        size_changed = target != self._pixel_size
        self._pixel_size = target
        if pixel_ratio is not None:
            self.pixel_ratio = max(1.0, float(pixel_ratio))
        self.scale = SCALE * self.pixel_ratio
        if size_changed and self._swapchain is not None:
            self._recreate_swapchain()

    def close(self):
        if self._closed:
            return
        if self._device is not None:
            vk.vkDeviceWaitIdle(self._device)
            self._gpu_keep_pipeline = False
            self._destroy_swapchain_resources()
            for texture in self._gpu_tex_cache.values():
                self._release_texture(texture)
            for _, texture, _, page_id in self._gpu_immutable_cache.values():
                if page_id is None:
                    self._release_texture(texture)
            for page in self._atlas_pages.values():
                self._release_texture(page["texture"])
            if self._gpu_white is not None:
                self._release_texture(self._gpu_white)
            self._gpu_tex_cache.clear()
            self._gpu_immutable_cache.clear()
            self._atlas_pages.clear()
            self._gpu_white = None
            if self._gpu_vertex_mapped is not None:
                vk.vkUnmapMemory(self._device, self._gpu_vertex_memory)
                vk.vkDestroyBuffer(self._device, self._gpu_vertex_buffer, None)
                vk.vkFreeMemory(self._device, self._gpu_vertex_memory, None)
                self._gpu_vertex_mapped = None
            if self._gpu_upload_mapped is not None:
                vk.vkUnmapMemory(self._device, self._gpu_upload_memory)
                vk.vkDestroyBuffer(self._device, self._gpu_upload_buffer, None)
                vk.vkFreeMemory(self._device, self._gpu_upload_memory, None)
                self._gpu_upload_mapped = None
            if self._gpu_capture_mapped is not None:
                vk.vkUnmapMemory(self._device, self._gpu_capture_memory)
                vk.vkDestroyBuffer(self._device, self._gpu_capture_buffer, None)
                vk.vkFreeMemory(self._device, self._gpu_capture_memory, None)
                self._gpu_capture_mapped = None
            if self._gpu_sampler is not None:
                vk.vkDestroySampler(self._device, self._gpu_sampler, None)
                self._gpu_sampler = None
            if self._gpu_descriptor_pool is not None:
                vk.vkDestroyDescriptorPool(
                    self._device, self._gpu_descriptor_pool, None)
                self._gpu_descriptor_pool = None
            if self._gpu_pipeline_layout is not None:
                vk.vkDestroyPipelineLayout(
                    self._device, self._gpu_pipeline_layout, None)
                self._gpu_pipeline_layout = None
            if self._gpu_descriptor_layout is not None:
                vk.vkDestroyDescriptorSetLayout(
                    self._device, self._gpu_descriptor_layout, None)
                self._gpu_descriptor_layout = None
        super().close()
