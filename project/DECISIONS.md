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

> ACTIVO

La batería reúne las preguntas únicas de una oposición tras la deduplicación ([D011]).
El modelo se define en `src/opox/models/bank.py` ([D007]), cuyo docstring incluye un
diagrama, y se almacena en `processed/<oposición>/bank.json`.

- Cada entrada procede de un grupo de `dedup_contexts.json` y referencia todas sus
  apariciones (`sources`) y su pregunta canónica (`canonical`), de la que toma el
  enunciado y la respuesta.
- `bank_id` (`B0001`...) sigue el orden de `canonical` y puede cambiar al regenerar la
  batería. Si en el futuro hace falta un enlace estable, se resolverá conservando los
  identificadores por solapamiento de `sources`.
- El contexto y los distractores siguen [D011]. Los distractores de la canónica van
  primero y el resto, por antigüedad, de más reciente a más antigua; se descartan los
  que coinciden con alguna respuesta del grupo.

La genera el código mediante `opox extract bank`, que exige completar antes las tres
etapas de deduplicación. Se valida con `opox check bank` frente a `questions.json`,
dando por buena la agrupación.


## [D011] Decisiones sobre la deduplicación de preguntas

> ACTIVO

### Normalización

- **Base** o **moderada**: Estandarizando Unicode (NFKC), comillas, guiones y espacios,
  eliminando el punto final y las mayúsculas. Conserva tildes, puntuación y símbolos;
  necesario para psicotécnico verbal, fórmulas y operaciones, que, de lo contrario, se
  perderían o mezclarían pese a ser diferentes. Usado en **respuestas**.
- **Extendida** o **agresiva**: Base más eliminación de tildes y puntuación de prosa,
  con la particularidad de que `. , ; :` sólo se elimina cuando le sigue un espacio o
  es el final del texto, para evitar romper fórmulas y operaciones. Usado en
  **enunciados**.

### Igualdad

En **respuestas** y **enunciados**, dos o más son directamente **iguales** si, tras
normalizar, coinciden al 100%. A su vez, se consideran **similares** si superan cierto
umbral bajo la similitud de Levenshtein normalizada (`1 - ediciones / longitud mayor`).
En este caso, se realiza una revisión manual para determinar si son verdaderamente
iguales o no.

Los **enunciados** sólo miden su igualdad entre respuestas iguales.

La **revisión manual** consiste en comparar clústers de 2 o más miembros, asignándoles
una etiqueta común de **grupo** ('1', 'a'...). Todos aquellos que compartan grupo serán
considerados iguales. En el caso de las **respuestas**, deben juzgarse a ciegas, sin
conocer el enunciado, para valorar el significado.

Actualmente, los umbrales de similitud son los siguientes:

- Para respuestas: **70%**
- Para enunciados: **75%**

### Preguntas canónicas

La pregunta canónica define el texto del enunciado, la respuesta y los distractores
principales. Su utilidad se limita a la extracción de *features*. A la hora de usar una
pregunta como pregunta, se escogerá una al azar de entre las `sources`.

Se escoge como canónica la pregunta más reciente. En caso de empate, se escoge la
primera según `question_id`.

### Contextos

Dentro de cada grupo de enunciados, los recortes de contexto distintos se comparan dos a
dos: cada par de recortes que aparece junto en algún grupo se revisa una sola vez, y la
decisión (`y` si son el mismo contexto, `n` si no) se aplica a todos los grupos que lo
contienen. Un par marcado `n` separa esos grupos, uno por contexto; las preguntas sin
contexto se quedan con el contexto más reciente. Una decisión `n` contradicha por otras
`y` es un error.

El contexto de un grupo es el de su pregunta más reciente con contexto (mismo criterio
que la canónica), aunque la canónica no lo tenga. No se distingue si es opcional: una
pregunta tomada de `sources` conserva su propio contexto, y añadirlo a la pregunta
genérica no resta.

### Distractores

Los distractores de un grupo son las opciones incorrectas de todas sus `sources`. Sólo
se unen los que coinciden al 100% tras la normalización base, conservando el texto de la
pregunta más reciente. Los distractores muy similares pero no iguales se mantienen
separados: se acepta que una pregunta generada tenga opciones casi idénticas antes que
arriesgarse a unir opciones distintas.

Al no requerir revisión manual, no tienen etapa propia: se calculan al generar
`bank.json`.

### Flujo

La deduplicación se hace en tres etapas encadenadas: `answers`; `stems`, que parte de
`dedup_answers.json`; y `contexts`, que parte de `dedup_stems.json`. Para cada etapa
`<s>`, en `interim/<oposición>/`:

- `dedup_<s>.json`: grupos (`DedupCollection`, `src/opox/models/dedup.py`), derivados
  de las preguntas y de la hoja. Cada pregunta con respuesta está en exactamente un grupo.
- `dedup_<s>_review.csv`: hoja de revisión, única fuente de verdad de las decisiones
  manuales.
- `dedup_<s>_review.md`: guía de revisión, sin trabajo manual.

En `answers` y `stems`, la hoja tiene una fila por miembro (preguntas de igual clave
normalizada); los miembros enlazados por similitud, directa o encadenada, forman un caso.
Las etiquetas de `group` son globales a la hoja, pero no pueden abarcar varios casos.
Los miembros sin etiqueta se consideran pendientes y quedan separados.

En `contexts`, la hoja tiene una fila por par de recortes (`context_a;context_b;same;
groups`). Los pares sin decisión se consideran pendientes y no separan nada.

Comandos: `opox dedup extract | add | check <s>`, según [D006]. `check` falla si hay
decisiones pendientes, si la hoja no está al día o si el JSON no coincide con lo que
produciría `add`. `opox dedup check all` comprueba las tres etapas en orden. El
detalle está en `README.md`.
