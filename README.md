# ComfyUI Sequential Batcher (v1.5.1)

Una suite altamente especializada de nodos personalizados para ComfyUI diseñada para el **Auto-Encolado Recursivo (Recursive Self-Queuing)** y el procesamiento secuencial autónomo. Esta arquitectura minimiza el uso de VRAM procesando tareas pesadas (como la generación de vídeo) de forma secuencial, lote por lote, orquestadas completamente desde dentro del propio grafo.

> **Read in English:** [README_EN.md](README_EN.md)

---

## 🌟 La Arquitectura Híbrida de Identidad

La **Arquitectura Híbrida de Identidad** (introducida en v1.4.1) elimina la deuda técnica de los antiguos cargadores acoplados y divide el procesamiento de video en tres roles lógicos principales:

1. **🕵️ El Explorador (`VideoAnalyzerWithAudio`)**: Integrado nativamente con VideoHelperSuite, utiliza OpenCV para escanear el vídeo de entrada en busca de rostros nítidos, extraer la pista de audio íntegra pura (Torchaudio), y **generar y emitir un Frame de Referencia (Preview Visual)** en formato de imagen (`IMAGE`) directamente en el lienzo de ComfyUI.
2. **📊 El Cerebro (`AutoLoopCalculator`)**: Recibe la lista de frames seguros del Explorador y planifica cortes asimétricos e inteligentes (`chunk_frames`, `skip_frames`). Prioriza realizar cortes en frames donde el rostro es nítido para mantener la coherencia de identidad entre bucles, e incluye un **Margen Dinámico del ±10%** para absorber restos finales sin colas ineficientes.
3. **🛠️ El Obrero (`VHS_LoadVideo`)**: El nodo estándar de VideoHelperSuite de ComfyUI ahora se encarga exclusivamente del trabajo pesado: extraer los tensores de vídeo exactos según las órdenes del Cerebro.

---

## 🧩 Los Nodos Principales

El sistema se organiza en cuatro categorías principales en la interfaz de ComfyUI bajo el menú `🔁 Sequential Batcher`:

### 🔁 Loop (Orquestación Autónoma)

1. **`🏁 Loop Start (Index)`**
   - **Inputs:** `reset_loop` (BOOLEAN), `loop_idx` (INT)
   - **Outputs:** `current_loop_index` (INT)
   - **Descripción:** Inicia el bucle, gestiona el índice global y provee el índice actual a los nodos de imagen y vídeo del flujo.

2. **`🚀 Loop Trigger (Auto-Queue)`**
   - **Inputs:** `trigger_dependency` (*), `port` (INT)
   - **Descripción:** Se coloca al final del flujo de trabajo. Incrementa el contador y auto-encola el siguiente ciclo mediante un POST a la propia API de ComfyUI (`/prompt`).
   - **Funciones Especiales:**
     - **Mutador de Semillas:** Inyecta nuevas semillas aleatorias (32 bits) a cualquier nodo con `seed` o `noise_seed` en el lienzo para romper la caché hacia adelante.
     - **💉 Inyección Anti-Caché:** Busca específicamente al nodo `Loop Start` dentro de la carga útil JSON e inyecta forzosamente el nuevo índice para romper la caché inversa que congela el flujo.

### 🖼️ Image (Memoria de Sesión)

3. **`📥 Session Image Receiver`**
   - **Inputs:** `initial_image` (IMAGE), `current_loop_index` (INT)
   - **Outputs:** `current_image` (IMAGE)
   - **Descripción:** Proporciona la imagen inicial o la última generada del ciclo anterior, rescatando la sesión almacenada en la memoria RAM global.

4. **`📤 Session Image Sender`**
   - **Inputs:** `generated_images` (IMAGE), `current_loop_index` (INT), `validate_face` (BOOLEAN)
   - **Outputs:** `VALIDATED_IMAGES` (IMAGE)
   - **Descripción:** Extrae la última imagen válida del lote y la asegura en la memoria del sistema global (`.clone().cpu()`) para el siguiente ciclo.
   - **Funciones Especiales:**
     - **💾 Guardado de Keyframes:** Realiza un volcado de seguridad en el disco duro, guardando progresivamente `keyframe_XXX.png` cada ciclo.
     - **🏎️ Motor Dinámico F1:** Trunca dinámicamente el tensor generado hacia atrás buscando el último rostro válido (si `validate_face` es True), y actualiza el acumulador global para que el `Auto Loop Calculator` reajuste el siguiente ciclo sin desincronizaciones de audio.

### 🛠️ Tools (Herramientas y Resoluciones)

Nodos dedicados para calcular resoluciones estrictamente divisibles y proteger tu VRAM de errores de tensores, aplicando un límite matemático hacia abajo.

- **`📐 ResTool 8x (SD1.5)`**: Múltiplos de 8. Base nativa ~262,144 px.
- **`📏 ResTool 16x (SDXL)`**: Múltiplos de 16. Base nativa ~1,048,576 px.
- **`🎞️ ResTool 32x (WanVideo)`**: Múltiplos de 32. Base nativa ~399,360 px.
- **`🎬 ResTool 64x (Hunyuan)`**: Múltiplos de 64. Base nativa ~921,600 px.

**Todas las herramientas comparten la misma interfaz:**
- **Inputs:** `aspect_ratio` (ej. 16:9, 9:16), `base_resolution` (Campo numérico INT libre, puedes escribir el valor exacto que necesites, ej. 832 o 1024)
- **Outputs:** `width` (INT), `height` (INT), `debug_info` (STRING)

> **🛡️ Escudo de Megapíxeles (NUEVO en v1.5.1):** Cada herramienta conoce el "suelo de entrenamiento" (Training Floor) de su modelo. Si solicitas una resolución extrema que cae por debajo del área mínima vital, el nodo escalará primero la resolución proporcionalmente hacia arriba para proteger la generación contra artefactos, y luego aplicará la divisibilidad estricta.

### 🎞️ Video (Ensamblaje y Validación)

5. **`🕵️ Video Analyzer + Audio`**
   - **Inputs:** `video` (STRING), `reference_frame_idx` (INT), `use_face_detector` (BOOLEAN), `blur_threshold` (FLOAT)
   - **Outputs:** `video_name` (STRING), `total_frames` (INT), `source_fps` (FLOAT), `source_audio` (AUDIO), `safe_faces_list` (FACE_CUTS), `reference_frame` (IMAGE)
   - **Descripción:** Escanea el vídeo usando OpenCV para detectar frames con rostros nítidos, extrae la pista de audio pura usando Torchaudio y emite un Frame de Referencia visual y en tensor (`IMAGE`).

6. **`📊 Auto Loop Calculator`**
   - **Inputs:** `source_frame_count` (INT), `target_frames_per_loop` (INT), `select_every_nth` (INT), `current_loop_index` (INT)
   - **Optional Input:** `safe_faces_list` (FACE_CUTS)
   - **Outputs:** `chunk_frames` (INT), `skip_frames` (INT), `select_every_nth` (INT)
   - **Descripción:** Calcula los cortes de los frames asimétricamente basado en rostros seguros y aplica el margen dinámico.

7. **`📊 Auto Loop Calculator (WanVideo 3dVAE)`**
   - **Inputs:** `source_frame_count` (INT), `target_frames_per_loop` (INT), `select_every_nth` (INT), `current_loop_index` (INT)
   - **Optional Input:** `safe_faces_list` (FACE_CUTS)
   - **Outputs:** `chunk_frames` (INT), `skip_frames` (INT), `select_every_nth` (INT)
   - **Descripción:** Variante especializada para el modelo WanVideo. Incluye un blindaje matemático estricto que trunca todas las metas y totales de frames hacia abajo a múltiplos de 4, ignorando de forma segura los últimos 1 a 3 frames remanentes para evitar que el 3D VAE colapse con el error de "shape is invalid".

8. **`🎞️ Incremental Auto-Stitcher`**
   - **Inputs:** `images` (IMAGE), `audio` (AUDIO), `current_loop_index` (INT)
   - **Outputs:** `ALL_IMAGES` (IMAGE), `AUDIO_OUT` (AUDIO)
   - **Descripción:** Archiva progresivamente los tensores generados temporalmente en el disco duro (`.pt`) liberando la RAM (**Cero OOM**) de inmediato. En el ciclo final, ensambla todos los bloques con un passthrough limpio de la pista de audio original.

---

## 🚀 Configuración y Uso

### Prerrequisitos
- **VideoHelperSuite (VHS)**: Obligatorio para el nodo "Obrero" de extracción (`VHS_LoadVideo`).
- **OpenCV (`opencv-python`)**: Necesario para el Explorador (`VideoAnalyzerWithAudio`). Sin él, la detección de rostros fallará elegantemente.
- **FFmpeg**: Debe estar instalado y disponible en el PATH de tu sistema.
- **Torchaudio**: Necesario para la extracción pura de audio (generalmente preinstalado con PyTorch).

### Instalación
1. Ve a la carpeta `custom_nodes` de ComfyUI.
2. Ejecuta: `git clone https://github.com/your-repo/ComfyUI-Sequential-Batcher.git`
3. Instala los requerimientos adicionales si te falta alguno: `pip install -r requirements.txt` (o `pip install opencv-python`).
4. Reinicia ComfyUI.

### 🔌 Guía de Conexión de la Arquitectura Híbrida

1. **El Explorador (`🕵️ Video Analyzer + Audio`)**: Colócalo al inicio del flujo y sube o selecciona tu vídeo base aquí.
2. **El Cerebro (`📊 Auto Loop Calculator`)**:
   - Conecta `total_frames` del Explorador a `source_frame_count`.
   - Conecta `safe_faces_list` del Explorador (opcional pero recomendado).
   - Conecta `current_loop_index` desde el nodo `🏁 Loop Start`.
3. **El Obrero (`VHS_LoadVideo`)**:
   - Haz clic derecho sobre el nodo de VHS y selecciona **Convert Widget to Input -> video**.
   - Conecta `video_name` del Explorador a la entrada `video` del Obrero.
   - Conecta `chunk_frames`, `skip_frames`, y `select_every_nth` del Cerebro a sus respectivos pines en el Obrero.
4. **Audio Passthrough**: Saca un cable directo desde `source_audio` del Explorador y conéctalo al puerto `audio` de tu `🎞️ Incremental Auto-Stitcher` al final del flujo.
5. **Cierre de Ciclo (`🚀 Loop Trigger`)**: Conecta la salida de imagen o audio de tu Auto-Stitcher en la entrada `trigger_dependency`.
6. **Ejecución**: Pulsa **"Queue Prompt" UNA sola vez** (no marques la casilla Auto Queue en la interfaz de Comfy). El nodo Trigger se encargará de realizar el auto-encolado recursivo por detrás.

---
*Diseñado y optimizado para llevar la automatización secuencial y la identidad de ComfyUI un paso más allá.*
