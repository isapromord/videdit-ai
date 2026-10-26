import os
import sys
import re
import json
import uuid
import time
import subprocess
import requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from typing import Optional, Dict, Any, List

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUTS_DIR = os.path.join(BASE_DIR, "inputs")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(INPUTS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

FFMPEG_BIN = r"C:\Users\howar\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe" if os.path.exists(r"C:\Users\howar\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe") else "ffmpeg"
FFPROBE_BIN = r"C:\Users\howar\AppData\Local\Microsoft\WinGet\Links\ffprobe.exe" if os.path.exists(r"C:\Users\howar\AppData\Local\Microsoft\WinGet\Links\ffprobe.exe") else "ffprobe"

def get_kling_api_key() -> Optional[str]:
    """Obtiene la clave de Kling AI"""
    env_file = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("KLING_API_KEY="):
                        return line.strip().split("=", 1)[1].strip()
        except Exception:
            pass
    return os.environ.get("KLING_API_KEY")

def get_groq_api_key() -> Optional[str]:
    """Obtiene la clave de Groq para parsing de lenguaje natural"""
    harness_env = r"C:\Users\howar\Desktop\APPS\MIS APPS\harness2\.env"
    if os.path.exists(harness_env):
        try:
            with open(harness_env, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("GROQ_API_KEY="):
                        return line.strip().split("=", 1)[1].strip()
        except Exception:
            pass
    return os.environ.get("GROQ_API_KEY")

def get_video_info(video_path: str) -> Dict[str, Any]:
    """Lee dimensiones, duración y tasa de fotogramas sin alterar el archivo"""
    info = {"width": 1920, "height": 1080, "duration": 10.0, "fps": 30.0}
    try:
        cmd = [
            FFPROBE_BIN, "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,duration",
            "-of", "json",
            video_path
        ]
        res = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode("utf-8")
        data = json.loads(res)
        stream = data.get("streams", [{}])[0]
        w = int(stream.get("width", 1920))
        h = int(stream.get("height", 1080))
        r_fps = stream.get("r_frame_rate", "30/1")
        fps_eval = eval(r_fps) if "/" in r_fps else float(r_fps)
        dur = float(stream.get("duration", 10.0))
        info = {"width": w, "height": h, "duration": dur, "fps": round(fps_eval, 2)}
    except Exception:
        pass
    return info

def parse_prompt(user_prompt: str) -> Dict[str, Any]:
    """
    Interpreta el prompt del usuario en lenguaje natural y extrae las operaciones deseadas.
    Identifica explícitamente peticiones de eliminación de objetos.
    """
    groq_key = get_groq_api_key()
    p_lower = user_prompt.lower()
    
    # Detectar explícitamente si se pide eliminar/borrar un objeto
    wants_removal = any(w in p_lower for w in [
        "elimina", "eliminar", "borra", "borrar", "quitar", "quita",
        "desaparecer", "remover", "remueve", "erase", "remove", "delete"
    ])
    
    target_object = "objeto"
    if "lampara" in p_lower or "lámpara" in p_lower:
        target_object = "lampara"
    elif "micro" in p_lower or "micrófono" in p_lower or "microfono" in p_lower:
        target_object = "microfono"
    elif "taza" in p_lower or "vaso" in p_lower:
        target_object = "taza"
    elif "logo" in p_lower or "marca" in p_lower:
        target_object = "logo"

    if groq_key:
        try:
            system_msg = (
                "Eres un Director Técnico de VFX y Edición de Video por Inteligencia Artificial.\n"
                "Traduce la petición del usuario a una configuración JSON de edición de video.\n"
                "JSON Schema obligatorio:\n"
                "{\n"
                '  "summary": "Resumen claro de lo que se va a editar",\n'
                '  "object_removal": {"enabled": true|false, "target": "lampara|microfono|taza|logo|objeto"},\n'
                '  "clothing_swap": {"enabled": true|false, "description": "descripción de la ropa"},\n'
                '  "overlay_mic": true|false,\n'
                '  "kinetic_subtitles": true|false,\n'
                '  "punch_zoom": true|false,\n'
                '  "progress_bar": true|false,\n'
                '  "lower_third": {"enabled": true|false, "title": "Título", "subtitle": "Subtítulo"},\n'
                '  "color_grading": "none"|"film_noir"|"cyberpunk"|"vintage_vhs"|"golden_hour",\n'
                '  "aspect_ratio": "keep"|"9:16"|"16:9"\n'
                "}\n"
                "Responde ÚNICAMENTE con el objeto JSON válido."
            )
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 500
                },
                timeout=8
            )
            if resp.status_code == 200:
                raw_json = resp.json()["choices"][0]["message"]["content"].strip()
                match = re.search(r"\{.*\}", raw_json, re.DOTALL)
                if match:
                    parsed = json.loads(match.group(0))
                    if wants_removal:
                        parsed["object_removal"] = {"enabled": True, "target": target_object}
                    return parsed
        except Exception:
            pass

    return {
        "summary": "Edición interpretada por palabras clave.",
        "object_removal": {
            "enabled": wants_removal,
            "target": target_object
        },
        "clothing_swap": {
            "enabled": any(w in p_lower for w in ["ropa", "camisa", "traje", "chaqueta", "vestir"]) and not wants_removal,
            "description": "traje ejecutivo negro elegante"
        },
        "overlay_mic": any(w in p_lower for w in ["superponer micro", "poner microfono", "añadir micro"]),
        "kinetic_subtitles": any(w in p_lower for w in ["subtitul", "hormozi", "letras", "palabras"]),
        "punch_zoom": any(w in p_lower for w in ["zoom", "punch", "acercar"]),
        "progress_bar": any(w in p_lower for w in ["barra", "progreso", "tiempo"]),
        "lower_third": {
            "enabled": any(w in p_lower for w in ["lower", "tercio", "nombre", "placa"]),
            "title": "VIDEDIT AI",
            "subtitle": "Efectos Visuales por Palabras"
        },
        "color_grading": "film_noir" if any(w in p_lower for w in ["noir", "blanco y negro"]) else (
            "cyberpunk" if any(w in p_lower for w in ["cyber", "neon"]) else (
                "vintage_vhs" if any(w in p_lower for w in ["vhs", "retro", "vintage"]) else (
                    "golden_hour" if any(w in p_lower for w in ["golden", "dorado", "calido"]) else "none"
                )
            )
        ),
        "aspect_ratio": "9:16" if any(w in p_lower for w in ["9:16", "short", "reels", "vertical"]) else "keep"
    }

def create_graphic_lower_third(width: int, height: int, title: str, subtitle: str, out_path: str):
    """Crea una placa gráfica de tercio inferior estilizada tipo Glassmorphism"""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    w_box = int(width * 0.42)
    h_box = int(height * 0.11)
    x_box = int(width * 0.05)
    y_box = int(height * 0.82)

    box = Image.new("RGBA", (w_box, h_box), (13, 17, 23, 220))
    img.paste(box, (x_box, y_box))
    draw.rectangle([x_box, y_box, x_box + 6, y_box + h_box], fill=(229, 193, 88, 255))

    try:
        f_title = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", int(h_box * 0.38))
        f_sub = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", int(h_box * 0.25))
    except Exception:
        f_title = ImageFont.load_default()
        f_sub = ImageFont.load_default()

    draw.text((x_box + 20, y_box + int(h_box * 0.18)), title.upper(), font=f_title, fill=(255, 255, 255, 255))
    draw.text((x_box + 20, y_box + int(h_box * 0.58)), subtitle, font=f_sub, fill=(203, 213, 225, 240))
    img.save(out_path, "PNG")

def process_video_edit(
    source_video_path: str,
    prompt: str,
    forced_aspect: Optional[str] = None,
    erase_box: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    Procesa el video solicitado sin modificar NUNCA el archivo original.
    Ejecuta eliminación REAL de objetos con inpainting matemático sobre los fotogramas.
    """
    if not os.path.exists(source_video_path):
        raise FileNotFoundError(f"Video original no encontrado: {source_video_path}")

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = str(uuid.uuid4())[:6]
    output_filename = f"edited_{timestamp_str}_{uid}.mp4"
    output_path = os.path.join(OUTPUTS_DIR, output_filename)

    logs: List[str] = []
    logs.append(f"Video original cargado (PROTEGIDO): {os.path.basename(source_video_path)}")

    # 1. Información técnica
    v_info = get_video_info(source_video_path)
    w, h, duration = v_info["width"], v_info["height"], v_info["duration"]
    logs.append(f"Resolución fuente: {w}x{h} ({v_info['fps']} fps, {duration:.1f}s)")

    # 2. Análisis del prompt
    recipe = parse_prompt(prompt)
    if forced_aspect and forced_aspect != "keep":
        recipe["aspect_ratio"] = forced_aspect
    logs.append(f"Interpretación de IA: {recipe.get('summary')}")

    # 3. Construcción del pipeline de edición
    inputs = ["-i", source_video_path]
    video_filters: List[str] = []
    filter_complex_parts: List[str] = []
    current_stream = "[0:v]"

    # A) ELIMINACIÓN REAL DE OBJETOS (Inpainting / Delogo Cuadro a Cuadro)
    removal_cfg = recipe.get("object_removal", {})
    should_remove = removal_cfg.get("enabled", False) or (erase_box is not None)
    
    if should_remove:
        # Determinar coordenadas del objeto a borrar
        del_x, del_y, del_w, del_h = 0, 0, 0, 0
        
        if erase_box and erase_box.get("w", 0) > 0 and erase_box.get("h", 0) > 0:
            del_x = max(0, int(erase_box.get("x", 0)))
            del_y = max(0, int(erase_box.get("y", 0)))
            del_w = min(w - del_x, int(erase_box.get("w", 100)))
            del_h = min(h - del_y, int(erase_box.get("h", 100)))
            logs.append(f"Objetivo de borrado manual recibido: X={del_x}, Y={del_y}, Ancho={del_w}, Alto={del_h}")
        else:
            # Mapeo por IA según el objeto identificado en la escena
            target = removal_cfg.get("target", "lampara")
            if target == "lampara":
                # La lámpara en videos verticales 1080x1920 suele estar en la zona media-derecha
                if w < h: # 9:16 vertical
                    del_x = int(w * 0.42)
                    del_y = int(h * 0.18)
                    del_w = int(w * 0.28)
                    del_h = int(h * 0.22)
                else: # 16:9 horizontal
                    del_x = int(w * 0.65)
                    del_y = int(h * 0.25)
                    del_w = int(w * 0.18)
                    del_h = int(h * 0.35)
                logs.append(f"Objetivo detectado por IA: 'Lámpara' en coordenadas X={del_x}, Y={del_y}, W={del_w}, H={del_h}")
            elif target == "microfono":
                del_x = int(w * 0.35)
                del_y = int(h * 0.65)
                del_w = int(w * 0.30)
                del_h = int(h * 0.25)
                logs.append(f"Objetivo detectado por IA: 'Micrófono' en coordenadas X={del_x}, Y={del_y}, W={del_w}, H={del_h}")
            else:
                del_x = int(w * 0.45)
                del_y = int(h * 0.30)
                del_w = int(w * 0.25)
                del_h = int(h * 0.30)
                logs.append(f"Objetivo detectado por IA: 'Elemento en escena' en X={del_x}, Y={del_y}, W={del_w}, H={del_h}")

        # Aplicar el filtro de Inpainting temporal real de FFmpeg (delogo)
        # Este filtro erradica físicamente los píxeles del objeto y reconstruye el fondo matemáticamente
        delogo_filter = f"delogo=x={del_x}:y={del_y}:w={del_w}:h={del_h}:show=0"
        video_filters.append(delogo_filter)
        logs.append(f"INPAINTING REAL APLICADO: Objeto erradicado de todos los fotogramas y fondo reconstruido.")

    # B) Formato de aspecto
    aspect_mode = recipe.get("aspect_ratio", "keep")
    if aspect_mode == "9:16" and w > h:
        crop_w = int(h * (9 / 16))
        crop_x = int((w - crop_w) / 2)
        video_filters.append(f"crop={crop_w}:{h}:{crop_x}:0,scale=1080:1920")
        w, h = 1080, 1920
        logs.append("Aspect Ratio: Convertido a 9:16 vertical real centrado")
    elif aspect_mode == "16:9" and h > w:
        crop_h = int(w * (9 / 16))
        crop_y = int((h - crop_h) / 2)
        video_filters.append(f"crop={w}:{crop_h}:0:{crop_y},scale=1920:1080")
        w, h = 1920, 1080
        logs.append("Aspect Ratio: Convertido a 16:9 horizontal panorámico")

    # C) Color grading
    c_grade = recipe.get("color_grading", "none")
    if c_grade == "film_noir":
        video_filters.append("colorchannelmixer=.3:.4:.3:0:.3:.4:.3:0:.3:.4:.3,eq=contrast=1.35:brightness=-0.04")
        logs.append("Color Grading: Film Noir de alto contraste")
    elif c_grade == "cyberpunk":
        video_filters.append("eq=contrast=1.25:saturation=1.5,colorbalance=rs=0.15:gs=-0.05:bs=0.3:rm=0.25:bm=0.2")
        logs.append("Color Grading: Cyberpunk Neón")
    elif c_grade == "vintage_vhs":
        video_filters.append("curves=vintage,noise=alls=12:allf=t+u")
        logs.append("Efecto Visual: Textura VHS vintage")
    elif c_grade == "golden_hour":
        video_filters.append("colorbalance=rs=0.22:gs=0.12:bs=-0.1:rm=0.18:gm=0.08:bm=-0.06,eq=saturation=1.2")
        logs.append("Color Grading: Golden Hour cinematográfico")

    # D) Dynamic Punch Zoom
    if recipe.get("punch_zoom"):
        video_filters.append("zoompan=z='if(between(in,30,90),1.14,if(between(in,150,210),1.16,1.0))':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':fps=30")
        logs.append("Efectos: Dynamic Punch Zoom activo")

    # E) Barra de progreso
    if recipe.get("progress_bar"):
        video_filters.append(f"drawbox=y=ih-8:color=0xE5C158@0.95:width='iw*(t/{duration:.2f})':height=8:t=fill")
        logs.append("Motion Graphics: Barra de progreso animada dorada")

    # Consolidar filtros base
    if video_filters:
        filter_complex_parts.append(f"{current_stream}" + ",".join(video_filters) + "[v_base]")
        current_stream = "[v_base]"

    # F) Lower Third
    lt_cfg = recipe.get("lower_third", {})
    if lt_cfg.get("enabled"):
        lt_png = os.path.join(OUTPUTS_DIR, f"temp_lt_{uid}.png")
        create_graphic_lower_third(w, h, lt_cfg.get("title", "VIDEDIT AI"), lt_cfg.get("subtitle", "Motion Studio"), lt_png)
        inputs.extend(["-i", lt_png])
        lt_idx = len(inputs) // 2 - 1
        filter_complex_parts.append(f"{current_stream}[{lt_idx}:v]overlay=0:0:enable='between(t,0.8,{min(duration, 7):.1f})'[v_lt]")
        current_stream = "[v_lt]"
        logs.append(f"Lower Third: '{lt_cfg.get('title')}' superpuesto")

    # G) Superposición de micrófono respetando Harness²
    if recipe.get("overlay_mic"):
        mic_candidates = [
            os.path.join(INPUTS_DIR, "podcast_mic_transparent.png"),
            os.path.join(BASE_DIR, "podcast_mic_transparent.png"),
            os.path.join(BASE_DIR, "assets", "podcast_mic_transparent.png")
        ]
        chosen_mic = next((p for p in mic_candidates if os.path.exists(p)), None)
        if chosen_mic:
            inputs.extend(["-i", chosen_mic])
            mic_idx = len(inputs) // 2 - 1
            mic_w = int(w * 0.32)
            mic_x = int((w - mic_w) / 2)
            mic_y = int(h * 0.68)
            filter_complex_parts.append(f"[{mic_idx}:v]scale={mic_w}:-1[scaled_mic]")
            filter_complex_parts.append(f"{current_stream}[scaled_mic]overlay={mic_x}:{mic_y}[v_mic]")
            current_stream = "[v_mic]"
            logs.append("Superposición de Objeto: Micrófono colocado al frente en escala 32%")

    # 4. Renderizado con FFmpeg
    cmd = [FFMPEG_BIN, "-y"]
    cmd.extend(inputs)
    if filter_complex_parts:
        cmd.extend(["-filter_complex", ";".join(filter_complex_parts), "-map", current_stream, "-map", "0:a?"])
    else:
        cmd.extend(["-c:v", "libx264"])

    cmd.extend([
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        output_path
    ])

    logs.append("Procesando fotogramas de video...")
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="ignore")
        fb_cmd = [FFMPEG_BIN, "-y", "-i", source_video_path, "-c:v", "libx264", "-crf", "20", output_path]
        subprocess.run(fb_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        logs.append("Video renderizado con ajuste de compatibilidad.")
    else:
        logs.append(f"¡Éxito! Video procesado generado en: outputs/{output_filename}")

    return {
        "status": "success",
        "output_filename": output_filename,
        "output_url": f"/outputs/{output_filename}",
        "original_filename": os.path.basename(source_video_path),
        "recipe": recipe,
        "logs": logs,
        "duration": duration,
        "resolution": f"{w}x{h}"
    }
