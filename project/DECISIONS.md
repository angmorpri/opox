# Decisiones

## [D001] Iteración previa

> ACTIVO

Este proyecto ya se llevó a cabo en una iteración previa, sin llegar a resolver la hipótesis.
Todo el código y contenido que no se ha reutilizado se halla en una carpeta temporal `old/prev-iter/`.

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

Los subcomandos de `opox` deben admitir cualquier prefijo que no sea ambiguo
(`opox dedup check ans`, `opox ext cont`).

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
   y lo marca para revisión. Es incremental por examen ([D006]): los exámenes con alguna
   fila en la hoja o algún recorte se dan por cubiertos y no se tocan, de modo que se
   conservan las correcciones y los falsos positivos eliminados. Sólo se escanean los
   demás, y sus contextos se recortan y se añaden al final de la hoja. Los exámenes sin
   contextos se vuelven a escanear en cada ejecución. `--force` lo reconstruye todo.
2. Manualmente, se revisa la hoja y los recortes: se corrigen los erróneos, se añaden los
   que falten y se eliminan los falsos positivos.
3. `opox check contexts` valida la hoja frente a los recortes y las preguntas extraídas.
4. `opox add contexts` asigna a cada pregunta la ruta de su recorte. Sobrescribe
   siempre cualquier ejecución previa.
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

- Sobrescribir datos existentes debe ser la excepción, no la regla.
- Siempre que sea posible, las operaciones deben ser idempotentes o incrementales, es
  decir, no modifican nada que ya existiera, pero permite añadir el contenido de nuevo
  material que entre. Las operaciones que funcionen así deben disponer de una opción
  especial (por ejemplo, `--force`) que permita forzar el reinicio.


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
`pdfplumber`, de forma incremental por examen ([D006]): los exámenes ya presentes en
`questions.json` no se tocan. Al terminar, muestra los puntos que requieren revisión o
completarse manualmente y los exámenes añadidos, referidos sólo a lo extraído en esa
ejecución.


## [D010] Modelo de datos para la batería de preguntas

> ACTIVO

Resultado de descartar las preguntas sin respuesta, deduplicar ([D011]) y agrupar los
distractores. Se almacena en `processed/<oposición>/bank.json`, modelo `QuestionBank`
(`src/opox/models/bank.py`), y lo genera `opox make bank`, siempre desde cero.

```
bank_id: str                # ID de la pregunta más reciente, que será la canónica
sources: list[str]          # IDs de las preguntas originales
text: str                   # Texto de la pregunta canónica
answer: str                 # Respuesta de la pregunta canónica
context: path?              # Ruta al contexto de la pregunta más reciente que lo posea
distractors: list[str]      # Todos los distractores, con el texto del más reciente que lo tenga
```

La pregunta más reciente es la del año más reciente, con empates resueltos por
`question_id`. Las preguntas sin duplicados forman su propia entrada, con una única
`source`.


## [D011] Decisiones sobre la deduplicación de preguntas

> ACTIVO

Una iteración previa del proceso de deduplicación se halla en `old/dedup-manual/`, sólo
para uso referencial e histórico.

### Normalización

- **Base** o **moderada**: Estandarizando Unicode (NFKC), comillas, guiones y espacios,
  eliminando el punto final y las mayúsculas. Conserva tildes, puntuación y símbolos;
  necesario para psicotécnico verbal, fórmulas y operaciones, que, de lo contrario, se
  perderían o mezclarían pese a ser diferentes.
- **Extendida** o **agresiva**: Base más eliminación de tildes y puntuación de prosa,
  con la particularidad de que `. , ; :` sólo se elimina cuando le sigue un espacio o
  es el final del texto, para evitar romper fórmulas y operaciones.

### Distractores

Los distractores de un grupo son las opciones incorrectas de todas sus `sources`. Sólo
se unen los que coinciden al 100% tras la normalización base, conservando el texto de la
pregunta más reciente. Los distractores muy similares pero no iguales se mantienen
separados: se acepta que una pregunta generada tenga opciones casi idénticas antes que
arriesgarse a unir opciones distintas.

Se validan garantizando que existen, al menos, 3 distractores por pregunta.

### Agrupación

Sólo se consideran las preguntas con respuesta. Cada una se representa con la clave
`"{enunciado extendido} {respuesta base}"`.

- **Exacta**: las preguntas con la misma clave forman un grupo automáticamente.
- **Por similitud**: los pares de grupos con similitud de Levenshtein normalizada
  de la clave ≥ 75% y de la respuesta base ≥ 95% (ambos umbrales configurables) se
  proponen para revisión manual, que es opcional.

Por debajo del 100%, los falsos positivos se concentran en preguntas de plantilla
(antónimos, ecuaciones, secuencias, consultas a tablas), donde lo que varía es corto.
La similitud de la respuesta las separa casi por completo de los duplicados reales,
cuyo enunciado sólo cambia en matices (título completo de la norma, versión de software,
reformulaciones). El beneficio de la revisión es pequeño (≈2% del corpus), por lo que
es opcional.

Las uniones son transitivas: si A~B y B~C, A, B y C forman un mismo grupo.

### Contextos

Dentro de cada grupo, los recortes de contexto distintos se comparan dos a dos: cada
par de recortes que aparece junto en algún grupo se revisa una sola vez, y la decisión
(`y` si son el mismo contexto, `n` si no) se aplica a todos los grupos que lo
contienen. Un par marcado `n` separa esos grupos, uno por contexto; las preguntas sin
contexto se quedan con el contexto más reciente. Una decisión `n` contradicha por otras
`y` es un error.

El contexto de un grupo es el de su pregunta más reciente con contexto (mismo criterio
que la canónica), aunque la canónica no lo tenga.

### Flujo

Los archivos se alojan en `interim/<oposición>/`. Las decisiones manuales se identifican
por IDs (de pregunta o de recorte), nunca por posición, de modo que sobreviven a
cualquier recálculo. Los CSV son la fuente de verdad; los Markdown son vistas generadas
para la revisión y se regeneran en cada `extract`, `add` y `check`.

- `duplicates.json`: grupos de más de una pregunta, cada uno con sus `members`
  (`question_id`) y su `origin` (`exact` o `manual`). La pregunta canónica no se guarda.
- `dup_contexts.csv` (+ `.md`): un par de recortes por fila (`context_a, context_b,
  same`), sólo para grupos con dos o más recortes distintos. `same` vacío por defecto;
  su revisión es obligatoria.
- `dup_check.csv` (+ `.md`): un par de grupos por fila, identificado por un
  `question_id` de cada uno (`question_a, question_b, score, answer_score, same`),
  ordenado por similitud descendente. `same` vacío por defecto; su revisión es opcional.

1. `opox extract duplicates` recalcula los grupos exactos, conserva los manuales de
   `duplicates.json` y añade a los CSV sólo los pares nuevos, sin tocar los ya
   existentes ([D006]). `--force` lo reconstruye todo.
2. Manualmente, se completa `dup_contexts.csv` y, si se quiere, `dup_check.csv`.
3. `opox check duplicates` informa de los contextos y casos pendientes, y valida IDs
   inexistentes en `questions.json`, valores de decisión inválidos y contradicciones.
4. `opox add duplicates` (opcional) une en `duplicates.json` los pares marcados `y`
   como grupos `manual`, añade a `dup_contexts.csv` los pares de recortes que surjan y
   regenera `dup_check.csv` sin los pares ya unidos. Las decisiones `n` se conservan
   para no volver a proponerlas.
5. `opox make bank` genera desde cero el banco a partir de `questions.json`,
   `duplicates.json` y `dup_contexts.csv`. Falla si quedan contextos sin decidir o si
   las validaciones de `check duplicates` o de distractores no se cumplen; sólo avisa
   si quedan casos pendientes en `dup_check.csv`.
