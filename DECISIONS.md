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
   enunciados compartidos), guarda los recortes y genera la hoja de control. Respeta
   [D006]: no sobrescribe recortes ni hojas existentes; si ya existen, informa de los
   candidatos no cubiertos.
2. Manualmente, se revisa la hoja y los recortes: se corrigen los erróneos, se añaden los
   que falten y se eliminan los falsos positivos.
3. `opox check contexts` valida la hoja frente a los recortes y las preguntas extraídas.
4. `opox add contexts` asigna a cada pregunta la ruta de su recorte.
5. `opox check questions` verifica la coherencia de las preguntas con la hoja e informa
   si la asignación de contextos está pendiente.

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
`rules.json` y la hoja de contextos.


