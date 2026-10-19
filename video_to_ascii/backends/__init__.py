"""Select a frame renderer without importing optional GPU libraries eagerly.

Renderers expose name, pixel_format, frame_to_cells(), configure_raster(), and
render_frame(). Video decoding and encoding are selected separately.
"""
import sys

BACKENDS = ('cpu', 'cuda', 'metal', 'mlx', 'auto')


def normalize_backend(backend):
    if backend not in BACKENDS:
        raise ValueError('Backend must be cpu, cuda, metal, mlx, or auto')
    return 'metal' if backend == 'mlx' else backend


def backend_for(backend):
    backend = normalize_backend(backend)
    if backend == 'auto':
        return 'metal' if sys.platform == 'darwin' else 'cuda'
    return backend


def create_renderer(backend, strategy, rasterizer=None):
    """Initialize a renderer; only auto permits GPU-to-CPU startup fallback."""
    target = backend_for(backend)
    try:
        if target == 'cuda':
            from .cuda import CudaCellMapper
            renderer = CudaCellMapper(strategy)
        elif target == 'metal':
            from .metal import MlxCellMapper
            renderer = MlxCellMapper(strategy)
        else:
            from .cpu import CpuRenderer
            renderer = CpuRenderer(strategy)
        if rasterizer is not None:
            renderer.configure_raster(rasterizer)
    except Exception as exc:
        if backend != 'auto' or target == 'cpu':
            raise RuntimeError(f'{target.upper()} renderer failed: {exc}') from exc
        print(f'{target.upper()} rendering unavailable; using CPU: {exc}', file=sys.stderr)
        from .cpu import CpuRenderer
        renderer = CpuRenderer(strategy)
        if rasterizer is not None:
            renderer.configure_raster(rasterizer)
    print(f'ASCII renderer: {renderer.name}', file=sys.stderr)
    return renderer
