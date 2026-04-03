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
* **Soporte Nativo LTX 2.3:** Se han añadido calculadores matemáticos específicos (`AutoLoopCalculatorLTX` y `ResTool64xLTX`) para garantizar que los lotes de vídeo cumplan con las estrictas reglas de descompresión de arquitectura DiT y el factor de escala latente (resoluciones divisibles por 64 y particiones de fotogramas de `8n + 1`).

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
El procesamiento de vídeo se divide en roles altamente especializados:

* **🕵️ Video Analyzer + Audio (El Explorador):** Escanea el vídeo vía OpenCV, extrae el audio y escupe un Frame de Referencia visual. Actúa como la puerta de entrada principal.
* **📊 Auto Loop Calculator (El Cerebro):** Recibe la biometría del Explorador y calcula las coordenadas de corte asimétricas (chunk_frames, skip_frames) con un margen dinámico del ±10% para evitar minilotes residuales.
* **📊 Auto Loop Calculator (WanVideo 3dVAE):** Alternativa para WanVideo que asegura que los chunks de frames sean estrictamente múltiplos de 4, protegiendo al VAE 3D de colapsar.
* **🛠️ El Obrero (VHS_LoadVideo):** Liberado de tareas de análisis, este nodo estándar de ComfyUI se limita a extraer los tensores exactos que el Cerebro le ordena.
* **🎞️ Incremental Auto-Stitcher (El Ensamblador):** Recoge los lotes renderizados y la pista de audio original, cosiendo el vídeo final de forma progresiva.
* **📥 Session Image Receiver** y **📤 Session Image Sender:** Retienen y transfieren el último keyframe válido (frame de referencia) a través de los ciclos para mantener la coherencia temporal de la identidad.
* **⏱️ Auto FPS Limiter (El Sincronizador):** Previene errores de VRAM en vídeos de alta tasa de fotogramas (ej. 60 FPS) calculando automáticamente el salto de frames necesario (`select_every_nth`) y ajustando los FPS finales para garantizar que el audio y el movimiento mantengan una sincronización perfecta.
* **Resoluciones Protegidas (Megapixel Shield):** Herramientas de resolución matemáticas que escalan las dimensiones para evitar artefactos protegiendo el "training floor" de cada modelo:
  * **📐 ResTool 8x (SD1.5)**
  * **📏 ResTool 16x (SDXL)**
  * **🎞️ ResTool 32x (WanVideo)**
  * **🎬 ResTool 64x (Hunyuan)**

## 🔌 Guía de Cableado (Workflow Setup)
Para montar el flujo secuencial perfecto, sigue estos pasos:

1. **Setup Inicial:** Coloca el 🕵️ Video Analyzer + Audio al principio. Sube un vídeo o conéctale un cable STRING desde tu descargador favorito.
2. **Matemáticas:** Conecta total_frames y safe_faces_list del Explorador hacia el 📊 Auto Loop Calculator (o 📊 Auto Loop Calculator (WanVideo 3dVAE) si usas WanVideo).
3. **Extracción:** Añade un nodo VHS_LoadVideo. Haz clic derecho en él -> Convert Widget to Input -> video. Conecta el video_name del Explorador a esta nueva entrada. Alimenta los parámetros de corte desde el Cerebro.
4. **Passthrough de Audio:** Lleva el cable source_audio desde el Explorador hasta el puerto audio de tu 🎞️ Incremental Auto-Stitcher (al final del flujo).
5. **El Gatillo:** Conecta la salida de tu Stitcher a la entrada del 🚀 Loop Trigger (Auto-Queue).
6. **Ejecución:** Conecta el 🏁 Loop Start (Index) al Cerebro y al Stitcher. Dale a "Queue Prompt" UNA SOLA VEZ (sin marcar Auto Queue en la UI). ¡Disfruta de la magia autónoma!

## 🧹 Auto-Limpieza de VRAM (NUEVO)
El nodo `SequentialLoopTrigger` ahora actúa como un gestor de limpieza inteligente. Una vez que detecta que se han procesado todos los frames y la generación del video ha finalizado, automáticamente:
1. Obliga a ComfyUI a soltar de memoria todos los modelos pesados (WanVideo, VAE, etc.).
2. Fuerza al recolector de basura de Python para eliminar memoria residual en la RAM.
3. Vacía profundamente las cachés de PyTorch, soportando múltiples plataformas (CUDA/ROCm para NVIDIA/AMD, y MPS para Apple Silicon).

¡Esto asegura que tu gráfica vuelva a 0GB de uso al terminar, previniendo errores OOM en tus siguientes generaciones!

**Changelog v1.5.3:** Se ha introducido un sistema de limpieza profunda automática de VRAM en el nodo `SequentialLoopTrigger`, garantizando que la memoria de la GPU (y RAM) se libere completamente tras la generación de videos pesados en arquitecturas CUDA, ROCm y Mac MPS.
**Changelog v1.5.2:** Instalación automatizada de FFmpeg, mejora crítica en el bypass del pre-flight check de ComfyUI para inputs dinámicos en el Analyzer, y exposición detallada de excepciones de torchaudio.
