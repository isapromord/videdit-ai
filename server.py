import os
import sys
import shutil
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import ai_editor_engine

app = FastAPI(title="VIDEDIT AI - Standalone AI Video VFX & Prompt Studio")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUTS_DIR = os.path.join(BASE_DIR, "inputs")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/inputs", StaticFiles(directory=INPUTS_DIR), name="inputs")
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")

class EditRequest(BaseModel):
    video_filename: str
    prompt: str
    aspect_ratio: Optional[str] = "keep"
    erase_box: Optional[dict] = None

@app.get("/")
def get_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "VIDEDIT AI Server running. Static index.html not found."}

@app.get("/api/videos")
def list_available_videos():
    """Lista todos los videos disponibles para editar (todos se tratan como lectura-protegida)"""
    videos = []
    # 1. Videos en inputs/
    if os.path.exists(INPUTS_DIR):
        for f in os.listdir(INPUTS_DIR):
            if f.lower().endswith((".mp4", ".mov", ".mkv", ".webm")):
                fpath = os.path.join(INPUTS_DIR, f)
                size_mb = round(os.path.getsize(fpath) / (1024 * 1024), 2)
                videos.append({
                    "name": f,
                    "location": "inputs",
                    "path": fpath,
                    "url": f"/inputs/{f}",
                    "size_mb": size_mb
                })
    # 2. Videos en la raíz de VIDEDIT
    for f in os.listdir(BASE_DIR):
        if f.lower().endswith((".mp4", ".mov", ".mkv", ".webm")):
            fpath = os.path.join(BASE_DIR, f)
            size_mb = round(os.path.getsize(fpath) / (1024 * 1024), 2)
            if not any(v["name"] == f for v in videos):
                videos.append({
                    "name": f,
                    "location": "root",
                    "path": fpath,
                    "url": f"/inputs/{f}" if os.path.exists(os.path.join(INPUTS_DIR, f)) else f,
                    "size_mb": size_mb
                })
    return {"videos": videos}

@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    """Sube un nuevo video al directorio inputs/ de forma segura sin sobreescribir nada"""
    clean_filename = f"upload_{str(uuid.uuid4())[:6]}_{file.filename}"
    dest_path = os.path.join(INPUTS_DIR, clean_filename)
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    size_mb = round(os.path.getsize(dest_path) / (1024 * 1024), 2)
    return {
        "status": "success",
        "name": clean_filename,
        "path": dest_path,
        "url": f"/inputs/{clean_filename}",
        "size_mb": size_mb
    }

@app.post("/api/edit")
def edit_video(req: EditRequest):
    """Ejecuta la edición guiada por prompt sin tocar el video original"""
    # Localizar archivo
    target_path = None
    if os.path.isabs(req.video_filename) and os.path.exists(req.video_filename):
        target_path = req.video_filename
    else:
        # Buscar en inputs/
        cand1 = os.path.join(INPUTS_DIR, req.video_filename)
        cand2 = os.path.join(BASE_DIR, req.video_filename)
        if os.path.exists(cand1):
            target_path = cand1
        elif os.path.exists(cand2):
            target_path = cand2

    if not target_path or not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail=f"No se encontró el video '{req.video_filename}'")

    try:
        res = ai_editor_engine.process_video_edit(
            source_video_path=target_path,
            prompt=req.prompt,
            forced_aspect=req.aspect_ratio,
            erase_box=req.erase_box
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/presets")
def get_presets():
    return {
        "presets": [
            {
                "id": "clothes_black_suit",
                "title": "👔 Cambiar Ropa a Traje Ejecutivo",
                "prompt": "Cambia la vestimenta por un traje ejecutivo negro de alta costura, iluminación de estudio suave y presencia imponente."
            },
            {
                "id": "podcast_mic_pro",
                "title": "🎙️ Superponer Micrófono de Podcast",
                "prompt": "Superponer un micrófono de podcast Shure al frente con escala y posición natural sin tapar elementos clave del fondo, y añadir lower-third con mi nombre."
            },
            {
                "id": "film_noir_punch",
                "title": "🎬 Film Noir + Dynamic Zoom",
                "prompt": "Aplica gradación de color Film Noir blanco y negro dramático con alto contraste, y añade dynamic punch zoom en los puntos de impacto."
            },
            {
                "id": "cyberpunk_neon",
                "title": "⚡ Cyberpunk Neón + Barra de Tiempo",
                "prompt": "Gradación de color Cyberpunk con sombras azules y resplandor neón magenta, junto con una barra de progreso inferior dorada."
            },
            {
                "id": "vhs_retro",
                "title": "📼 Textura VHS Retro + Grano",
                "prompt": "Filtro vintage VHS con grano cinematográfico, ligeras aberraciones cromáticas y lower third animado."
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8686))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
