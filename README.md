# ♾️ ComfyUI Sequential Batcher
**v1.6.0** | **VRAM-Optimized Generation** | **Recursive Self-Queuing** | **Perfect Audio Sync**

Una suite de grado profesional de nodos personalizados para ComfyUI. Diseñada para sortear los límites extremos de VRAM en la generación de vídeo pesado (WanVideo, Hunyuan, LTX) mediante **Auto-Encolado Recursivo**, procesamiento autónomo lote por lote y gestión de memoria forense.

> 🌍 **Read in English:** [README_EN.md](README_EN.md)

---

## 🌟 Lo Nuevo en v1.6.0 (Perfect Sync Update)
* **🛡️ VAE Safe Frame Padder (Hold Last Frame):** El motor ahora expande dinámicamente los tensores incompletos al final del vídeo. Si faltan frames para cumplir los estrictos requisitos de WanVideo (múltiplos de 4) o LTX (8n+1), clona el último fotograma de forma imperceptible. **Resultado: Cero cuelgues del VAE y 100% de sincronización de audio sin micro-cortes.**
* **📈 Inversión Matemática a "Expansión":** Los calculadores `AutoLoopCalculatorWan` y `AutoLoopCalculatorLTX` ahora redondean el timeline de forma segura hacia arriba, garantizando fluidez total en ciclos intermedios.

---

## ✨ Características Clave

* **Orquestación Autónoma:** Convierte tu ComfyUI en un motor de renderizado continuo. Pulsa "Queue Prompt" una sola vez y el flujo se retroalimentará modificando semillas e índices hasta terminar todo el vídeo.
* **Cortes Inteligentes (Smart Chunking):** Analiza el vídeo base y realiza cortes matemáticos protegiendo los frames donde los rostros son más nítidos, manteniendo la coherencia de identidad (Face Cuts).
* **Extracción de Audio Nativa:** Extrae la pista original directamente desde el nodo inicial y la inyecta de vuelta en el ensamblaje final.
* **Soporte Arquitecturas DiT (WanVideo & LTX 2.3):** Calculadores matemáticos específicos aseguran que los lotes de vídeo cumplan con las estrictas reglas de descompresión (múltiplos de 4 para WanVideo, o regla `8n + 1` para LTX).
* **Resoluciones Protegidas (Megapixel Shield):** Herramientas matemáticas (`ResTool`) que escalan las dimensiones automáticamente protegiendo el *training floor* de cada modelo base.

---

## ⚠️ Requisitos del Sistema (Crítico)

Para que el nodo `VideoAnalyzerWithAudio` pueda desempaquetar contenedores `.mp4` y extraer el audio con `torchaudio`, **FFmpeg es absolutamente obligatorio**.

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
El procesamiento se divide en roles altamente especializados:

* **🕵️ Video Analyzer Face detector + Audio:** Escanea el vídeo vía OpenCV o mediante un modelo YOLO acelerado por GPU. Extrae rostros, el audio y el Frame de Referencia.
* **📊 Auto Loop Calculator (Base / WanVideo / LTX):** Recibe la biometría y calcula las coordenadas de corte (chunk_frames, skip_frames).
* **🛡️ VAE Safe Frame Padder:** Intercepta el tensor final de VHS y lo rellena ("acolcha") clonando el último frame si falta material, salvando al VAE de un colapso.
* **🎞️ Incremental Auto-Stitcher:** Recoge los lotes renderizados y la pista de audio, cosiendo el vídeo final de forma progresiva en la carpeta temporal.
* **📥 Receiver & 📤 Sender:** Retienen y transfieren el último keyframe válido a través de los ciclos para mantener la coherencia temporal.
* **⏱️ Auto FPS Limiter:** Reduce los FPS inteligentemente garantizando que el audio y el movimiento mantengan una sincronización perfecta sin romper la VRAM.
* **🔀 Master Switch (Evaluación Perezosa):** Amputa físicamente los cables de rutas inactivas en el JSON enviado a ComfyUI. Los nodos pesados que no se necesitan en un ciclo específico ni siquiera se cargan en memoria.
* **🧹 VRAM Defragmenter:** Purga forense de memoria (Secuencia Sagrada) que limpia la caché de CUDA/MPS y fuerza al Garbage Collector entre ciclos pesados.

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
El `VideoAnalyzerWithAudio` tiene un puerto `bbox_detector` para delegar el escaneo facial a la tarjeta gráfica:
1. Instala el *Impact Pack*.
2. Añade el nodo `UltralyticsDetectorProvider` y selecciona un modelo de rostros (ej. `face_yolov8m.pt`).
3. Conecta su salida al puerto del Analyzer.
*(El nodo cuenta con auto-descarga: destruirá este modelo de la VRAM al terminar para hacer hueco a la generación).*

---

## 📝 Changelog Reciente
* **v1.6.0:** Implementación del `VAESafeFramePadder` (Hold Last Frame) y rediseño matemático a modo Expansión. Adiós a los recortes de audio y a los cuelgues en el ciclo final de WanVideo y LTX.
* **v1.5.4:** Inyección de la variable de entorno de PyTorch `max_split_size_mb:128` para evitar la micro-fragmentación de VRAM con kernels de Triton (SageAttention). Auto-descarga temprana de modelos YOLO.
* **v1.5.3:** "Secuencia Sagrada" en el VRAM Defragmenter (Romper ciclos -> Evacuación Suave -> Limpieza IPC -> Sincronización de hilos).
