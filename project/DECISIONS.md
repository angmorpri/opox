# Decisiones

## [D001] Iteración previa

> ACTIVO

Este proyecto ya se llevó a cabo en una iteración previa, sin llegar a resolver la hipótesis.
Todo el código y contenido que no se ha reutilizado se halla en una carpeta temporal `old/`.

Este contenido debe usarse sólo de forma orientativa, nunca como ejemplo o guía. Las
excepciones a esta regla se mencionarán explícitamente.

Esta carpeta se deja fuera del registro de cambios.


## [D002] Estructura de datos

> ACTIVO

La carpeta raíz de datos es `data/`, dividida en tres:

- `raw/`, para las fuentes primarias tal y como se descargan, organizadas y renombradas
  según [D003]. Nunca se editan, ni a mano ni mediante agentes ni mediante código.
- `interim/`, para resultados intermedios que aún requieren transformación.
- `processed/`, para datos estructurados y limpios, listos para su uso.

`interim/` y `processed/` admiten contenido generado por código, por agentes o a mano.
Al no ser regenerables en general, ambas carpetas se mantienen en el control de cambios.

Como criterio general, el código se encarga del trabajo masivo y repetible, y los agentes
o la intervención manual del trabajo puntual, ambiguo o de corrección. Cuando un paso no
lo realiza el código, se acompaña, si es posible, de un comando `opox check` que valide
su resultado frente a datos fiables.

El orden de los pasos para reconstruir los datos desde cero se documenta en `RUNBOOK.md`.

Dentro de cada carpeta, las diferentes oposiciones se organizan por sus identificadores
(por ejemplo, "C2_AGE").


## [D003] Nomenclatura para documentos oficiales de oposiciones

> ACTIVO

Se adoptan las siguientes nomenclaturas para cada tipo de documento:

- ***Bases de convocatoria***: `YYYYT`.
- ***Exámenes y solucionarios***: `YYYYTNMS`.

Donde:

- `YYYY` es el año de la convocatoria tal y como figura en la web oficial de los CGE.
- `T` es el tipo de convocatoria, que puede ser "L" (acceso libre), "I" (promoción interna) o "E" (estabilización de empleo temporal).
- `N` es el llamamiento. **Este campo está obsoleto**: los llamamientos se distinguen ahora mediante `M`. Se mantiene fijo a `0` para no renombrar los archivos existentes, y así debe hacerse también con los nuevos.
- `M` es el modelo. Los exámenes ordinarios serán "A", "B"... Los llamamientos extraordinarios serán "X", "Y"...
- `S` distingue entre "T" para los exámenes y "R" para los solucionarios definitivos.


## [D004] Estructura de código

> ACTIVO

El código utilizado se englobará en un proyecto Python llamado `opox`, gestionado
mediante `uv` y `pyproject.toml`. Su carpeta raíz estará en `src/opox/`.

`opox` deberá disponer de una interfaz por línea de comando desde la que ejecutar cada
una de las funcionalidades principales que se desarrollen.

`README.md` se usará exclusivamente para describir el código y se redactará en inglés.


## [D005] Contextos de preguntas

> ACTIVO

Algunas preguntas dependen de un contexto (imagen, diagrama o tabla). Los contextos son
datos finales, pues se entregarán íntegros a los agentes de resolución.

- **Recortes**: `processed/<oposición>/contexts/<exam_id>_p<página>.png`, donde
  `exam_id` es el código del examen sin el sufijo `T`/`R` ([D003]) y la página sigue la
  numeración del PDF.
- **Hoja de control**: `interim/<oposición>/contexts.csv`, con columnas
  `exam_id, page, first, last`: página del contexto y preguntas primera y última que lo
  requieren (ambas incluidas).

Se asume que cada página contiene, como mucho, un contexto, y que éste aparece antes que
sus preguntas. Así, las preguntas de un contexto son las primeras con números `first` a
`last` que aparecen a partir de su página, lo que resuelve la ambigüedad de la
numeración, que se reinicia en cada parte y en cada bloque de reserva. Ambas premisas
se cumplen en todos los exámenes de C2_AGE y deben revisarse en nuevas oposiciones.

El flujo es el siguiente:

1. `opox extract contexts` detecta los contextos de cada examen (imágenes incrustadas y
   tablas dibujadas), guarda los recortes y genera la hoja de control. Cuando el rango
   de preguntas no es explícito ("N a M."), lo estima limitado a la página del contexto
   y lo marca para revisión. Respeta [D006]: no sobrescribe recortes ni hojas
   existentes; si ya existen, informa de los candidatos no cubiertos.
2. Manualmente, se revisa la hoja y los recortes: se corrigen los erróneos, se añaden los
   que falten y se eliminan los falsos positivos.
3. `opox check contexts` valida la hoja frente a los recortes y las preguntas extraídas.
4. `opox add contexts` asigna a cada pregunta la ruta de su recorte.
5. `opox check questions` verifica que los recortes asignados existen e informa si la
   asignación de contextos está pendiente. Mantener la asignación al día con la hoja es
   responsabilidad de quien la edita: tras cada cambio en la hoja, repetir
   `opox add contexts`.

La hoja y los recortes son la única fuente de verdad. Si se vuelven a extraer las
preguntas, basta con repetir `opox add contexts`.


## [D006] Escritura de datos por código

> ACTIVO

Como `interim/` y `processed/` admiten edición manual y de agentes ([D002]), el código
debe proteger ese trabajo:

- Siempre que sea posible, las operaciones son idempotentes: ejecutarlas de nuevo
  produce el mismo resultado sin alterar lo existente.
- Si una operación fuera a sobrescribir o borrar datos existentes, no lo hace: avisa
  y se detiene.
- Sólo se sobrescribe si se fuerza explícitamente (por ejemplo, con `--force`), y
  aun así se informa de qué se va a modificar.


## [D007] Pydantic v2 para modelos de datos

> ACTIVO

Usaremos Pydantic v2 para el modelado de datos. El código se almacenará en `src/opox/models/`.


## [D008] Modelo de datos para convocatorias

> ACTIVO

De cada **bases de convocatoria** se extrae el formato de examen y el programa. El modelo
se define en `src/opox/models/rules.py` ([D007]), cuyo docstring incluye un diagrama.

Sobre los bloques del programa:

- El **psicotécnico** se considera un bloque propio. Sus temas son las aptitudes que se
  mencionen explícitamente en las bases ("aptitudes administrativas", "aptitudes
  numéricas"...).
- El resto de bloques se toman del programa, a veces numerados ("I", "II") y a veces con
  nombre ("ofimática").
- Los temas se numeran por su posición en el programa, empezando en 1.
- Los identificadores de bloque son internos y transicionales, pues lo relevante será la
  categoría. Regla: el numeral del documento si existe (`"I"`, `"II"`); `"PSICO"` para el
  psicotécnico; `"U"` si el programa no tiene bloques; el nombre en mayúsculas y sin
  tildes si tiene nombre pero no numeral.

La extracción la realiza un agente directamente a `processed/<oposición>/rules.json`,
un único archivo con todas las convocatorias, y se valida con
`opox check rules` frente a un recuento manual de bloques y temas por convocatoria.


## [D009] Modelo de datos para preguntas por examen

> ACTIVO

De cada examen y su solucionario se extraen sus preguntas. El modelo se define en
`src/opox/models/questions.py` ([D007]), organizado por examen
(`ExamCollection` → `Exam` → `Question`), y se almacena en un único
`processed/<oposición>/questions.json`.

- Cada examen se identifica por su código sin el sufijo `T`/`R` ([D003]), p. ej.
  `2025L0A`, y apunta a su convocatoria ([D008]).
- Las preguntas no repiten datos deducibles del examen o la convocatoria (año, tipo,
  fuente).
- Las preguntas anuladas no tienen respuesta (`answer = None`).
- El contexto de cada pregunta se asigna después con `opox add contexts` ([D005]).

La extracción la realiza el código mediante `opox extract questions`, usando
`pdfplumber`. Al terminar, muestra la lista de puntos que requieren revisión o
completarse manualmente. Se valida con `opox check questions`, frente a
`rules.json` y los recortes de contextos.


## [D010] Modelo de datos para la batería de preguntas

> EN DEFINICIÓN, consultar NOTES

La **batería** reúne las preguntas por examen ([D009]) sin duplicados. El modelo se
define en `src/opox/models/bank.py` ([D007]) y se almacena en un único
`processed/<oposición>/bank.json`.

```
BankQuestion
  bank_id: str                  # question_id del representante
  sources: list[str]            # question_id de todas las apariciones
  text: str
  context: PurePosixPath | None
  answer: str
  distractors: list[str]        # pool deduplicado, al menos 3
```

- **Igualdad**: dos preguntas son iguales si enunciado (texto + contexto) y respuesta
  correcta serían iguales para un opositor. El texto se compara sin mayúsculas, tildes
  ni puntuación. Respuesta y opciones, con una normalización conservadora (Unicode,
  comillas, guiones, espacios y punto final), que conserva tildes, mayúsculas y
  puntuación para no confundir opciones de preguntas de ortografía.
- **Representante**: la aparición más reciente (año de convocatoria y, a igualdad,
  `exam_id`). Su texto y contexto son los canónicos y su `question_id` es el `bank_id`,
  estable aunque se regenere la batería.
- **Distractores**: unión de los de todas las versiones, deduplicados tras normalizar.
  Al montar un examen se eligen 3 al azar y se mezclan con la respuesta.
- Las preguntas **anuladas** se excluyen. Las **obsoletas** se incluyen, pues aún no se
  detectan (ver "Validez temporal" en `NOTES.md`).
- No se contemplan opciones fijas (p. ej. "a y b son correctas"): en C2_AGE no hay
  ningún caso en el que mezclar distractores rompa una pregunta. Se revisará con la
  detección de formatos de preguntas.

El flujo sigue el patrón de [D005]:

1. `opox extract bank` agrupa las coincidencias exactas (mismo texto, respuesta, conjunto
   de opciones y recorte de contexto) y busca **candidatos**: grupos cuyo texto y
   respuesta superan un umbral de similitud (`rapidfuzz`, sobre texto sin mayúsculas,
   tildes ni puntuación). El umbral es **0,85** por defecto (`--threshold`), ajustado a
   ojo sobre C2_AGE: recoge todos los casos conocidos, pero no se ha medido cuántas
   reformulaciones más lejanas se escapan.
   - Escribe `bank.json` con los grupos no ligados a ningún candidato.
   - Escribe dos hojas de control en `interim/<oposición>/`, únicas fuentes de verdad
     de las decisiones manuales:
     - `bank_merges.csv` (`question_a, question_b, reason, merge, note`): pares de
       grupos, identificados por su representante. `reason` es `text`, `answer`,
       `options` o `context` (sólo uno tiene contexto).
     - `bank_contexts.csv` (`context_a, context_b, same`): pares de recortes en
       preguntas por lo demás iguales. Ningún recorte coincide píxel a píxel, ni entre
       modelos A y B, así que la equivalencia se decide por imagen y se aplica a todas
       las preguntas que los usan.
   - Escribe `bank_review.md`, derivado: los pendientes lado a lado, con las
     diferencias resaltadas y las imágenes.
   - Si ya existen las hojas o la batería, se detiene salvo con `--force`.
2. Manualmente se rellena `merge` / `same` con `y` o `n`.
3. `opox add bank` aplica las decisiones. Los grupos ligados por filas forman bloques,
   que sólo se añaden cuando todas sus filas están decididas; las fusiones son
   transitivas y un `n` contradicho por otras fusiones es un error. No toca entradas
   existentes salvo con `--force`, falla ante valores no válidos, informa de añadidas,
   existentes y pendientes, y regenera `bank_review.md`.
4. `opox check bank` verifica que toda pregunta con respuesta está en exactamente una
   entrada y que cada entrada es coherente con `questions.json`.

Al fusionar versiones cuya respuesta está redactada de forma distinta, las redacciones
descartadas no pasan a distractores.
