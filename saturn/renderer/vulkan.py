"""Vulkan presentation backend.

Saturn's widgets target a small immediate-mode renderer interface. This first
Vulkan backend keeps the deterministic 2x rasterizer and uses Vulkan for the
window surface, swapchain, synchronization, transfer, and presentation. A
frame is uploaded through a host-visible staging buffer and copied into the
acquired swapchain image, so no OpenGL context or software SDL presentation is
involved.
"""
from __future__ import annotations

import ctypes
import ctypes.util
import os
from pathlib import Path

import pygame
import vulkan as vk

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


class VulkanRenderer(SoftwareRenderer):
    """Render Saturn frames into an SDL Vulkan window."""

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
        mapped = vk.vkMapMemory(
            self._device, self._staging_memory, 0, len(data), 0)
        mapped[:] = data
        vk.vkUnmapMemory(self._device, self._staging_memory)

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
        if pixel_ratio is not None:
            self.pixel_ratio = max(1.0, float(pixel_ratio))
            self._aa_scale = 1 if self.pixel_ratio >= 1.5 else SCALE
            self.scale = self._aa_scale * self.pixel_ratio
        target = tuple(pixel_size) if pixel_size is not None else (width, height)
        target = tuple(max(1, int(value)) for value in target)
        changed = self.screen.get_size() != target
        self.screen = pygame.Surface(target, pygame.SRCALPHA, 32)
        self._buf = pygame.Surface(
            (target[0] * self._aa_scale, target[1] * self._aa_scale),
            pygame.SRCALPHA, 32)
        self._apply_clip()
        if changed and self._swapchain is not None:
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
