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

### 5. Asignación de contextos a preguntas ([D005])

- **Entrada**: `interim/C2_AGE/contexts.csv`, `processed/C2_AGE/contexts/` y
  `processed/C2_AGE/questions.json`.
- **Salida**: `processed/C2_AGE/questions.json`, con el campo `context` asignado.
- **Ejecutor**: código, `uv run opox add contexts`. Repetir tras cada nueva extracción
  de preguntas.
- **Validación**: `uv run opox check questions`.

### 6. Deduplicación de respuestas ([D011])

- **Entrada**: `processed/C2_AGE/questions.json`.
- **Salida**: `interim/C2_AGE/dedup_answers.json`, `dedup_answers_review.csv` y
  `dedup_answers_review.md`.
- **Ejecutor**: código y manual. `uv run opox dedup extract answers`; se rellena `group`
  en la hoja, a ciegas y con ayuda de la guía; `uv run opox dedup add answers`.
- **Validación**: `uv run opox dedup check answers`.

### 7. Deduplicación de enunciados ([D011])

- **Entrada**: `processed/C2_AGE/questions.json` e `interim/C2_AGE/dedup_answers.json`.
- **Salida**: `interim/C2_AGE/dedup_stems.json`, `dedup_stems_review.csv` y
  `dedup_stems_review.md`.
- **Ejecutor**: código y manual, como en el paso 6, con `stems`.
- **Validación**: `uv run opox dedup check stems`.

### 8. Deduplicación de contextos ([D011])

- **Entrada**: `processed/C2_AGE/questions.json`, `processed/C2_AGE/contexts/` e
  `interim/C2_AGE/dedup_stems.json`.
- **Salida**: `interim/C2_AGE/dedup_contexts.json`, `dedup_contexts_review.csv` y
  `dedup_contexts_review.md`.
- **Ejecutor**: código y manual. `uv run opox dedup extract contexts`; se rellena `same`
  (`y`/`n`) en la hoja, comparando los recortes de la guía;
  `uv run opox dedup add contexts`.
- **Validación**: `uv run opox dedup check contexts`.

Si se repite la extracción de preguntas (paso 3) o de contextos (pasos 4 y 5), o cambian
los grupos de una etapa (pasos 6 a 8), se regeneran las etapas afectadas con
`extract --force`, que conserva las decisiones de los miembros o pares que siguen
existiendo, y se completan los casos nuevos. `uv run opox dedup check all` comprueba
las tres etapas en orden.

### 9. Batería de preguntas ([D010])

- **Entrada**: `processed/C2_AGE/questions.json` e `interim/C2_AGE/dedup_contexts.json`,
  con las tres etapas de deduplicación completas.
- **Salida**: `processed/C2_AGE/bank.json`.
- **Ejecutor**: código, `uv run opox extract bank`. Repetir, con `--force`, tras cualquier
  cambio en los pasos 3 a 8.
- **Validación**: `uv run opox check bank`.
