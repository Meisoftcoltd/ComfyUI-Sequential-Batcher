# ComfyUI Sequential Batcher (v1.0.0)

Una suite altamente especializada de nodos personalizados para ComfyUI diseñada para el **Auto-Encolado Recursivo (Recursive Self-Queuing)** y el procesamiento secuencial autónomo. Esta arquitectura minimiza el uso de VRAM procesando tareas pesadas (como la generación de vídeo) de forma secuencial, lote por lote, orquestadas completamente desde dentro del propio grafo.

> **Read in English:** [README.md](README.md)

## La Arquitectura "Motor de Fórmula 1"

A partir de la versión 1.0.0, este repositorio ha pivotado exclusivamente hacia la arquitectura de bucles secuenciales autónomos y memoria global. Toda la deuda técnica de los antiguos nodos (lotes, secuencias, depuración) ha sido eliminada, dejando un código base limpio y fácil de mantener enfocado en los 6 fantásticos.

## Los 6 Nodos Principales

El sistema se construye alrededor de tres categorías principales:

### 🔁 Loop (Orquestación Autónoma)
1. **🏁 Loop Start (Index) (`SequentialLoopStart`)**: Inicia el bucle, gestiona el índice global y provee el índice actual a los nodos de imagen y vídeo del flujo.
2. **🚀 Loop Trigger (Auto-Queue) (`SequentialLoopTrigger`)**: Se coloca al final del flujo de trabajo. Incrementa el contador y, si es necesario, auto-encola el siguiente ciclo mediante un POST a la propia API de ComfyUI (`/prompt`), inyectando el lienzo actual en los parámetros ocultos.

### 🖼️ Image (Memoria de Sesión)
3. **📥 Session Image Receiver (`SessionImageReceiver`)**: Proporciona la imagen inicial o la última generada del ciclo anterior, detectando inteligentemente el inicio de una sesión.
4. **📤 Session Image Sender (`SessionImageSender`)**: Extrae, guarda en la memoria global y muestra en la interfaz el último fotograma de un lote de vídeo, para que el receptor del siguiente ciclo lo utilice.

### 🎞️ Video (Ensamblaje y Validación)
5. **🛡️ Wan Frame Validator (`WanFrameValidator`)**: Valida y corrige el número objetivo de fotogramas para asegurar que encajen en la fórmula `4k+1` requerida por modelos específicos (ej. Wan).
6. **🎞️ Incremental Auto-Stitcher (`IncrementalVideoStitcher`)**: Ensambla secuencialmente los fragmentos de vídeo generados en la sesión actual utilizando FFmpeg, leyendo directamente las rutas desde las entradas nativas `VHS_FILENAMES`.

## Configuración y Uso

### Prerrequisitos
- **FFmpeg**: Debe estar instalado y disponible en el PATH del sistema para que el `Incremental Auto-Stitcher` funcione correctamente.

### Instalación
1. Ve a la carpeta `custom_nodes` de ComfyUI.
2. Clona este repositorio: `git clone https://github.com/your-repo/ComfyUI-Sequential-Batcher.git`
3. Reinicia ComfyUI.

### Cómo Conectar tu Nueva Máquina Autónoma
1. **El Inicio:** Añade el nodo `🏁 Loop Start (Index)`. Conecta su salida `current_loop_index` a las entradas de índice de tu `SessionImageReceiver` y tu `Incremental Auto-Stitcher`. Asegúrate de que su interruptor `reset_loop` está en `False`.
2. **El Final:** Añade el nodo `🚀 Loop Trigger (Auto-Queue)`. Crucial: Conecta la salida de texto (`final_video_path`) de tu `Incremental Auto-Stitcher` en la entrada `trigger_dependency`. Esto obliga al trigger a esperar a que el vídeo se haya guardado físicamente antes de disparar. Configura la cantidad de lotes que quieres en `target_loops`.
3. **Ejecución:** **Ya no tienes que marcar la casilla "Auto Queue" nunca más.** Pulsa "Queue Prompt" **1 sola vez**. El lote 0 arranca y, al llegar al final, el nodo `Trigger` envía una señal invisible al servidor. Verás que en el menú de ComfyUI aparece mágicamente el lote pendiente 1. Arranca el lote 1, lee la memoria perfecta y repite el proceso hasta llegar al target, ensambla el vídeo y se apaga automáticamente.

---
*Creado para llevar los límites de la automatización en ComfyUI un paso más allá.*