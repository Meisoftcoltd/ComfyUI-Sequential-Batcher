# ComfyUI Sequential Batcher (v1.4.1)

Una suite altamente especializada de nodos personalizados para ComfyUI diseñada para el **Auto-Encolado Recursivo (Recursive Self-Queuing)** y el procesamiento secuencial autónomo. Esta arquitectura minimiza el uso de VRAM procesando tareas pesadas (como la generación de vídeo) de forma secuencial, lote por lote, orquestadas completamente desde dentro del propio grafo.

> **Read in English:** [README_EN.md](README_EN.md)

## La Arquitectura Híbrida de Identidad

A partir de la versión 1.4.1, hemos dado un paso más allá implementando la **Arquitectura Híbrida de Identidad**. Toda la deuda técnica de los antiguos cargadores acoplados ha sido eliminada. Ahora, el procesamiento de video se divide en tres roles lógicos principales:

1. **El Explorador (`VideoAnalyzerWithAudio`)**: Un nodo rediseñado con una interfaz ultra-limpia (integrada nativamente con el widget de VideoHelperSuite). Utiliza OpenCV para escanear el vídeo de entrada en busca de rostros nítidos, extraer la pista de audio íntegra y **generar y emitir un Frame de Referencia (Preview Visual)** directamente en el lienzo de ComfyUI.
2. **El Cerebro (`AutoLoopCalculator`)**: Recibe la lista de frames seguros del Explorador y planifica cortes asimétricos e inteligentes. En lugar de dividir el video matemáticamente de forma ciega, prioriza realizar cortes en frames donde el rostro es nítido, manteniendo la coherencia de identidad entre bucles.
3. **El Obrero (`VHS_LoadVideo`)**: El nodo estándar de VideoHelperSuite de ComfyUI ahora se encarga exclusivamente del trabajo pesado: extraer los tensores de vídeo exactos según las órdenes del Cerebro.

## Los Nodos Principales

El sistema se construye alrededor de tres categorías principales:

### 🔁 Loop (Orquestación Autónoma)
1. **🏁 Loop Start (Index) (`SequentialLoopStart`)**: Inicia el bucle, gestiona el índice global y provee el índice actual a los nodos de imagen y vídeo del flujo.
2. **🚀 Loop Trigger (Auto-Queue) (`SequentialLoopTrigger`)**: Se coloca al final del flujo de trabajo. Incrementa el contador y auto-encola el siguiente ciclo mediante un POST a la propia API de ComfyUI (`/prompt`).
   - **Mutador de Semillas:** Escanea el lienzo, localiza nodos con una semilla (`seed` o `noise_seed`) y les inyecta una nueva (32 bits), rompiendo la caché hacia adelante en los samplers.
   - **💉 Inyección Anti-Caché (¡Nuevo en v1.1.0!):** Busca específicamente al nodo `Loop Start` dentro de la carga útil (payload) JSON y le **inyecta forzosamente el nuevo índice**. Esto rompe el infame "caché inverso" (bottom-up) de ComfyUI que congelaba los nodos iniciales durante el Auto-Queue, garantizando un avance ininterrumpido.

### 🖼️ Image (Memoria de Sesión)
3. **📥 Session Image Receiver (`SessionImageReceiver`)**: Proporciona la imagen inicial o la última generada del ciclo anterior, detectando inteligentemente el inicio de una sesión en la memoria RAM.
4. **📤 Session Image Sender (`SessionImageSender`)**: Extrae la última imagen del lote y la asegura en la memoria del sistema para el siguiente ciclo.
   - **💾 Guardado de Keyframes (¡Nuevo en v1.1.0!):** Ahora recibe el índice actual y realiza un volcado de seguridad en el disco duro, guardando progresivamente `keyframe_XXX.png` en cada ciclo para prevenir pérdidas de datos.

### 🎞️ Video (Ensamblaje y Validación)
5. **🕵️ Video Analyzer + Audio (`VideoAnalyzerWithAudio`)**: Es el "Explorador" de la máquina. Escanea el vídeo usando OpenCV para detectar frames con rostros nítidos, extrae la pista de audio íntegra de forma pura mediante Torchaudio, y genera un visual **Preview del Frame de Referencia** en su propia interfaz. Emite dicho frame de referencia en formato de imagen (IMAGE) para el resto del flujo de trabajo.
6. **📊 Auto Loop Calculator (`AutoLoopCalculator`)**: Es el "Cerebro". Recibe la información del Explorador y calcula los cortes de los frames (chunk, skip) de forma asimétrica. Si se le pasa la lista de `safe_faces_list`, forzará los cortes en fotogramas donde haya rostros reconocibles para no romper la fluidez.
7. **🎞️ Incremental Auto-Stitcher (`IncrementalVideoStitcher`)**: Archiva progresivamente los tensores generados en el disco duro y los ensambla de forma segura al final de todos los ciclos.
   - **🧠 Cero OOM:** Sustituye las acumulaciones en memoria por guardados temporales en disco (`.pt`), borrando la RAM de inmediato para poder procesar vídeos infinitos sin colapsar el sistema.
   - **🎵 Passthrough de Audio:** Alimenta directamente el audio original hacia el archivo ensamblado en el último ciclo (devolviendo `None` en los ciclos intermedios para ahorrar recursos).

## Configuración y Uso

### Prerrequisitos
- **VideoHelperSuite (VHS)**: **Recomendado/Estándar** para el nodo "Obrero" de extracción (`VHS_LoadVideo`).
- **OpenCV (`opencv-python`)**: Necesario para que el Explorador (`VideoAnalyzerWithAudio`) escanee rostros nítidos. Si no está instalado, la detección de rostros se desactivará de forma segura.
- **FFmpeg**: Debe estar instalado y disponible en el PATH del sistema para manejar procesos subyacentes de vídeo.
- **Torchaudio**: (Generalmente incluido en los entornos ComfyUI) es necesario para extraer la pista de audio fuente original de forma pura en el nodo Explorador.

### Instalación
1. Ve a la carpeta `custom_nodes` de ComfyUI.
2. Clona este repositorio: `git clone https://github.com/your-repo/ComfyUI-Sequential-Batcher.git`
3. Instala los requerimientos adicionales si es necesario (ej. `pip install opencv-python`).
4. Reinicia ComfyUI.

### Cómo Conectar la Arquitectura Híbrida de Identidad
1. **El Explorador (`🕵️ Video Analyzer + Audio`)**: Coloca este nodo al principio de tu flujo. Sube tu vídeo aquí.
2. **El Cerebro (`📊 Auto Loop Calculator`)**: Conecta la salida `total_frames` del Explorador a la entrada `source_frame_count` del Cerebro. Conecta también la salida `safe_faces_list`. Conecta el `current_loop_index` desde el nodo `🏁 Loop Start`.
3. **El Obrero (`VHS_LoadVideo`)**: Haz clic derecho sobre este nodo estándar de ComfyUI y selecciona **Convert Widget to Input -> video**.
   - Conecta la salida `video_name` del Explorador a la nueva entrada `video` del Obrero.
   - Conecta las salidas `chunk_frames`, `skip_frames` y `select_every_nth` del Cerebro al Obrero.
4. **Conectando el Audio:** Saca un cable de la salida `source_audio` del Explorador y conéctalo directamente al puerto `audio` azul de tu `🎞️ Incremental Auto-Stitcher`.
5. **El Final:** Añade el nodo `🚀 Loop Trigger (Auto-Queue)` al final. Conecta la salida de imagen o audio de tu `Incremental Auto-Stitcher` en la entrada `trigger_dependency`.
6. **Ejecución:** Pulsa "Queue Prompt" **1 sola vez** (no marques la casilla Auto Queue). El lote 0 arranca, el Explorador analiza el vídeo una vez, pasa los cortes al Cerebro, y el Obrero ejecuta los tensores iterativamente mientras la Inyección Anti-Caché fluye ciclo tras ciclo.

---
*Creado para llevar los límites de la automatización en ComfyUI un paso más allá.*