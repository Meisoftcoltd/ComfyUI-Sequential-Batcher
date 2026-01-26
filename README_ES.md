# 🔁 ComfyUI Sequential Batcher & Video Loop Master (Beta v0.9.2)

> [!IMPORTANT]
> Esta versión se encuentra actualmente en fase **BETA**. Hemos renombrado el proyecto de "Job Iterator" a **Sequential Batcher** para reflejar mejor su propósito: procesar lotes uno a uno para ahorrar VRAM.

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
- **BATCH (Lote, anteriormente JOB)**: Una colección estructurada de "pasos". Cada paso tiene **Atributos** con nombre.
- **Iteración**: La magia ocurre en nodos como `Batch To List`, `Image Batch To List` o `Latent Batch To List`. Cuando ComfyUI detecta una salida tipo "Lista" de estos nodos, ejecuta todos los nodos conectados a continuación una vez por cada elemento de la lista.

---

## 🎞️ Flujo de Vídeo (Wan2.2 / LTX-Video / Modelos Futuros)

Los modelos de vídeo generan muchos fotogramas que pueden superar fácilmente los 24GB de VRAM.
1. **Split (Dividir)**: Usa `Latent Batch To List` para convertir tu latente de vídeo en una lista de fotogramas individuales.
2. **Process (Procesar)**: Conecta a tu KSampler o VAE Decoder. ComfyUI procesará el Fotograma 1, luego el 2, luego el 3... ahorrando memoria.
3. **Gather (Reunir)**: Usa `Latent List To Batch` (o `Image List To Batch` si decodificaste primero) para reconstruir el lote completo de vídeo para guardarlo.

---

## 🔢 Referencia Detallada de Nodos

### Categoría Bucles (`🔁 Sequential Batcher/Loop`)
- **🔁 Sequential Loop Index**: La forma más sencilla de iniciar un bucle.
  - *Entrada*: `count` (Cuántas veces ejecutar).
  - *Salida*: `index` (0, 1, 2...). Útil para semillas (seeds) o selección de elementos.
- **🔁 Repeat**: Toma cualquier entrada y la repite N veces.
  - *Entrada*: `input` (Cualquiera), `count` (INT).
  - *Salida*: `output` (Lista de la misma entrada repetida).

### Categoría Lote (`🔁 Sequential Batcher/Job`)
- **🛠️ Make Batch**: Convierte una secuencia en un objeto "Batch".
  - *Entrada*: `sequence` (Los datos), `name` (El nombre del atributo, ej: "cfg_scale").
- **🖇️ Combine Batches**: Fusiona varios lotes.
  - *Modos*: `zip` (por parejas) o `product` (todas las combinaciones posibles).
- **🔄 Batch To List**: **CRÍTICO**. Convierte un Lote en un flujo de atributos que activa el bucle secuencial.
- **📥 Get Attribute**: Extrae un valor específico del paso actual del lote por su nombre.

### Categoría Imagen y Latente (`🔁 Sequential Batcher/Image` & `/Latent`)
- **🖼️ Image Batch To List**: Divide un tensor [N,H,W,C] en N imágenes separadas.
- **🖼️ Image List To Batch**: Reconstruye un lote a partir de imágenes iteradas.
- **🎞️ Latent Batch To List**: Divide latentes de vídeo fotograma a fotograma para un procesamiento seguro en VRAM.
- **🎞️ Latent List To Batch**: Une fotogramas individuales de nuevo en un lote latente de vídeo.
- **⏳ Progress Bar**: Genera un indicador visual de progreso.

---

## 💡 Consejos Pro
- Usa **🖇️ Combine Batches** en modo `product` para crear "XY Plots" (ej: probar cada Prompt contra cada valor de CFG).
- Usa **🔍 Model Finder** para iterar automáticamente a través de una carpeta de LoRAs o Checkpoints.
- Combina con **⌨️ Interact** para pausar tu flujo en un fotograma específico e inspeccionar variables en la terminal.
