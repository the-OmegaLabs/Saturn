"""Vulkan's optional additive ShaderBuffer pass; no CPU rasterization."""
from collections import OrderedDict
import vulkan as vk
from .shader_source import buffer_source, compile_spirv, ShaderCompilationError


def _initialize(renderer):
    renderer._shader_buffers = OrderedDict()
    renderer._buffer_pipelines = OrderedDict()
    renderer._shader_buffer_draws = []
    attachment = vk.VkAttachmentDescription(
        format=vk.VK_FORMAT_R8G8B8A8_UNORM, samples=vk.VK_SAMPLE_COUNT_1_BIT,
        loadOp=vk.VK_ATTACHMENT_LOAD_OP_CLEAR, storeOp=vk.VK_ATTACHMENT_STORE_OP_STORE,
        stencilLoadOp=vk.VK_ATTACHMENT_LOAD_OP_DONT_CARE,
        stencilStoreOp=vk.VK_ATTACHMENT_STORE_OP_DONT_CARE,
        initialLayout=vk.VK_IMAGE_LAYOUT_UNDEFINED,
        finalLayout=vk.VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL)
    reference = vk.VkAttachmentReference(attachment=0, layout=vk.VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL)
    subpass = vk.VkSubpassDescription(pipelineBindPoint=vk.VK_PIPELINE_BIND_POINT_GRAPHICS,
                                    colorAttachmentCount=1, pColorAttachments=[reference])
    dependency = vk.VkSubpassDependency(srcSubpass=0, dstSubpass=vk.VK_SUBPASS_EXTERNAL,
        srcStageMask=vk.VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
        dstStageMask=vk.VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT,
        srcAccessMask=vk.VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,
        dstAccessMask=vk.VK_ACCESS_SHADER_READ_BIT)
    renderer._buffer_render_pass = vk.vkCreateRenderPass(renderer._device,
        vk.VkRenderPassCreateInfo(attachmentCount=1, pAttachments=[attachment],
            subpassCount=1, pSubpasses=[subpass], dependencyCount=1, pDependencies=[dependency]), None)


def _release(renderer, target):
    vk.vkDestroyFramebuffer(renderer._device, target[2], None)
    renderer._release_texture(target[1])


def prepare_buffer(renderer, buffer_pass, layout, width, height, offset):
    if not hasattr(renderer, '_shader_buffers'):
        _initialize(renderer)
    token, vertex, fragment, instances = buffer_pass
    key = (vertex, fragment, layout)
    failure_key = ('buffer', *key)
    if failure_key in renderer._custom_failures:
        raise ShaderCompilationError(renderer._custom_failures[failure_key])
    resources = renderer._custom_uniform_resources
    active_pipelines = {draw[1] for draw in renderer._shader_buffer_draws}
    if key not in renderer._buffer_pipelines:
        try:
            pipeline = renderer._create_gpu_pipeline(
                compile_spirv(buffer_source(fragment, layout, vulkan=True)), resources[1],
                vertex_code=compile_spirv(buffer_source(vertex, layout, vertex=True, vulkan=True), 'vert'),
                render_pass=renderer._buffer_render_pass, additive=True)
        except ShaderCompilationError as error:
            renderer._custom_failures[failure_key] = str(error)
            if len(renderer._custom_failures) > 32:
                renderer._custom_failures.popitem(last=False)
            raise
        renderer._buffer_pipelines[key] = pipeline
        if len(renderer._buffer_pipelines) > 16:
            for old_key, old in tuple(renderer._buffer_pipelines.items()):
                if old_key != key and old not in active_pipelines:
                    vk.vkDeviceWaitIdle(renderer._device)
                    vk.vkDestroyPipeline(renderer._device, old, None)
                    del renderer._buffer_pipelines[old_key]
                    break
    pipeline = renderer._buffer_pipelines[key]
    renderer._buffer_pipelines.move_to_end(key)
    # A repeated draw of one control needs a separate image until compositing.
    occurrence = sum(1 for draw in renderer._shader_buffer_draws if draw[4] == token)
    target_key = (token, occurrence)
    size = max(1, round(width*renderer.scale)), max(1, round(height*renderer.scale))
    target = renderer._shader_buffers.get(target_key)
    if target is not None and target[0] != size:
        vk.vkDeviceWaitIdle(renderer._device)
        _release(renderer, target)
        del renderer._shader_buffers[target_key]
        target = None
    if target is None:
        texture = renderer._create_texture_resource(*size, render_target=True)
        try:
            framebuffer = vk.vkCreateFramebuffer(renderer._device, vk.VkFramebufferCreateInfo(
                renderPass=renderer._buffer_render_pass, attachmentCount=1, pAttachments=[texture[2]],
                width=size[0], height=size[1], layers=1), None)
        except Exception:
            renderer._release_texture(texture)
            raise
        target = renderer._shader_buffers[target_key] = size, texture, framebuffer
    renderer._shader_buffers.move_to_end(target_key)
    active_targets = {id(draw[0]) for draw in renderer._shader_buffer_draws}
    if len(renderer._shader_buffers) > 16:
        for old_key, old in tuple(renderer._shader_buffers.items()):
            if old_key != target_key and id(old) not in active_targets:
                vk.vkDeviceWaitIdle(renderer._device)
                _release(renderer, old)
                del renderer._shader_buffers[old_key]
                break
    renderer._shader_buffer_draws.append((target, pipeline, offset, instances, token))
    return target[1]


def record_buffers(renderer, command):
    resources = renderer._custom_uniform_resources
    for (size, _, framebuffer), pipeline, offset, instances, _ in renderer._shader_buffer_draws:
        area = vk.VkRect2D(offset=vk.VkOffset2D(x=0,y=0), extent=vk.VkExtent2D(width=size[0],height=size[1]))
        begin = vk.VkRenderPassBeginInfo(renderPass=renderer._buffer_render_pass,
            framebuffer=framebuffer, renderArea=area, clearValueCount=1,
            pClearValues=[vk.VkClearValue(color=vk.VkClearColorValue(float32=(0,0,0,0)))])
        vk.vkCmdBeginRenderPass(command, begin, vk.VK_SUBPASS_CONTENTS_INLINE)
        vk.vkCmdBindPipeline(command, vk.VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline)
        vk.vkCmdSetViewport(command, 0, 1, [vk.VkViewport(x=0.,y=0.,width=float(size[0]),
            height=float(size[1]),minDepth=0.,maxDepth=1.)])
        vk.vkCmdSetScissor(command, 0, 1, [area])
        vk.vkCmdBindDescriptorSets(command, vk.VK_PIPELINE_BIND_POINT_GRAPHICS,
            resources[1], 1, 1, [resources[3]], 1, [offset])
        vk.vkCmdDraw(command, 6, instances, 0, 0)
        vk.vkCmdEndRenderPass(command)


def close_buffers(renderer):
    for pipeline in renderer._buffer_pipelines.values():
        vk.vkDestroyPipeline(renderer._device, pipeline, None)
    for target in renderer._shader_buffers.values():
        _release(renderer, target)
    vk.vkDestroyRenderPass(renderer._device, renderer._buffer_render_pass, None)
    renderer._buffer_pipelines.clear()
    renderer._shader_buffers.clear()
    renderer._shader_buffer_draws.clear()
