# ♾️ ComfyUI Sequential Batcher
**v1.5.4** | **VRAM-Optimized Generation** | **Recursive Self-Queuing**

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

* **🕵️ Video Analyzer Face detector + Audio (El Explorador):** Escanea el vídeo vía OpenCV o mediante un modelo YOLO/ONNX acelerado por GPU (opcional) para detección precisa de rostros, extrae el audio y escupe un Frame de Referencia visual. Actúa como la puerta de entrada principal.
* **📊 Auto Loop Calculator (El Cerebro):** Recibe la biometría del Explorador y calcula las coordenadas de corte asimétricas (chunk_frames, skip_frames) con un margen dinámico del ±10% para evitar minilotes residuales.
* **📊 Auto Loop Calculator (WanVideo 3dVAE):** Alternativa para WanVideo que asegura que los chunks de frames sean estrictamente múltiplos de 4, protegiendo al VAE 3D de colapsar.
* **🛠️ El Obrero (VHS_LoadVideo):** Liberado de tareas de análisis, este nodo estándar de ComfyUI se limita a extraer los tensores exactos que el Cerebro le ordena.
* **🎞️ Incremental Auto-Stitcher (El Ensamblador):** Recoge los lotes renderizados y la pista de audio original, cosiendo el vídeo final de forma progresiva.
* **📥 Session Image Receiver** y **📤 Session Image Sender:** Retienen y transfieren el último keyframe válido (frame de referencia) a través de los ciclos para mantener la coherencia temporal de la identidad.
* **⏱️ Auto FPS Limiter (El Sincronizador):** Previene errores de VRAM en vídeos de alta tasa de fotogramas (ej. 60 FPS) calculando automáticamente el salto de frames necesario (`select_every_nth`) y ajustando los FPS finales para garantizar que el audio y el movimiento mantengan una sincronización perfecta.
* **🔀 Master Switch (Evaluación Perezosa y Cirugía de Grafo):** Nodo lógico avanzado que utiliza *Evaluación Perezosa Nativa* en el Ciclo 0 y *Cirugía de Grafo en Caliente* en ciclos posteriores. Amputa físicamente los cables de rutas inactivas en el JSON enviado a ComfyUI, asegurando que los nodos pesados (como Lip Syncs o Upscalers) ni siquiera se carguen en memoria cuando no se necesitan, lo que representa un ahorro masivo de VRAM.
* **Resoluciones Protegidas (Megapixel Shield):** Herramientas de resolución matemáticas que escalan las dimensiones para evitar artefactos protegiendo el "training floor" de cada modelo:
  * **📐 ResTool 8x (SD1.5)**
  * **📏 ResTool 16x (SDXL)**
  * **🎞️ ResTool 32x (WanVideo)**
  * **🎬 ResTool 64x (Hunyuan)**

## 🔌 Guía de Cableado (Workflow Setup)
Para montar el flujo secuencial perfecto, sigue estos pasos:

1. **Setup Inicial:** Coloca el 🕵️ Video Analyzer Face detector + Audio al principio. Sube un vídeo o conéctale un cable STRING desde tu descargador favorito. Opcionalmente, conecta un nodo 'ONNX Detection Model Loader' a su entrada `bbox_detector` para escaneo de rostros por GPU.
2. **Matemáticas:** Conecta total_frames y safe_faces_list del Explorador hacia el 📊 Auto Loop Calculator (o 📊 Auto Loop Calculator (WanVideo 3dVAE) si usas WanVideo).
3. **Extracción:** Añade un nodo VHS_LoadVideo. Haz clic derecho en él -> Convert Widget to Input -> video. Conecta el video_name del Explorador a esta nueva entrada. Alimenta los parámetros de corte desde el Cerebro.
4. **Passthrough de Audio:** Lleva el cable source_audio desde el Explorador hasta el puerto audio de tu 🎞️ Incremental Auto-Stitcher (al final del flujo).
5. **El Gatillo:** Conecta la salida de tu Stitcher a la entrada del 🚀 Loop Trigger (Auto-Queue).
6. **Ejecución:** Conecta el 🏁 Loop Start (Index) al Cerebro y al Stitcher. Dale a "Queue Prompt" UNA SOLA VEZ (sin marcar Auto Queue en la UI). ¡Disfruta de la magia autónoma!

## 🚀 Aceleración por GPU para el Escaneo de Rostros (NUEVO)
El nodo `VideoAnalyzerWithAudio` ahora cuenta con un puerto de entrada opcional llamado `bbox_detector`. Esto permite delegar el escaneo facial a tu tarjeta gráfica, multiplicando la velocidad de análisis masivamente.

**Cómo usarlo:**
1. Instala el popular **Impact Pack**.
2. Añade el nodo `UltralyticsDetectorProvider` a tu lienzo.
3. Selecciona un modelo de rostros (ej. `bbox/face_yolov8m.pt`).
4. Conecta la salida `BBOX_DETECTOR` a la nueva entrada de nuestro nodo Explorador.
*Nota: Si no conectas nada a este puerto, el nodo usará un escaneo estándar por CPU (OpenCV) como método de respaldo.*

## 🧹 Auto-Limpieza y Desfragmentación Profunda de VRAM (NUEVO)
El entorno ahora implementa un blindaje anti-fragmentación de nivel forense, esencial para modelos masivos como WanVideo:
* **Secuencia Sagrada de Destrucción:** El nodo `VRAM Defragmenter` ejecuta una secuencia estricta de limpieza (Romper ciclos Python -> Evacuación Suave -> Descarga de Modelos -> Limpieza IPC -> Vaciado CUDA -> Sincronización de Hilos) para eliminar fragmentos huérfanos y prevenir *race conditions* asíncronas con kernels de Triton (como SageAttention).
* **Asignador de Memoria Bloqueado:** Se inyecta la variable de entorno `PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:128"` automáticamente al inicio para prohibir a PyTorch trocear bloques de VRAM mayores a 128 MB, garantizando bloques continuos masivos para los samplers.
* **Auto-Descarga del Explorador:** El nodo `VideoAnalyzerWithAudio` ahora incluye la opción `unload_detector` para destruir inmediatamente de la VRAM el modelo de detección facial una vez finalizado el escaneo, liberando espacio crítico antes de que comience la generación pesada.

El nodo `SequentialLoopTrigger` además actúa como gestor de limpieza de cierre, forzando a ComfyUI a soltar todos los modelos pesados al terminar la generación del vídeo. ¡Esto asegura que tu gráfica vuelva a 0GB de uso, previniendo errores OOM!

**Changelog v1.5.4:** Implementación de "Secuencia Sagrada" de limpieza en `VRAM Defragmenter`, inyección de entorno anti-micro-fragmentación de PyTorch (`max_split_size_mb:128`), y auto-destrucción temprana del detector de rostros en el Analyzer.
**Changelog v1.5.3:** Se ha introducido un sistema de limpieza profunda automática de VRAM en el nodo `SequentialLoopTrigger`, garantizando que la memoria de la GPU (y RAM) se libere completamente tras la generación de videos pesados en arquitecturas CUDA, ROCm y Mac MPS.
**Changelog v1.5.2:** Instalación automatizada de FFmpeg, mejora crítica en el bypass del pre-flight check de ComfyUI para inputs dinámicos en el Analyzer, y exposición detallada de excepciones de torchaudio.
