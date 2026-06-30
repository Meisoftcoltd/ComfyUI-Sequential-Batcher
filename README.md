# ♾️ ComfyUI Sequential Batcher
**v0.8.3** | **VRAM-Optimized Generation** | **Recursive Self-Queuing** | **Perfect Audio Sync**

Una suite de grado profesional de nodos personalizados para ComfyUI. Diseñada para sortear los límites extremos de VRAM en la generación de vídeo pesado (WanVideo, Hunyuan, LTX) mediante **Auto-Encolado Recursivo**, procesamiento autónomo lote por lote y gestión de memoria forense.

> 🌍 **Read in English:** [README_EN.md](README_EN.md)

---

## ✨ Características Clave

* **Orquestación Autónoma:** Convierte tu ComfyUI en un motor de renderizado continuo. Pulsa "Queue Prompt" una sola vez y el flujo se retroalimentará modificando semillas e índices hasta terminar todo el vídeo.
* **Cortes Inteligentes (Smart Chunking):** Analiza el vídeo base y realiza cortes matemáticos protegiendo los frames donde los rostros son más nítidos, manteniendo la coherencia de identidad (Face Cuts).
* **Extracción de Audio Nativa:** Extrae la pista original directamente desde el nodo inicial y la inyecta de vuelta en el ensamblaje final.
* **Soporte Arquitecturas DiT (WanVideo & LTX 2.3):** Calculadores matemáticos específicos aseguran que los lotes de vídeo cumplan con las estrictas reglas de descompresión (regla de `4n + 1` para WanVideo, o regla `8n + 1` para LTX).
* **Resoluciones Protegidas (Megapixel Shield):** Herramientas matemáticas (`ResTool`) que escalan las dimensiones automáticamente protegiendo el *training floor* de cada modelo base.

---

## ⚠️ Requisitos del Sistema (Crítico)

Para que el nodo `VideoAnalyzerFaceDetector` pueda desempaquetar contenedores `.mp4` y extraer el audio con `torchaudio`, **FFmpeg es absolutamente obligatorio**.

* **🐧 Ubuntu / Linux / WSL2:**
  El script intentará instalarlo por ti. Si falla, ejecuta manualmente:
  ```bash
  sudo apt update && sudo apt install ffmpeg -y
  ```
* **🪟 Windows:**
  Descarga los binarios precompilados de FFmpeg y añade la carpeta `bin` a tus variables de entorno (PATH).

### 🚨 Advertencia Crítica sobre el Uso de la VRAM
Se **desrecomienda encarecidamente** el uso del argumento `--highvram` al arrancar ComfyUI.

El argumento `--highvram` le da la orden estricta a ComfyUI de mantener los modelos bloqueados en la memoria de video. Esto sabotea directamente el funcionamiento de nuestro `VRAM Defragmenter`, ya que bloquea el comando `mm.unload_all_models()` impidiendo que la gráfica se vacíe entre ciclos. Para que esta suite funcione correctamente con modelos masivos como WanVideo y evite errores de OOM (Out Of Memory), los usuarios deben usar el arranque estándar (o `--normalvram`), permitiendo que el sistema libere dinámicamente la memoria hasta llegar a 0 GB entre lotes.

---

## 🧠 La Arquitectura Híbrida (Desglose de Nodos)

El procesamiento se divide en roles altamente especializados, organizados en las siguientes categorías:

### 🎼 Orquestación
* **🏁 Loop Start (Index):** Inicia la secuencia de bucle y mantiene el índice actual.
* **🚀 Loop Trigger (Auto-Queue):** Dispara la siguiente iteración de ComfyUI de manera autónoma hasta que se completa la tarea.

### 🎬 Director / Storyboard
* **🎬 Dynamic Scene Director:** Máquina de estados para orquestar metadatos (prompts, duraciones) en la preproducción (Split-Workflow).
* **💾 Save Scene Keyframe / 🖼️ Load Scene Keyframe:** Guarda y carga los frames clave de la escena para mantener la continuidad entre flujos separados.

### 📦 Lotes (Batches)
* **📂 Batch Audio Folder Loader:** Carga dinámicamente carpetas enteras de archivos (ej. lotes de audio).
* **🎛️ Audio Batch Selector:** Despacha los archivos del lote uno por uno sincronizándose con el bucle.

### 🔬 Análisis y Cálculos
* **🕵️ Video Analyzer Face detector + Audio:** Escanea el vídeo vía OpenCV/YOLO, extrayendo rostros, audio y frame de referencia.
* **🎬 Video Analyzer Scene detector:** Detecta cortes de escena en los vídeos.
* **📊 Auto Loop Calculators:** Nodos especializados (`Base`, `WanVideo`, `LTX`, `TTS`) que reciben metadatos y calculan matemáticamente las coordenadas de corte exactas (`chunk_frames`, `skip_frames`).

### 🎞️ Video
* **🎞️ Incremental Auto-Stitcher:** Ensambla progresivamente los fragmentos de video renderizados en un único archivo.
* **🛡️ VAE Safe Frame Padder:** Rellena ("acolcha") tensores incompletos clonando el último frame para salvar al VAE de un colapso en modelos restrictivos (ej. reglas 4n+1).
* **💉 LTXV Single Frame Injector:** Inyecta frames individuales específicos requeridos por flujos de LTX.
* **⏱️ Auto FPS Limiter:** Limita de manera inteligente los cuadros por segundo para ahorrar VRAM manteniendo sincronía de audio.

### 🎵 Audio
* **✂️ Precise Audio Slicer:** Corta el audio de forma precisa (a nivel de muestra matemática) en base a los frames de vídeo correspondientes.
* **🎛️ Conditional Audio Router (Bypass):** Enruta el audio condicionalmente permitiendo saltar su procesamiento si no es necesario.

### 📐 Herramientas de Resolución
* **ResTool (`8x`, `16x`, `32x`, `64x`, `64xLTX`):** Calculan resoluciones óptimas basadas en límites de VRAM y las reglas geométricas (multiplicadores) de diferentes modelos (SD1.5, SDXL, WanVideo, Hunyuan, LTX).

### 🧠 Gestión de Memoria / Lógica
* **🔀 Master Switch & 🗄️ Lazy Session Cache:** Evaluación perezosa nativa; amputan rutas inactivas para que los nodos pesados ni siquiera se carguen en memoria.
* **🧹 VRAM Defragmenter:** Purga forense de memoria (Secuencia Sagrada) que limpia la caché de CUDA/MPS y fuerza al recolector de basura (GC) de Python entre ciclos.
* **📥 Session Image Receiver / 📤 Session Image Sender:** Retienen y transfieren imágenes en memoria a través de diferentes ciclos.

---

## 🔌 Guía de Cableado Rápido (Workflow Setup)

1. **El Explorador:** Coloca el `Video Analyzer` al principio. Sube un vídeo (o usa una ruta de YTDLP).
2. **Matemáticas:** Conecta `total_frames` y `safe_faces_list` hacia tu `Auto Loop Calculator` elegido.
3. **Extracción Segura:** Añade el nodo nativo `VHS_LoadVideo`. Conviértele la entrada a *video_name* y conéctala al Analyzer. Conecta su salida `IMAGE` al nuevo nodo `VAE Safe Frame Padder`.
4. **Passthrough de Audio:** Lleva el cable `source_audio` desde el Explorador directamente hasta el puerto `audio` de tu `Incremental Auto-Stitcher` (al final del flujo).
5. **El Gatillo:** Conecta la salida de tu Stitcher al nodo `Loop Trigger (Auto-Queue)`.
6. **Ejecución:** Conecta el `Loop Start (Index)` al Cerebro y al Stitcher.
7. **Dispara:** Haz clic en "Queue Prompt" **UNA SOLA VEZ**. ¡Disfruta de la magia autónoma!

---

## 🚀 Aceleración por GPU (Escaneo de Rostros)
El `VideoAnalyzerFaceDetector` tiene un puerto `bbox_detector` para delegar el escaneo facial a la tarjeta gráfica:
1. Instala el *Impact Pack*.
2. Añade el nodo `UltralyticsDetectorProvider` y selecciona un modelo de rostros (ej. `face_yolov8m.pt`).
3. Conecta su salida al puerto del Analyzer.
*(El nodo cuenta con auto-descarga: destruirá este modelo de la VRAM al terminar para hacer hueco a la generación).*
