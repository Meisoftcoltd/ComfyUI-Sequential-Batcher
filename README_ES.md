# 🔁 ComfyUI Sequential Batcher & Video Loop Master (Beta v0.9.3)

> [!IMPORTANT]
> Esta versión se encuentra actualmente en fase **BETA**. Hemos completado la transición de la terminología de "Job" a **Batch** (Lote) para alinearnos con los estándares de ComfyUI y el nombre del proyecto.

La herramienta definitiva para crear flujos de trabajo iterativos complejos y procesamiento de vídeo fotograma a fotograma en ComfyUI. Diseñada para manejar tareas pesadas (como generación de vídeo de alta resolución con Wan2.2 o LTX Video) sin colapsar tu GPU, utilizando bucles secuenciales inteligentes en lugar de procesamiento por lotes masivo que agota la VRAM.

## 🚀 ¿Por qué usar esto?

El procesamiento por lotes (batch) estándar de ComfyUI procesa todo a la vez (tensores 4D). Para vídeo o lotes grandes, esto provoca errores de **Falta de Memoria (OOM)**.
**Sequential Batcher** te permite "dividir" estas tareas y procesarlas **una a una** (secuencialmente) dentro de una sola ejecución de "Queue Prompt", para luego "reunir" los resultados en un solo lote o archivo de vídeo.

---

## 🛠️ Instalación

1. Clona este repositorio en `custom_nodes/comfyui-sequential-batcher`.
2. Reinicia ComfyUI.
3. Las dependencias (`torch`, `numpy`) se gestionarán automáticamente si usas ComfyUI Manager gracias al archivo `requirements.txt`.

---

## 📖 Conceptos Clave

- **SEQUENCE (Secuencia)**: Una lista simple de valores (números, textos, etc.).
- **BATCH (Lote)**: Una colección estructurada de "pasos". Cada paso tiene **Atributos** con nombre.
- **Iteración**: La magia ocurre en nodos como `Batch To List`, `Image Batch To List` o `Latent Batch To List`. Cuando ComfyUI detecta una salida tipo "Lista" de estos nodos, ejecuta todos los nodos conectados a continuación una vez por cada elemento de la lista.

---

## 🎞️ Flujo de Vídeo (Wan2.2 / LTX-Video / Modelos Futuros)

Los modelos de vídeo generan muchos fotogramas que pueden superar fácilmente los 24GB de VRAM.
1. **Split (Dividir)**: Usa `Latent Batch To List` para convertir tu latente de vídeo en una lista de fotogramas individuales.
2. **Process (Procesar)**: Conecta a tu KSampler o VAE Decoder. ComfyUI procesará el Fotograma 1, luego el 2, luego el 3... ahorrando memoria.
3. **Gather (Reunir)**: Usa `Latent List To Batch` (o `Image List To Batch` si decodificaste primero) para reconstruir el lote completo de vídeo para guardarlo.
4. **Stitch (Unir con VHS)**: Para unir chunks pesados de vídeo secuencialmente:
   - *Opción A (Matemática)*: `Range` -> `MakeBatch` (atributo: "skip_frames") -> `BatchToList` -> `GetAttributeInt` (nombre: "skip_frames") conectado a `VHS_LoadVideo`.
   - *Opción B (Por CSV)*: `LoadCSV` (con una columna `skip_frames`) -> `BatchToList` -> `GetAttributeInt`.
   - Conecta la salida de `VHS_VideoCombine` (específicamente la salida `VHS_FILENAMES`) al nodo **FFmpeg Video Stitcher** (`video_paths`). ¡El Stitcher esperará a que terminen todos los chunks y los unirá automáticamente!

> [!WARNING]
> **Prevención OOM (Aviso de Memoria):** Aunque `BatchToList` soluciona el paso de datos, a nivel de VRAM de PyTorch, se debe seguir gestionando la memoria. Es altamente recomendable usar el nodo **easy cleanGpuUsed** (o similar) después del decodificador (VAE) en cada ciclo del Batch. Sin la liberación manual de VRAM en cada iteración, el bucle secuencial acumulará basura en la tarjeta gráfica y eventualmente provocará un error de "Out of Memory".

---

## 🔢 Referencia Detallada de Nodos

### 🔄 Categoría Bucles (`🔁 Sequential Batcher/Loop`)
- **🔁 Sequential Loop Index**: La forma más sencilla de iniciar un bucle.
  - *Entrada*: `count` (Cuántas veces ejecutar).
  - *Salida*: `index` (0, 1, 2...). Útil para semillas (seeds) o selección de elementos.
- **🔁 Repeat**: Toma cualquier entrada y la repite N veces.
  - *Entrada*: `input` (Cualquiera), `count` (INT).
  - *Salida*: `output` (Lista de la misma entrada repetida).

### 🛠️ Categoría Lote (`🔁 Sequential Batcher/Batch`)
- **📂 Load CSV**: Carga un archivo CSV como un Lote (Batch). Ahora incluye una vista previa de la tabla en el flujo de trabajo.
  - *Entrada*: `path` (Ubicación del archivo), `delimiter`, `quotechar`.
  - *Entrada Opcional*: `index` (Para elegir una fila específica).
  - *Salida*: `batch` (La lista completa), `current_attributes` (Diccionario de la fila seleccionada), `count` (Total de filas).
- **📊 Preview Batch**: Muestra una tabla del contenido del lote en el flujo de trabajo.
  - *Entrada*: `batch`, `index` (Resaltar fila específica), `max_rows`.
- **🛠️ Make Batch**: Convierte una secuencia en un objeto "Batch".
  - *Entrada*: `sequence` (Los datos), `name` (El nombre del atributo, ej: "cfg_scale").
- **🖇️ Combine Batches**: Fusiona varios lotes.
  - *Modos*: `zip` (por parejas) o `product` (todas las combinaciones posibles).
- **🔄 Batch To List**: **CRÍTICO**. Convierte un Lote en un flujo de atributos que activa el bucle secuencial.
- **📥 Get Attribute**: Extrae un valor específico del paso actual del lote por su nombre.

### 🖼️ Categoría Imagen y Latente (`🔁 Sequential Batcher/Image` & `/Latent`)
- **🖼️ Image Batch To List**: Divide un tensor [N,H,W,C] en N imágenes separadas.
- **🖼️ Image List To Batch**: Reconstruye un lote a partir de imágenes iteradas.
- **🎞️ Latent Batch To List**: Divide latentes de vídeo fotograma a fotograma para un procesamiento seguro en VRAM.
- **🎞️ Latent List To Batch**: Une fotogramas individuales de nuevo en un lote latente de vídeo.
- **⏳ Progress Bar**: Genera un indicador visual de progreso.

### 🎞️ Categoría Vídeo (`🔁 Sequential Batcher/Video`)
- **🎞️ FFmpeg Video Stitcher**: Nodo final en un bucle de vídeo. Espera a que termine todo el lote secuencial y une los fragmentos de vídeo utilizando FFmpeg sin recodificar.
  - *Entrada*: `video_paths` (Lista de VHS_FILENAMES), `output_filename` (Cadena de texto).
  - *Salida*: `final_video_path` (Ruta del vídeo ensamblado).
- **🎞️ Incremental Auto-Stitcher**: Nodo de ensamblaje incremental diseñado específicamente para ciclos de Auto Queue. Se ejecuta inmediatamente después de que cada fragmento es guardado y extrae de manera estricta las rutas `.mp4` del JSON de salida que genera `VHS_FILENAMES`. Mantiene una lista en la memoria de la sesión activa (que se vacía automáticamente al reiniciar ComfyUI) para ensamblar *únicamente* los vídeos generados durante la sesión actual, garantizando inmunidad a archivos viejos o "basura" en el directorio de salida.
  - *Entrada*: `trigger` (JSON/lista de VHS_FILENAMES), `output_filename` (Cadena de texto), `reset_list` (Booleano: actívalo a True en un ciclo para vaciar manualmente la memoria de la sesión y empezar un vídeo nuevo).
  - *Salida*: `final_video_path` (Ruta del vídeo ensamblado incremental).

---

## 💡 Consejos Pro y Casos de Uso

### 📝 Uso de CSV para Prompts y Escenas
Puedes crear un CSV con columnas como `prompt`, `negative_prompt` y `seed`.
1. Usa **📂 Load CSV** para cargar tu archivo.
2. Conecta `batch` a **🔄 Batch To List**.
3. Usa **📥 Get Attribute** para pasar el `prompt` a tu CLIP Text Encode.
4. Cada fila de tu CSV se procesará como un "fotograma" o "trabajo" en la secuencia.

### 🎬 Tiempos de Escena para Vídeo
Si tienes un CSV con `frame_start` y `prompt`, puedes usarlo para cambiar los prompts en puntos específicos de un bucle de generación de vídeo.

### 🧪 XY Plots
Usa **🖇️ Combine Batches** en modo `product` para crear "XY Plots" (ej: probar cada Prompt contra cada valor de CFG).

### 🔍 Iteración Automática de Modelos
Usa **🔍 Model Finder** para iterar automáticamente a través de una carpeta de LoRAs o Checkpoints.
