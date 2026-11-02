# Runbook

Pasos, en orden, para reconstruir `data/interim/` y `data/processed/` desde cero a partir
de `data/raw/` ([D002]).

Cada paso indica:

- **Entrada / Salida**: rutas afectadas.
- **Ejecutor**: código (`opox ...`), agente (con referencia a sus instrucciones) o manual.
- **Validación**: comando `opox check ...` u otro criterio.

Si parte de una fuente no puede leerse con herramientas estándar, el camino preferente es
completarla manualmente: el paso termina mostrando la lista de puntos pendientes.


## C2_AGE

### 1. Recuento manual de temas de las bases

> ✍️ MANUAL

- **Entrada**: `raw/C2_AGE/rules/<id_convocatoria>.pdf`.
- **Salida**: `interim/C2_AGE/check_rules.csv`.
- **Ejecución**: Se cuentan los temas de cada bloque del programa, sin el psicotécnico.
- **Validación**: N/A.

### 2. Extracción de las bases de convocatoria ([D008])

> 🤖 AGENTE

- **Entrada**: `raw/C2_AGE/rules/<id_convocatoria>.pdf`.
- **Salida**: `processed/C2_AGE/rules.json`, modelo `CallRulesCollection`.
- **Ejecución**: Con las siguientes instrucciones:
  - Formato del examen (partes, secciones, reserva, penalización, duración, versiones):
    transcripción a partir del apartado "Proceso de selección" o "Fase de oposición".
  - Psicotécnico: bloque `PSICO` con las aptitudes citadas ("administrativas, numéricas
    o verbales"), sólo en convocatorias que lo incluyan.
  - Programa: extracción del texto con `pdftotext -layout`, eliminando cabeceras y
    números de página, y uniendo las líneas de cada tema. Revisar los temas contra los
    de otras convocatorias para detectar texto perdido.
  - Particularidad conocida: en 2024I (tema 3) y 2024L (tema II.7), una línea visible en
    el PDF no está en su capa de texto y debe completarse manualmente.
- **Validación**: `uv run opox check rules`.

### 3. Extracción de preguntas y contextos por examen ([D009], [D005])

> 👨🏻‍💻 PROGRAMA

- **Entrada**: `raw/C2_AGE/tests/<exam_id>T.pdf` y `<exam_id>R.pdf`;
  `processed/C2_AGE/rules.json`.
- **Salida**: `processed/C2_AGE/questions.json`, modelo `ExamCollection`.
- **Ejecución**:
  - Para las preguntas: `uv run opox extract questions`.
  - Para los contextos: `uv run opox extract contexts`.
- **Validación**: `uv run opox check questions`. Si no se han revisado manualmente
  los contextos (siguiente paso), lanzará una advertencia.

### 4. Revisión de contextos

> ✍️ MANUAL

- **Entrada**: `processed/C2_AGE/contexts/<exam_id>_p<página>.png` e
  `interim/C2_AGE/contexts.csv`.
- **Salida**: N/A.
- **Ejecución**: Revisión manual de la hoja y los recortes.
- **Validación**: `uv run opox check contexts`.

### 5. Asignación de contextos a preguntas ([D005])

> 👨🏻‍💻 PROGRAMA

- **Entrada**: `interim/C2_AGE/contexts.csv`, `processed/C2_AGE/contexts/` y
  `processed/C2_AGE/questions.json`.
- **Salida**: `processed/C2_AGE/questions.json`, con el campo `context` asignado.
- **Ejecutor**: código, `uv run opox add contexts`. Repetir tras cada nueva extracción
  de preguntas.
- **Validación**: `uv run opox check questions`.
