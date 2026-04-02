# ♾️ ComfyUI Sequential Batcher
**v1.5.2** | **VRAM-Optimized Generation** | **Recursive Self-Queuing**

Una suite de grado profesional de nodos personalizados para ComfyUI. Diseñada para sortear los límites de VRAM en la generación de vídeo pesado (WanVideo, Hunyuan, etc.) mediante **Auto-Encolado Recursivo** y procesamiento autónomo lote por lote.

> 🌍 **Read in English:** [README_EN.md](README_EN.md)

---

## ✨ Características Clave

* **Orquestación Autónoma:** Convierte tu ComfyUI en un motor de renderizado continuo. Pulsa "Queue" una sola vez y el flujo se retroalimentará hasta terminar todo el vídeo.
* **Cortes Inteligentes (Smart Chunking):** Analiza el vídeo base y realiza cortes matemáticos evitando separar frames donde los rostros son más nítidos, manteniendo la coherencia de identidad.
* **Extracción de Audio Nativa:** Extrae la pista de audio original directamente desde el nodo inicial y la inyecta de vuelta en el ensamblaje final.
* **Dual Input Engine:** El nodo explorador acepta tanto vídeos subidos manualmente como rutas inyectadas por cable desde descargadores (ej. YTDLP) comportándose exactamente como VideoHelperSuite.

---

## ⚠️ Requisitos del Sistema (Crítico)

Para que el nodo `VideoAnalyzerWithAudio` pueda desempaquetar contenedores `.mp4` y extraer el audio con `torchaudio`, **FFmpeg es absolutamente obligatorio**.

* **🐧 Ubuntu / Linux / WSL2:**
  El script de ComfyUI Manager intentará instalarlo por ti. Si falla, ejecuta:
  ```bash
  sudo apt update && sudo apt install ffmpeg -y
  ```
* **🪟 Windows:**
  Descarga los binarios precompilados de FFmpeg y añade la carpeta bin a tus variables de entorno (PATH).

## 🧠 La Arquitectura Híbrida (Cómo funciona)
El procesamiento de vídeo se divide en 4 roles altamente especializados:

* **🕵️ El Explorador (VideoAnalyzerWithAudio):** Escanea el vídeo vía OpenCV, extrae el audio y escupe un Frame de Referencia visual. Actúa como la puerta de entrada principal.
* **📊 El Cerebro (AutoLoopCalculator):** Recibe la biometría del Explorador y calcula las coordenadas de corte asimétricas (chunk_frames, skip_frames) con un margen dinámico del ±10% para evitar minilotes residuales.
* **🛠️ El Obrero (VHS_LoadVideo):** Liberado de tareas de análisis, este nodo estándar de ComfyUI se limita a extraer los tensores exactos que el Cerebro le ordena.
* **🎞️ El Ensamblador (IncrementalVideoStitcher):** Recoge los lotes renderizados y la pista de audio original, cosiendo el vídeo final de forma progresiva.

## 🔌 Guía de Cableado (Workflow Setup)
Para montar el flujo secuencial perfecto, sigue estos pasos:

1. **Setup Inicial:** Coloca el 🕵️ Video Analyzer + Audio al principio. Sube un vídeo o conéctale un cable STRING desde tu descargador favorito.
2. **Matemáticas:** Conecta total_frames y safe_faces_list del Explorador hacia el 📊 Auto Loop Calculator.
3. **Extracción:** Añade un nodo VHS_LoadVideo. Haz clic derecho en él -> Convert Widget to Input -> video. Conecta el video_name del Explorador a esta nueva entrada. Alimenta los parámetros de corte desde el Cerebro.
4. **Passthrough de Audio:** Lleva el cable source_audio desde el Explorador hasta el puerto audio de tu 🎞️ Incremental Auto-Stitcher (al final del flujo).
5. **El Gatillo:** Conecta la salida de tu Stitcher a la entrada del 🚀 Loop Trigger (Auto-Queue).
6. **Ejecución:** Conecta el 🏁 Loop Start al Cerebro y al Stitcher. Dale a "Queue Prompt" UNA SOLA VEZ (sin marcar Auto Queue en la UI). ¡Disfruta de la magia autónoma!

**Changelog v1.5.2:** Instalación automatizada de FFmpeg, mejora crítica en el bypass del pre-flight check de ComfyUI para inputs dinámicos en el Analyzer, y exposición detallada de excepciones de torchaudio.
