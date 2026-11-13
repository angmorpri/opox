# Runbook

Pasos, en orden, para reconstruir `data/interim/` y `data/processed/` desde cero a partir
de `data/raw/` ([D002]).

Cada paso indica:

- **Entrada / Salida**: rutas afectadas.
- **Ejecutor**: código (`opox ...`), agente (con referencia a sus instrucciones) o manual.
- **Validación**: comando `opox <paso> check ...` u otro criterio.

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
- **Ejecución**: `uv run opox rules extract` muestra las instrucciones para el agente,
  con las convocatorias nuevas (todas con `--force`).
- **Validación**: `uv run opox rules check`.

### 3. Extracción de preguntas y contextos por examen ([D009], [D005])

> 👨🏻‍💻 PROGRAMA

- **Entrada**: `raw/C2_AGE/tests/<exam_id>T.pdf` y `<exam_id>R.pdf`;
  `processed/C2_AGE/rules.json`.
- **Salida**: `processed/C2_AGE/questions.json`, modelo `ExamCollection`.
- **Ejecución**:
  - Para las preguntas: `uv run opox tests extract questions`.
  - Para los contextos: `uv run opox tests extract contexts`.
  - O ambos, en orden: `uv run opox tests extract all`.
- **Validación**: `uv run opox tests check questions`. Si no se han revisado
  manualmente los contextos (siguiente paso), lanzará una advertencia.

### 4. Revisión de contextos

> ✍️ MANUAL

- **Entrada**: `processed/C2_AGE/contexts/<exam_id>_p<página>.png` e
  `interim/C2_AGE/contexts.csv`.
- **Salida**: N/A.
- **Ejecución**: Revisión manual de la hoja y los recortes.
- **Validación**: `uv run opox tests check contexts`.

### 5. Asignación de contextos a preguntas ([D005])

> 👨🏻‍💻 PROGRAMA

- **Entrada**: `interim/C2_AGE/contexts.csv`, `processed/C2_AGE/contexts/` y
  `processed/C2_AGE/questions.json`.
- **Salida**: `processed/C2_AGE/questions.json`, con el campo `context` asignado.
- **Ejecución**: código, `uv run opox tests add contexts`. Repetir tras cada cambio en
  la hoja o nueva extracción de preguntas.
- **Validación**: `uv run opox tests check questions`.

### 6. Identificación de duplicados ([D011])

> 👨🏻‍💻 PROGRAMA

- **Entrada**: `processed/C2_AGE/questions.json`, con los contextos asignados.
- **Salida**: `interim/C2_AGE/duplicates.json`, `dup_contexts.csv` y `dup_check.csv`,
  con sus guías `.md`.
- **Ejecución**: código, `uv run opox bank extract duplicates`. Repetir tras cada
  nueva extracción de preguntas o asignación de contextos: conserva las decisiones
  tomadas.
- **Validación**: `uv run opox bank check duplicates`. Fallará mientras queden
  contextos por revisar (siguiente paso).

### 7. Revisión de contextos de duplicados

> ✍️ MANUAL

- **Entrada**: `interim/C2_AGE/dup_contexts.csv` y su guía `dup_contexts.md`.
- **Salida**: `interim/C2_AGE/dup_contexts.csv`, con `same` completo.
- **Ejecución**: Para cada par de recortes, `y` si son el mismo contexto, `n` si no.
  Obligatorio.
- **Validación**: `uv run opox bank check duplicates`.

### 8. Revisión de posibles duplicados [OPCIONAL]

> ✍️ MANUAL + 👨🏻‍💻 PROGRAMA

- **Entrada**: `interim/C2_AGE/dup_check.csv` y su guía `dup_check.md`.
- **Salida**: `interim/C2_AGE/duplicates.json`, con los grupos `manual`.
- **Ejecución**: Para cada par, `y` si es la misma pregunta, `n` si no; las filas en
  blanco se ignoran. Después, código, `uv run opox bank add duplicates`. Si surgen
  nuevos pares de contextos, volver al paso 7.
- **Validación**: `uv run opox bank check duplicates`.

### 9. Generación del banco de preguntas ([D010])

> 👨🏻‍💻 PROGRAMA

- **Entrada**: `processed/C2_AGE/questions.json` e `interim/C2_AGE/duplicates.json`,
  `dup_contexts.csv` y `dup_check.csv`.
- **Salida**: `processed/C2_AGE/bank.json`, modelo `QuestionBank`.
- **Ejecución**: código, `uv run opox bank make`. Se regenera siempre desde cero.
- **Validación**: el propio comando, que valida los duplicados como `opox bank
  check duplicates` y exige al menos 3 distractores por pregunta.

### 10. Extracción de categorías ([D012])

> 👨🏻‍💻 PROGRAMA

- **Entrada**: `processed/C2_AGE/rules.json`.
- **Salida**: `processed/C2_AGE/categories.json`, modelo `CategoryCollection`.
- **Ejecución**: código, `uv run opox categories extract`. Sólo depende de las bases,
  así que puede ejecutarse en cualquier momento tras el paso 2. Es incremental por
  convocatoria; `--force` lo reconstruye.
- **Validación**: el propio comando, que falla si algún bloque no puede asignarse a una
  categoría, y `uv run opox categories check`.
