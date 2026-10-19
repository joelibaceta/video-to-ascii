"""CUDA kernels for luminance, glyph choice, ANSI mapping, and NV12 rasterization."""
import os
from pathlib import Path

import numpy as np

from ..render_strategy.image_processor import DENSITY

CUDA_SOURCE = r'''
extern "C" __global__ void map_cells(
    const unsigned char* bgr, unsigned char* glyphs, unsigned char* ansi,
    const unsigned char* chars, int count, int nchar, int colored) {
    int i = blockDim.x * blockIdx.x + threadIdx.x;
    if (i >= count) return;
    double r = bgr[i*3+2], g = bgr[i*3+1], b = bgr[i*3];
    double brightness = colored ? 0.267*r + 0.642*g + 0.091*b
                                : 0.2126*r + 0.7152*g + 0.0722*b;
    int index = (int)(brightness * (nchar-1) / 255.0 + 1e-12);
    glyphs[i] = chars[index < nchar ? index : nchar-1];
    if (!colored) { ansi[i] = 231; return; }
    double high = fmax(r, fmax(g, b)), low = fmin(r, fmin(g, b));
    double saturation = high ? (high-low)/high : 0;
    double ratio = saturation ? fmin(saturation+0.3, 1.0)/saturation : 1.0;
    int rgb[3] = {(int)fmax(0.0, fmin(255.0, high-(high-r)*ratio)),
                  (int)fmax(0.0, fmin(255.0, high-(high-g)*ratio)),
                  (int)fmax(0.0, fmin(255.0, high-(high-b)*ratio))};
    int levels[6] = {0, 95, 135, 175, 215, 255};
    int cube[3], cube_error = 0;
    for (int channel=0; channel<3; channel++) {
        int best=0, error=100000;
        for (int k=0; k<6; k++) {
            int delta = rgb[channel]-levels[k], distance=delta*delta;
            if (distance < error) { best=k; error=distance; }
        }
        cube[channel]=best; cube_error+=error;
    }
    int gray = (int)ceil(((rgb[0]+rgb[1]+rgb[2])/3.0-8)/10.0-0.5);
    gray = gray < 0 ? 0 : (gray > 23 ? 23 : gray);
    int gray_error=0;
    for (int k=0; k<3; k++) { int delta=rgb[k]-(8+gray*10); gray_error+=delta*delta; }
    ansi[i] = gray_error < cube_error ? 232+gray : 16+36*cube[0]+6*cube[1]+cube[2];
}

__device__ int clamp_byte(int value) { return value < 0 ? 0 : (value > 255 ? 255 : value); }

extern "C" __global__ void raster_nv12(
    const unsigned char* glyphs, const unsigned char* ansi,
    const unsigned char* masks, const unsigned char* palette, unsigned char* output,
    int cols, int rows, int cw, int ch, int width, int height) {
    int i = blockDim.x * blockIdx.x + threadIdx.x;
    if (i >= width*height/4) return;
    int x=(i % (width/2))*2, y=(i/(width/2))*2;
    int top=(height-rows*ch)/2, left=(width-cols*cw)/2;
    int sum_u=0, sum_v=0;
    for (int dy=0; dy<2; dy++) for (int dx=0; dx<2; dx++) {
        int px=x+dx-left, py=y+dy-top, r=0, g=0, b=0;
        if (px>=0 && py>=0 && px<cols*cw && py<rows*ch) {
            int cell=(py/ch)*cols+px/cw;
            int mask=masks[glyphs[cell]*cw*ch+(py%ch)*cw+px%cw];
            int color=ansi[cell]*3;
            r=mask*palette[color]/255; g=mask*palette[color+1]/255; b=mask*palette[color+2]/255;
        }
        // Limited-range BT.601 YUV, matching FFmpeg's standard RGB conversion.
        int luma=((66*r+129*g+25*b+128)>>8)+16;
        sum_u+=((-38*r-74*g+112*b+128)>>8)+128;
        sum_v+=((112*r-94*g-18*b+128)>>8)+128;
        output[(y+dy)*width+x+dx]=clamp_byte(luma);
    }
    int uv=width*height+(y/2)*width+x;
    output[uv]=clamp_byte((sum_u+2)/4); output[uv+1]=clamp_byte((sum_v+2)/4);
}
'''


class CudaCellMapper:
    name = 'cuda'
    pixel_format = 'nv12'

    def __init__(self, strategy):
        # Honor user paths; otherwise use the locally installed CUDA toolkit.
        if 'CUDA_PATH' not in os.environ and Path('/usr/local/cuda').exists():
            os.environ['CUDA_PATH'] = '/usr/local/cuda'
        import cupy as cp
        self.cp = cp
        from ..render_strategy.ascii_bw_strategy import AsciiBWStrategy
        from ..render_strategy.ascii_color_filled_strategy import AsciiColorFilledStrategy
        self.colored = not isinstance(strategy, AsciiBWStrategy)
        density = 2 if isinstance(strategy, AsciiColorFilledStrategy) else (1 if self.colored else 0)
        self.all_chars = list(dict.fromkeys(c for collection in DENSITY for c in collection))
        char_index = {c: i for i, c in enumerate(self.all_chars)}
        self.chars = cp.asarray(np.array([char_index[c] for c in DENSITY[density]], dtype=np.uint8))
        self.map_kernel = cp.RawKernel(CUDA_SOURCE, 'map_cells', options=('--fmad=false',))
        self.raster_kernel = cp.RawKernel(CUDA_SOURCE, 'raster_nv12')
        self.shape = None
        # Validate initialization and compilation now, before creating output files.
        self.map_device(np.zeros((1, 1, 3), dtype=np.uint8))
        cp.cuda.Stream.null.synchronize()

    def map_device(self, frame):
        if (frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3
                or not frame.shape[0] or not frame.shape[1]):
            raise ValueError('CUDA frames must be nonempty uint8 BGR arrays')
        on_device = isinstance(frame, self.cp.ndarray)
        frame = self.cp.ascontiguousarray(frame) if on_device else np.ascontiguousarray(frame)
        rows, cols = frame.shape[:2]
        if self.shape != (rows, cols):
            self.shape = (rows, cols)
            self.input = self.cp.empty(frame.shape, dtype=self.cp.uint8)
            self.glyphs = self.cp.empty((rows, cols), dtype=self.cp.uint8)
            self.ansi = self.cp.empty((rows, cols), dtype=self.cp.uint8)
        if on_device:
            self.input[...] = frame
        else:
            self.input.set(frame)
        self.map_kernel(((rows*cols+255)//256,), (256,),
                        (self.input, self.glyphs, self.ansi, self.chars,
                         np.int32(rows*cols), np.int32(len(self.chars)), np.int32(self.colored)))
        return self.glyphs, self.ansi

    def frame_to_cells(self, frame):
        glyphs, ansi = self.map_device(frame)
        chars = np.array(self.all_chars)[glyphs.get()]
        return chars, ansi.get() if self.colored else None

    def configure_raster(self, rasterizer):
        if (rasterizer.width <= 0 or rasterizer.height <= 0
                or rasterizer.width % 2 or rasterizer.height % 2):
            raise ValueError('NV12 raster dimensions must be positive and even')
        self.rasterizer = rasterizer
        self.masks = self.cp.asarray(rasterizer.masks)
        self.palette = self.cp.asarray(rasterizer.palette)
        size = rasterizer.width*rasterizer.height*3//2
        self.output = self.cp.empty(size, dtype=self.cp.uint8)
        self.pinned = self.cp.cuda.alloc_pinned_memory(size)
        self.host_output = np.frombuffer(self.pinned, dtype=np.uint8, count=size)
        self.raster_kernel.compile()

    def render_nv12(self, frame):
        glyphs, ansi = self.map_device(frame)
        rows, cols = frame.shape[:2]
        r = self.rasterizer
        count = r.width*r.height//4
        self.raster_kernel(((count+255)//256,), (256,),
                           (glyphs, ansi, self.masks, self.palette, self.output,
                            *map(np.int32, (cols, rows, r.cell_width, r.cell_height, r.width, r.height))))
        self.output.get(out=self.host_output)
        return memoryview(self.host_output)

    render_frame = render_nv12
