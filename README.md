# VIDEDIT AI Studio — Next-Gen Prompt-Driven Video VFX & Inpainting

Plataforma autónoma de edición de video con Inteligencia Artificial guiada por lenguaje natural. Permite realizar cortes, efectos especiales de código, motion graphics, y conectar modelos generativos de video inpainting en la nube (Fal.ai, Replicate, Seedance 2.0).

---

## Características Principales

1. **Edición Guiada por Lenguaje Natural:** Describe en palabras lo que deseas aplicar sobre el video (color grading, punch zoom, lower thirds, conversión 9:16 vertical real).
2. **Protección Total del Video Original:** Los videos de entrada en `inputs/` se tratan como solo lectura y jamás se sobreescriben. Todas las ediciones se exportan versionadas a `outputs/`.
3. **Herramienta Interactiva de Región:** Permite dibujar recuadros directamente sobre el video para marcar objetos.
4. **Integración con Modelos Generativos en la Nube:**
   - **Fal.ai (`bria/video/erase/prompt`):** Eliminación fotorrealista de objetos mediante difusión temporal.
   - **Replicate (`jd7h/propainter`):** Inpainting de video con propagación de flujo óptico.
   - **Seedance 2.0:** Planificación y generación cinematográfica.

---

## Despliegue en la Nube (Sin Localhost)

Este repositorio está preparado para correr en cualquier proveedor de hosting en la nube con Docker o Python:

### Opción 1: Render / Railway (Recomendada)
1. Conecta este repositorio de GitHub en [Render](https://render.com) o [Railway](https://railway.app).
2. Selecciona **Web Service** y entorno **Docker**.
3. Configura tus variables de entorno si vas a usar APIs generativas:
   - `FAL_KEY`: Clave de Fal.ai para video eraser.
   - `REPLICATE_API_TOKEN`: Clave de Replicate para ProPainter.
   - `GROQ_API_KEY`: Clave de Groq para interpretación de prompts con Llama 3.3.
4. El servicio te proporcionará una URL pública (ej. `https://videdit-ai.onrender.com`).

### Opción 2: Hugging Face Spaces (Gratuito con Docker)
1. Crea un nuevo Space en Hugging Face con SDK **Docker**.
2. Conecta este repositorio de GitHub.
3. El Space se desplegará automáticamente y tendrás tu app accesible públicamente.

---

## Ejecución Local

```bash
# Instalar dependencias
pip install -r requirements.txt

# Iniciar servidor
python server.py
# Acceso en: http://localhost:8686
```

---

## Licencia
Propiedad de **IsaPromo RD** (`isapromord`). Todos los derechos reservados.
