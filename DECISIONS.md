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

Algunas preguntas dependen de un contexto (imagen, diagrama o tabla). Su detección y
asignación combina un paso automático y una revisión manual, ambos en
`interim/<oposición>/contexts/`:

1. Una función del programa detecta y recorta los contextos de cada examen y genera un
   esqueleto de hoja de cálculo con todos los campos completos salvo las preguntas
   asociadas. Respeta [D006]: no sobrescribe recortes ni hojas existentes.
2. Manualmente, se completa la hoja indicando, al menos, el código del examen, la página
   del contexto (numeración del PDF) y las preguntas primera y última que lo requieren
   (ambas incluidas, numeración del examen). A la vez, se validan los recortes, se
   corrigen los erróneos y se añaden los que falten.
3. Las funciones posteriores toman esa hoja y esos recortes como única fuente de verdad.


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


