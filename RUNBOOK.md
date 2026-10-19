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

- **Entrada**: `raw/C2_AGE/rules/<id_convocatoria>.pdf`.
- **Salida**: `interim/C2_AGE/check_rules.csv` (formato en `README.md`, `opox check rules`).
- **Ejecutor**: manual. Se cuentan los temas de cada bloque del programa, sin el psicotécnico.
- **Validación**: no aplica; es la referencia del paso 2.

### 2. Extracción de las bases de convocatoria ([D008])

- **Entrada**: `raw/C2_AGE/rules/<id_convocatoria>.pdf`.
- **Salida**: `processed/C2_AGE/rules.json`, conforme a `CallRulesCollection`.
- **Ejecutor**: agente. Instrucciones:
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

### 3. Extracción de preguntas por examen ([D009])

- **Entrada**: `raw/C2_AGE/tests/<exam_id>T.pdf` y `<exam_id>R.pdf`;
  `processed/C2_AGE/rules.json`.
- **Salida**: `processed/C2_AGE/questions.json`.
- **Ejecutor**: código, `uv run opox extract questions`. Revisar los puntos `REVIEW`.
- **Validación**: `uv run opox check questions`. El aviso de contextos pendientes se
  resuelve en los pasos de contextos ([D005]).

### 4. Contextos de preguntas ([D005])

- **Entrada**: `raw/C2_AGE/tests/<exam_id>T.pdf`; `processed/C2_AGE/rules.json`.
- **Salida**: `processed/C2_AGE/contexts/<exam_id>_p<página>.png` e
  `interim/C2_AGE/contexts.csv`.
- **Ejecutor**: código, `uv run opox extract contexts`, y revisión manual de la hoja y
  los recortes. Los rangos marcados como estimados (`REVIEW`) sólo cubren la página del
  contexto y pueden quedarse cortos si las preguntas continúan en la siguiente.
- **Validación**: `uv run opox check contexts`.
