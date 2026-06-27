#!/usr/bin/env python3
"""
SpriteVideo & Memory Safe:
    Script minimalista para convertir un sprite sheet (1 sola fila de frames) en un video MP4
    centrado sobre un fondo negro en la resolución que elijas.
Instalación de imports (arch dentro de un entorno [venv]):
    python -m pip install imageio imageio-ffmpeg pillow numpy
"""

import imageio.v3 as iio
from PIL import Image, ImageColor
from pathlib import Path
import numpy as np
import os
import readline
import glob

def path_completer(text, state):
    text = os.path.expanduser(text)
    matches = glob.glob(text + '*')
    return [m + '/' if os.path.isdir(m) else m for m in matches][state]

readline.set_completer_delims(' \t\n;')
readline.parse_and_bind("tab: complete")
readline.set_completer(path_completer)

PRESETS = {
    "1":    (1280, 720),
    "2":    (1920, 1080),
    "3":    (2560, 1440),
    "4":    (3840, 2160),
}

class SpriteUI:
# Menu principal
    @staticmethod
    def ask_mode():
        print(f"\n: -- SpriteSheet Toolkit -- :")
        print("\n¿Qué realizarás? [1]:")
        print("1) Video")
        print("2) Imagen")
        print("q) salir")
        mode = input("> ").strip().lower() or "1"

        if mode == 'q':
            print("Saliendo...")
            return None
        return mode
# pregunta de la ruta de la imagen
    @staticmethod
    def ask_path(prompt: str):
        while True:
            user_input = input(prompt).strip().strip('"')
            if not user_input: return None, None
            p = Path(user_input).expanduser()
            if p.exists():
                canvas_px = SpriteUI.ask_int("Tamaño del lienzo (px)", default=64)
                engine = SpriteEngine(p, canvas_px)
                print(f"Número total de frames: 1 - {engine.total_frames}")
                return p, engine
            print(f"No encontré el archivo en {p}")
# pregunta para valores enteros
    @staticmethod
    def ask_int(prompt: str, min_val=1, max_val=None, default=None):
        while True:
            txt = input(f"{prompt} [{default}]: ").strip()
            if not txt and default is not None: return default
            try:
                v = int(txt)
                if (min_val and v < min_val) or (max_val and v > max_val): continue
                return v
            except ValueError: print("Ingresa un número entero.")
# pregunta para valores decimales
    @staticmethod
    def ask_float(prompt: str, min_val=None, default=None):
        while True:
            txt = input(f"{prompt} [{default}]: ").strip()
            if not txt and default is not None: return default
            try:
                v = float(txt)
                if min_val is not None and v < min_val: continue
                return v
            except ValueError: print("Ingresa un número decimal.")
# pregunta la posición del sprite
    @staticmethod
    def ask_position():
        print(f"\n: -- Posición del Sprite (Numpad) -- :")
        print("[1] Top-L  [2] Top-C  [3] Top-R")
        print("[4] Mid-L  [5] Center [6] Mid-R")
        print("[7] Bot-L  [8] Bot-C  [9] Bot-R")
        pos = input("Selecciona posición [5]: ").strip() or "5"
        return pos
# pregunta para el fondo
    @staticmethod
    def ask_background():
        hex_val = input("Color de fondo HEX (6 valores, ej: FF5733 #FF5733, FFF, #FFF) [000000]: ").strip().replace("#", "")
        if not hex_val: return (0, 0, 0, 255)

        if not hex_val.startswith("#"):
            hex_val = f"#{hex_val}"

        try:
            rgb = ImageColor.getrgb(hex_val)
            return (*rgb, 255)
        except:
            print(f"Formato '{hex_val}' inválido. Usando el color #000000")
            return (0, 0, 0, 255)
# pregunta para cualquier duración
    @staticmethod
    def ask_time_format():
        print(f"\n: -- Duración del Video -- :")
        print("[s] Segundos | [m] Minutos | [h] Horas")
        choice = input("Selecciona unidad [s]: ").strip().lower() or 's'

        val = SpriteUI.ask_float("Cantidad", default=4.0)

        if choice == 'm': return val * 60
        if choice == 'h': return val * 3600
        return val
# pregunta para la orientacion (canvas) del video
    @staticmethod
    def ask_video_setup():
        ori = input("Orientación del video [v (Vertical) / H (Horizontal)]: ").lower()
        print("\nCalidad:\n1) 720\n2) 1080\n3) 2k\n4) 4k\nc) Custom")
        choice = input("Selecciona [2]: ").strip().lower() or '2'

        if choice == 'c':
            w = SpriteUI.ask_int("Ancho (px)", default=1920)
            h = SpriteUI.ask_int("Alto (px)", default=1080)
            return (w, h)
        base_res = PRESETS.get(choice, (1920, 1080))
        if ori == 'v':
            return (base_res[1], base_res[0])
        return base_res
# proceso del sprite
class SpriteEngine:
    def __init__(self, sheet_path: Path, canvas_px: int):
        self.sheet = Image.open(sheet_path).convert("RGBA")
        self.canvas_px = canvas_px
        self.total_frames = self.sheet.width // canvas_px
        self.clean_frame = None

    def get_base_processed(self, start, end, out_size, scale, bg_color, pos_key="5", existing_frames=None):
        W, H = out_size

        # 1. Extraemos los frames seleccionados
        new_sprite_frames = []
        for i in range(start - 1, end):
            x = i * self.canvas_px
            box = (x, 0, x + self.canvas_px, self.sheet.height)
            fr = self.sheet.crop(box)
            if scale != 1.0:
                new_size = (int(fr.width * scale), int(fr.height * scale))
                fr = fr.resize(new_size, Image.NEAREST)
            new_sprite_frames.append(fr.convert("RGBA"))

        # 2. Sincronizamos longitudes
        num_new = len(new_sprite_frames)
        num_old = len(existing_frames) if existing_frames else 0
        total_len = max(num_new, num_old)

        final_frames = []

        for i in range(total_len):
            # Capa base
            if existing_frames:
                # Si el anterior era más corto, lo congelamos en su último frame
                idx_old = min(i, num_old - 1)
                canvas = Image.fromarray(existing_frames[idx_old]).convert("RGBA")
            else:
                canvas = Image.new("RGBA", (W, H), bg_color)
                if self.clean_frame is None:
                    self.clean_frame = np.array(canvas.convert("RGB"))

            # Capa nueva (el sprite actual)
            # USAMOS min() EN LUGAR DE % PARA NO FORZAR EL LOOP
            idx_new = min(i, num_new - 1)
            fr = new_sprite_frames[idx_new]

            # --- Cálculo de posición ---
            sw, sh = fr.size
            cw, ch = W // 3, H // 3
            c_x = [cw // 2, cw + cw // 2, 2 * cw + cw // 2]
            c_y = [ch // 2, ch + ch // 2, 2 * ch + ch // 2]
            positions = {
                "1": (c_x[0]-sw//2, c_y[0]-sh//2), "2": (c_x[1]-sw//2, c_y[0]-sh//2), "3": (c_x[2]-sw//2, c_y[0]-sh//2),
                "4": (c_x[0]-sw//2, c_y[1]-sh//2), "5": (c_x[1]-sw//2, c_y[1]-sh//2), "6": (c_x[2]-sw//2, c_y[1]-sh//2),
                "7": (c_x[0]-sw//2, c_y[2]-sh//2), "8": (c_x[1]-sw//2, c_y[2]-sh//2), "9": (c_x[2]-sw//2, c_y[2]-sh//2),
            }
            pos = positions.get(pos_key, positions["5"])

            # Composición
            canvas.alpha_composite(fr, pos)
            final_frames.append(np.array(canvas.convert("RGB")))

        return final_frames
# proceso de renderizacion
class VideoRenderer:
    @staticmethod
    def render(out_name, base_frames, clean_frame, duration_s, is_loop, fps, keep_last):
        # Streaming: Enviamos los frames uno a uno usando un generador.
        num_base = len(base_frames)
        # Se calcula los frames totales que tendrá el video final
        total_video_frames = int(duration_s * fps)

        def frame_generator():
            for i in range(total_video_frames):
                # Lógica de Loop o Frame Final (Padding)
                if is_loop:
                    idx = i % num_base
                    img = base_frames[idx]
                else:
                    # Si no es loop, mostramos la animación una vez y luego congelamos el último
                    if i < num_base:
                        img = base_frames[i]
                    else:
                        img = base_frames[-1] if keep_last else clean_frame

                if (i + 1) % 50 == 0 or (i + 1) == total_video_frames:
                    print(f"\r- Enviando a GPU: {i+1}/{total_video_frames} frames", end="", flush=True)
                yield img

        print(f"- Renderizando {total_video_frames} frames a {fps:.3f} FPS...")

        try:
            iio.imwrite(out_name, frame_generator(), fps=fps, extension=".mp4",
                        codec="h264_nvenc", pixelformat="yuv420p", is_batch=True)
        except Exception as e:
            print(f"\n! NVENC falló, usando CPU: {e}")
            iio.imwrite(out_name, frame_generator(), fps=fps, extension=".mp4",
                        codec="libx264", pixelformat="yuv420p", is_batch=True)

def main():
    ui = SpriteUI()
    # Menú Principal
    mode = ui.ask_mode()
    if not mode: return

    base_frames = None
    res_video = None
    bg_color = None
    final_engine = None
    output_path = None

    while True:
        # Ruta y motor del sprite
        path, engine = ui.ask_path("Ruta del sprite: ")
        if not engine: break

        if output_path is None: output_path = path
        final_engine = engine
        # Seleccion de frame
        if mode == "2":
            frame_idx = ui.ask_int(f"\nNumero de frame para la miniatura :",
                               default=1, max_val=engine.total_frames)
            start = end = frame_idx
        else:
            start = ui.ask_int("Frame inicial", default=1, max_val=engine.total_frames)
            end = ui.ask_int("Frame final", default=engine.total_frames, max_val=engine.total_frames)

        # Escala, posicion, orientacion y color de fondo
        scale = ui.ask_float("Escala", default=1.0)
        pos_key = ui.ask_position()

        if res_video is None:
            res_video = ui.ask_video_setup()
            bg_color = ui.ask_background()
        # Cacheo de la semilla
        print("- Procesando...")
        base_frames = engine.get_base_processed(start, end, res_video, scale, bg_color, pos_key, existing_frames=base_frames)

        more = input("\n¿Deseas agregar otro sprite a la misma escena? [s/N]: ").lower()
        if more != 's':
            break

    # Salida
    if mode == "2":
        out_file=output_path.parent / f"{output_path.stem}_img.png"
        Image.fromarray(base_frames[0]).save(out_file)
        print(f"\n Imagen Creada :) {out_file.name}")
    else:
        # Tiempos de la animación
        duration_s = ui.ask_time_format()
        print(f"\n: -- Velocidad de Animación -- :")
        manual = input("¿Velocidad manual para el sprite? [s/N]: ").lower() == 's'
        anim_time = ui.ask_float("Segundos por vuelta", default=1.0) if manual else duration_s
        loop = input("¿Activar Bucle (Loop)? [s/N]: ").lower() == 's'
        # Ultimo frame
        keep_last = True
        if not loop and anim_time < duration_s:
            keep_last = input("¿Dejar el último sprite al terminar la animación? [s/N]: ").lower() != 'n'
        # Calculo de los FPS reales para que la animación dure lo que se pidio
        final_fps = max(0.1, len(base_frames) / anim_time)
        # Renderizamos (Streaming)
        out_file = output_path.with_suffix(".mp4")
        VideoRenderer.render(out_file, base_frames, final_engine.clean_frame, duration_s, loop, final_fps, keep_last)
        print(f"\n- Video Creado :) {out_file.name}")

if __name__ == "__main__":
    main()
