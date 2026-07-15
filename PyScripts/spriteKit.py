#!/usr/bin/env python3
"""
SpriteVideo & Memory Safe:
    Script minimalista para convertir un sprite sheet (1 sola fila de frames) en un video MP4
    centrado sobre un fondo negro en la resolución que elijas.
Crea un entorno:
    python -m venv venv
Despues inicialo:
    source venv/bin/activate
Instalación de imports (arch dentro de un entorno [venv]):
    python -m pip install imageio imageio-ffmpeg pillow numpy
Despues ejecuta el archivo:
    python spriteKit.py
"""

import imageio.v3 as iio
from PIL import Image, ImageColor
from pathlib import Path
import numpy as np
import os
import readline
import glob

# Completador de rutas
def path_completer(text, state):
    text = os.path.expanduser(text)
    matches = glob.glob(text + '*')
    return [m + '/' if os.path.isdir(m) else m for m in matches][state]

readline.set_completer_delims(' \t\n;')
readline.parse_and_bind("tab: complete")
readline.set_completer(path_completer)

# Resolucion de videos
PRESETS = {
    "1":    (1280, 720),
    "2":    (1920, 1080),
    "3":    (2560, 1440),
    "4":    (3840, 2160),
}

# Metodos para el menu
class SpriteUI:
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

    @staticmethod
    def ask_position():
        print(f"\n: -- Posición del Sprite (Numpad) -- :")
        print("[1] Top-L  [2] Top-C  [3] Top-R")
        print("[4] Mid-L  [5] Center [6] Mid-R")
        print("[7] Bot-L  [8] Bot-C  [9] Bot-R")
        pos = input("Selecciona posición [5]: ").strip() or "5"
        return pos

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

    @staticmethod
    def ask_time(title="Duración del Video", default=0.0):
        print(f"\n: -- {title} -- :")
        print("[s] Segundos | [m] Minutos | [h] Horas")
        choice = input("Selecciona unidad [s]: ").strip().lower() or 's'

        val = SpriteUI.ask_float("Cantidad", min_val=0.0, default=default)

        if choice == 'm': return val * 60
        if choice == 'h': return val * 3600
        return val

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

# Manejo del SpriteSheet
class SpriteEngine:
    def __init__(self, sheet_path: Path, canvas_px: int):
        self.sheet = Image.open(sheet_path).convert("RGBA")
        self.canvas_px = canvas_px
        self.total_frames = self.sheet.width // canvas_px
        # Guarda un frame limpio del fondo para reutilizarlo en los delays.
        self.clean_frame = None

    def get_base_processed(self, start, end, out_size, scale, bg_color, pos_key="5", existing_frames=None):
        W, H = out_size

        # Extraer frames seleccionados
        new_sprite_frames = []
        for i in range(start - 1, end):
            x = i * self.canvas_px
            box = (x, 0, x + self.canvas_px, self.sheet.height)
            fr = self.sheet.crop(box)
            if scale != 1.0:
                new_size = (int(fr.width * scale), int(fr.height * scale))
                fr = fr.resize(new_size, Image.NEAREST)
            new_sprite_frames.append(fr.convert("RGBA"))

        # Sincronizar longitudes
        num_new = len(new_sprite_frames)
        num_old = len(existing_frames) if existing_frames else 0
        total_len = max(num_new, num_old)

        final_frames = []

        for i in range(total_len):
            # Capa base (escena existente o fondo vacio)
            if existing_frames:
                # Si el anterior spritesheet tiene menos frames se congela
                idx_old = min(i, num_old - 1)
                canvas = Image.fromarray(existing_frames[idx_old]).convert("RGBA")
            else:
                canvas = Image.new("RGBA", (W, H), bg_color)
                if self.clean_frame is None:
                    self.clean_frame = np.array(canvas.convert("RGB"))

            # Nueva capa del spritesheet actual
            idx_new = min(i, num_new - 1)
            fr = new_sprite_frames[idx_new]

            # Ubicacion de los sprites
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

            canvas.alpha_composite(fr, pos)
            final_frames.append(np.array(canvas.convert("RGB")))

        return final_frames

# Proceso de renderización
class VideoRenderer:
    @staticmethod
    def render(out_name, base_frames, clean_frame, duration_s, loop, fps, intro_delay=0.0, outro_delay=0.0, keep_first=True, keep_last=True):
        num_base = len(base_frames)

        # Convertir segundos a cantidad de frames
        intro_frames = int(intro_delay * fps)
        outro_frames = int(outro_delay * fps)

        # Si hay loop, la duración la determina el tiempo solicitado.
        # Si no hay loop, solo se reproduce una vuelta completa de los frames seleccionados.
        if loop:
            animation_frames = int(duration_s * fps)
        else:
            animation_frames = num_base

        total_video_frames = intro_frames + animation_frames + outro_frames

        def frame_generator():
            rendered_frames = 0

            def print_progress():
                # Mostrar el progreso cada 50 frames para evitar llamar a print() en cada iteración.
                if rendered_frames % 50 == 0 or rendered_frames == total_video_frames:
                    print(f"\r- Enviando a GPU: {rendered_frames}/{total_video_frames} frames", end="", flush=True)

            # Delay de entrada
            intro_image = base_frames[0] if keep_first else clean_frame
            for _ in range(intro_frames):
                rendered_frames += 1
                print_progress()
                yield intro_image

            # Animación Principal
            for i in range(animation_frames):
                rendered_frames += 1
                idx = i % num_base if loop else min(i, num_base - 1)
                animation_image = base_frames[idx]
                print_progress()
                yield animation_image

            # Delay de salida
            outro_image = base_frames[-1] if keep_last else clean_frame
            for _ in range(outro_frames):
                rendered_frames += 1
                print_progress()
                yield outro_image

        print(f"- Renderizando {total_video_frames} frames a {fps:.3f} FPS...")

        try:
            iio.imwrite(out_name, frame_generator(), fps=fps, extension=".mp4",
                        codec="h264_nvenc", pixelformat="yuv420p", is_batch=True)
        except Exception as e:
            print(f"\n! NVENC falló, usando CPU: {e}")
            iio.imwrite(out_name, frame_generator(), fps=fps, extension=".mp4",
                        codec="libx264", pixelformat="yuv420p", is_batch=True)

# Menu
def main():
    ui = SpriteUI()
    mode = ui.ask_mode()
    if not mode: return

    base_frames = None
    res_video = None
    bg_color = None
    final_engine = None
    output_path = None

    # Agregar uno o varios spritesheets a la escena
    while True:
        path, engine = ui.ask_path("Ruta del sprite: ")
        if not engine: break

        if output_path is None: output_path = path
        final_engine = engine
        if mode == "2":
            frame_idx = ui.ask_int(f"\nNumero de frame para la miniatura :",
                               default=1, max_val=engine.total_frames)
            start = end = frame_idx
        else:
            start = ui.ask_int("Frame inicial", default=1, max_val=engine.total_frames)
            end = ui.ask_int("Frame final", default=engine.total_frames, max_val=engine.total_frames)

        scale = ui.ask_float("Escala", default=1.0)
        pos_key = ui.ask_position()

        if res_video is None:
            res_video = ui.ask_video_setup()
            bg_color = ui.ask_background()
        # Cacheó de la semilla
        print("- Procesando...")
        base_frames = engine.get_base_processed(start, end, res_video, scale, bg_color, pos_key, existing_frames=base_frames)

        more = input("\n¿Deseas agregar otro sprite a la misma escena? [s/N]: ").lower()
        if more != 's':
            break

    # Salida
    if mode == "2":
        # Formato de imagen
        out_file=output_path.parent / f"{output_path.stem}_img.png"
        Image.fromarray(base_frames[0]).save(out_file)
        print(f"\n Imagen Creada :) {out_file.name}")
    else:
        # Formato de Video
        # Definir animación principal
        duration_s = ui.ask_time("Duración de la Animación (sin contar delays)", default=4.0)

        print(f"\n: -- Velocidad de Animación -- :")
        custom_speed = input("¿Definir la duración de una vuelta del sprite? [s/N]: ").lower() == 's'
        anim_time = ui.ask_float("Segundos por vuelta", default=1.0) if custom_speed else duration_s
        loop = input("¿Activar Bucle (Loop)? [s/N]: ").lower() == 's'

        # Definir Delays (Intro / Outro)
        intro_delay = ui.ask_time("Delay Inicial", default=0.0)
        outro_delay = ui.ask_time("Delay Final", default=0.0)

        # Determinar qué mostrar durante los delays
        keep_first = True
        keep_last = True

        if intro_delay > 0.0:
            keep_first = input("¿Mostrar el primer sprite durante el delay inicial? [s/N]: ").lower() != 'n'

        if outro_delay > 0.0:
            keep_last = input("¿Dejar el último sprite durante el delay final? [s/N]: ").lower() != 'n'

        final_fps = max(0.1, len(base_frames) / anim_time)
        out_file = output_path.with_suffix(".mp4")

        VideoRenderer.render(
            out_name=out_file,
            base_frames=base_frames,
            clean_frame=final_engine.clean_frame,
            duration_s=duration_s,
            loop=loop,
            fps=final_fps,
            intro_delay=intro_delay,
            outro_delay=outro_delay,
            keep_first=keep_first,
            keep_last=keep_last
        )
        print(f"\n- Video Creado :) {out_file.name}")

if __name__ == "__main__":
    main()
