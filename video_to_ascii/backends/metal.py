"""Optional Apple Silicon glyph mapping and NV12 rasterization using MLX/Metal."""
import numpy as np

from ..render_strategy.image_processor import DENSITY
from ..colors import normalize_rgb


MAP_SOURCE = r'''
int count=params[0], nchar=params[1], colored=params[2];
int i = int(thread_position_in_grid.x);
    if (i >= count) return;
    float r = bgr[i*3+2], g = bgr[i*3+1], b = bgr[i*3];
    int intensity = colored ? 267*int(r) + 642*int(g) + 91*int(b)
                            : 2126*int(r) + 7152*int(g) + 722*int(b);
    int index = intensity * (nchar-1) / (colored ? 255000 : 2550000);
    glyphs[i] = chars[index < nchar ? index : nchar-1];
    if (!colored) { ansi[i] = 231; return; }
    int rgb[3] = {normalized[i*3], normalized[i*3+1], normalized[i*3+2]};
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
    int gray = (int)metal::ceil(((rgb[0]+rgb[1]+rgb[2])/3.0f-8)/10.0f-0.5f);
    gray = gray < 0 ? 0 : (gray > 23 ? 23 : gray);
    int gray_error=0;
    for (int k=0; k<3; k++) { int delta=rgb[k]-(8+gray*10); gray_error+=delta*delta; }
    ansi[i] = gray_error < cube_error ? 232+gray : 16+36*cube[0]+6*cube[1]+cube[2];
'''

RASTER_SOURCE = r'''
int cols=params[0], rows=params[1], cw=params[2], ch=params[3], width=params[4], height=params[5];
int i = int(thread_position_in_grid.x);
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
        output[(y+dy)*width+x+dx]=metal::clamp(luma, 0, 255);
    }
    int uv=width*height+(y/2)*width+x;
    output[uv]=metal::clamp((sum_u+2)/4, 0, 255); output[uv+1]=metal::clamp((sum_v+2)/4, 0, 255);
'''


class MlxCellMapper:
    name = 'metal'
    pixel_format = 'nv12'

    def __init__(self, strategy):
        import mlx.core as mx
        if not mx.metal.is_available():
            raise RuntimeError('MLX Metal GPU is unavailable')
        from ..render_strategy.ascii_bw_strategy import AsciiBWStrategy
        from ..render_strategy.ascii_color_filled_strategy import AsciiColorFilledStrategy
        self.mx = mx
        self.colored = not isinstance(strategy, AsciiBWStrategy)
        density = 2 if isinstance(strategy, AsciiColorFilledStrategy) else (1 if self.colored else 0)
        self.all_chars = list(dict.fromkeys(c for collection in DENSITY for c in collection))
        self.chars = mx.array([self.all_chars.index(c) for c in DENSITY[density]], dtype=mx.uint8)
        self.map_kernel = mx.fast.metal_kernel(
            name='ascii_map_cells', input_names=['bgr', 'normalized', 'chars', 'params'],
            output_names=['glyphs', 'ansi'], source=MAP_SOURCE)
        self.raster_kernel = mx.fast.metal_kernel(
            name='ascii_raster_nv12', input_names=['glyphs', 'ansi', 'masks', 'palette', 'params'],
            output_names=['output'], source=RASTER_SOURCE)
        mx.eval(*self.map_device(np.zeros((1, 1, 3), dtype=np.uint8)))

    def map_device(self, frame):
        if (frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3
                or not frame.shape[0] or not frame.shape[1]):
            raise ValueError('MLX frames must be nonempty uint8 BGR arrays')
        mx = self.mx
        rows, cols = frame.shape[:2]
        normalized = normalize_rgb(frame) if self.colored else np.ascontiguousarray(frame[..., ::-1])
        return self.map_kernel(
            inputs=[mx.array(np.ascontiguousarray(frame)), mx.array(normalized), self.chars,
                    mx.array([rows*cols, len(self.chars), int(self.colored)], dtype=mx.int32)],
            grid=(rows*cols, 1, 1), threadgroup=(256, 1, 1),
            output_shapes=[(rows, cols), (rows, cols)],
            output_dtypes=[mx.uint8, mx.uint8], stream=mx.gpu)

    def frame_to_cells(self, frame):
        glyphs, ansi = self.map_device(frame)
        self.mx.eval(glyphs, ansi)
        return np.array(self.all_chars)[np.array(glyphs)], np.array(ansi) if self.colored else None

    def configure_raster(self, rasterizer):
        if (rasterizer.width <= 0 or rasterizer.height <= 0
                or rasterizer.width % 2 or rasterizer.height % 2):
            raise ValueError('NV12 raster dimensions must be positive and even')
        self.rasterizer = rasterizer
        self.masks = self.mx.array(rasterizer.masks)
        self.palette = self.mx.array(rasterizer.palette)
        # Compile and evaluate rasterization before opening an encoder, allowing
        # auto mode to recover from allocation or kernel compilation failures.
        self.render_frame(np.zeros((1, 1, 3), dtype=np.uint8))

    def render_nv12(self, frame):
        mx = self.mx
        glyphs, ansi = self.map_device(frame)
        r = self.rasterizer
        rows, cols = frame.shape[:2]
        output, = self.raster_kernel(
            inputs=[glyphs, ansi, self.masks, self.palette,
                    mx.array([cols, rows, r.cell_width, r.cell_height, r.width, r.height], dtype=mx.int32)],
            grid=(r.width*r.height//4, 1, 1), threadgroup=(256, 1, 1),
            output_shapes=[(r.width*r.height*3//2,)], output_dtypes=[mx.uint8], stream=mx.gpu)
        mx.eval(output)
        return np.array(output).tobytes()

    render_frame = render_nv12
