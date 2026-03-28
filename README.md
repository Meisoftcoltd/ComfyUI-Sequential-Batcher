# ComfyUI Sequential Batcher (v1.1.0)

Una suite altamente especializada de nodos personalizados para ComfyUI diseñada para el **Auto-Encolado Recursivo (Recursive Self-Queuing)** y el procesamiento secuencial autónomo. Esta arquitectura minimiza el uso de VRAM procesando tareas pesadas (como la generación de vídeo) de forma secuencial, lote por lote, orquestadas completamente desde dentro del propio grafo.

> **Read in English:** [README_EN.md](README_EN.md)

## La Arquitectura "Motor de Fórmula 1"

A partir de la versión 1.0.0, este repositorio ha pivotado exclusivamente hacia la arquitectura de bucles secuenciales autónomos y memoria global. Toda la deuda técnica de los antiguos nodos (lotes, secuencias, depuración) ha sido eliminada, dejando un código base limpio y fácil de mantener enfocado en los 6 fantásticos.

En la **v1.1.0**, hemos introducido capacidades de guardado a disco progresivo, soporte para multiplexado de audio y un hackeo profundo a nivel de JSON para vencer la agresiva caché de ComfyUI.

## Los 6 Nodos Principales

El sistema se construye alrededor de tres categorías principales:

### 🔁 Loop (Orquestación Autónoma)
1. **🏁 Loop Start (Index) (`SequentialLoopStart`)**: Inicia el bucle, gestiona el índice global y provee el índice actual a los nodos de imagen y vídeo del flujo. Ahora también acepta el parámetro `total_loops` para mostrar un rastreo detallado del progreso (`Ciclo X / Y`) en la consola.
2. **🚀 Loop Trigger (Auto-Queue) (`SequentialLoopTrigger`)**: Se coloca al final del flujo de trabajo. Incrementa el contador y auto-encola el siguiente ciclo mediante un POST a la propia API de ComfyUI (`/prompt`).
   - **Mutador de Semillas:** Escanea el lienzo, localiza nodos con una semilla (`seed` o `noise_seed`) y les inyecta una nueva (32 bits), rompiendo la caché hacia adelante en los samplers.
   - **💉 Inyección Anti-Caché (¡Nuevo en v1.1.0!):** Busca específicamente al nodo `Loop Start` dentro de la carga útil (payload) JSON y le **inyecta forzosamente el nuevo índice**. Esto rompe el infame "caché inverso" (bottom-up) de ComfyUI que congelaba los nodos iniciales durante el Auto-Queue, garantizando un avance ininterrumpido.

### 🖼️ Image (Memoria de Sesión)
3. **📥 Session Image Receiver (`SessionImageReceiver`)**: Proporciona la imagen inicial o la última generada del ciclo anterior, detectando inteligentemente el inicio de una sesión en la memoria RAM. Al igual que el inicio del bucle, ahora monitoriza e imprime el progreso total (`total_loops`).
4. **📤 Session Image Sender (`SessionImageSender`)**: Extrae la última imagen del lote y la asegura en la memoria del sistema para el siguiente ciclo. También reporta el estado actual en relación al total de bucles en consola.
   - **💾 Guardado de Keyframes (¡Nuevo en v1.1.0!):** Ahora recibe el índice actual y realiza un volcado de seguridad en el disco duro, guardando progresivamente `keyframe_XXX.png` en cada ciclo para prevenir pérdidas de datos.

### 🎞️ Video (Ensamblaje y Validación)
5. **🛡️ Wan Frame Validator (`WanFrameValidator`)**: Valida y corrige el número objetivo de fotogramas para asegurar que encajen en la fórmula `4k+1` requerida por modelos específicos (ej. Wan). A través de la entrada obligatoria `current_loop_index`, calcula e indica automáticamente cuántos fotogramas (`skip_frames`) debe saltar el cargador de vídeo por iteración.
6. **🎞️ Incremental Auto-Stitcher (`IncrementalVideoStitcher`)**: Archiva progresivamente los tensores generados en el disco duro y los ensambla de forma segura al final de todos los ciclos.
   - **🧠 Cero OOM (¡Nuevo!):** Sustituye las acumulaciones en memoria por guardados temporales en disco (`.pt`), borrando la RAM de inmediato para poder procesar vídeos infinitos sin colapsar el sistema. Al desactivar `INPUT_IS_LIST`, maneja tensores puros eficientemente.
   - **🎵 Passthrough de Audio (¡Nuevo!):** Alimenta directamente el audio original hacia el archivo ensamblado en el último ciclo (devolviendo `None` en los ciclos intermedios para ahorrar recursos).
7. **🎥 Load Video + Source Audio (`LoadVideoWithSourceAudio`)**: (¡Nuevo!) Utilizando un envoltorio de evaluación diferida (Lazy Evaluation Wrapper), este nodo extrae dinámicamente los parámetros de la clase original de VHS (`VHS_LoadVideo`) evitando fallos de carga inicial. Funciona exactamente igual, pero extrae y expone de manera segura la pista de audio original **completa**, junto al **primer fotograma** (`first_frame`) como una salida independiente.

## Configuración y Uso

### Prerrequisitos
- **VideoHelperSuite (VHS)**: **Obligatorio** para que el nodo `Load Video + Source Audio` funcione. Al heredar de su clase base, si VHS no está instalado en tu entorno de ComfyUI, este nodo no se cargará.
- **FFmpeg**: Debe estar instalado y disponible en el PATH del sistema para manejar procesos subyacentes de vídeo.
- **Torchaudio**: (Generalmente incluido en los entornos ComfyUI) es necesario para extraer la pista de audio fuente original de forma pura.

### Instalación
1. Ve a la carpeta `custom_nodes` de ComfyUI.
2. Clona este repositorio: `git clone https://github.com/your-repo/ComfyUI-Sequential-Batcher.git`
3. Reinicia ComfyUI.

### Cómo Conectar tu Nueva Máquina Autónoma
1. **El Inicio:** Añade el nodo `🏁 Loop Start (Index)`.
   - Conecta su salida `current_loop_index` a las entradas de índice de tu `SessionImageReceiver`, `SessionImageSender`, y tu `Incremental Auto-Stitcher`. *¡No olvides conectar el Sender para el guardado de los keyframes!*
   - Asegúrate de que su interruptor `reset_loop` está en `False`.
2. **Conectando el Audio (Opcional):** Si tu flujo tiene sonido, saca un cable de la salida de audio de tu nodo inicial (ej. `VHS_LoadVideo`) y conéctalo al puerto `audio` azul de tu `Incremental Auto-Stitcher`.
3. **El Final:** Añade el nodo `🚀 Loop Trigger (Auto-Queue)`. Crucial: Conecta la salida de texto (`final_video_path`) de tu `Incremental Auto-Stitcher` en la entrada `trigger_dependency`. Esto obliga al trigger a esperar a que el vídeo se haya guardado físicamente antes de disparar. Configura la cantidad de lotes que quieres en `target_loops`.
4. **Ejecución:** **Ya no tienes que marcar la casilla "Auto Queue" nunca más.** Pulsa "Queue Prompt" **1 sola vez**. El lote 0 arranca y, al llegar al final, el nodo `Trigger` envía una señal invisible al servidor. Gracias a la Inyección Anti-Caché, la caché se destruye en cada iteración y el progreso fluye hasta completar tu vídeo.

---
*Creado para llevar los límites de la automatización en ComfyUI un paso más allá.*