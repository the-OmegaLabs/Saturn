"""Shared GPU selector validation and exact/unique-name matching."""
class GPUSelectionError(ValueError):
    """The requested GPU cannot be used by this backend."""


def validate_gpu(gpu):
    if gpu is None:
        return None
    if isinstance(gpu, bool) or not isinstance(gpu, (str, int)):
        raise TypeError('gpu must be a GPU name, a nonnegative index, or None')
    if isinstance(gpu, int) and gpu < 0:
        raise ValueError('gpu index must be nonnegative')
    if isinstance(gpu, str):
        gpu = gpu.strip()
        if not gpu:
            raise ValueError('gpu name cannot be empty')
    return gpu


def normalized_name(name):
    return str(name).split('/PCIe',1)[0].strip().casefold()


def select_gpu(names, gpu, default=0):
    gpu = validate_gpu(gpu)
    names = tuple(names)
    if not names:
        raise GPUSelectionError('No compatible GPU is available')
    if gpu is None:
        return default
    if isinstance(gpu, int):
        if gpu < len(names):
            return gpu
        raise GPUSelectionError(f'GPU index {gpu} is unavailable; available GPUs: {names}')
    wanted = normalized_name(gpu)
    matches = [i for i,name in enumerate(names) if normalized_name(name)==wanted]
    if not matches:
        matches = [i for i,name in enumerate(names) if wanted in normalized_name(name)]
    if len(matches)==1:
        return matches[0]
    if len(matches)>1:
        raise GPUSelectionError(f'GPU name {gpu!r} is ambiguous; select an index from {names}')
    raise GPUSelectionError(f'GPU {gpu!r} is unavailable; available GPUs: {names}')
