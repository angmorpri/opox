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

La carpeta raíz de datos es `data/`, dividida en tres, según la convención habitual en
ciencia de datos:

- `raw/`, para fuentes primarias de información: documentos oficiales, guías manuales...
- `interim/`, para archivos y resultados intermedios.
- `processed/`, para resultados definitivos.

Todo el contenido de `interim` y `processed` debe poder ser regenerable a partir del de
`raw` mediante los scripts y programas del proyecto.

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
asignación combina un paso automático y una revisión manual, de la siguiente forma:

1. Una primera función del programa detecta y recorta los contextos de cada examen y los
   almacena en `interim/<oposición>/contexts/`. Genera además un esqueleto de hoja de
   cálculo con todos los campos completos salvo las preguntas asociadas. Esta función
   debe ser idempotente.
2. Manualmente, se copia la hoja a `raw/<oposición>/contexts/` y se completa indicando,
   al menos, el código del examen, la página del contexto (numeración del PDF) y las
   preguntas primera y última que lo requieren (ambas incluidas, numeración del examen).
   A la vez, se validan los recortes automáticos y se añaden a `raw/<oposición>/contexts/`
   los que falten o deban corregirse.
3. Las funciones posteriores toman la hoja de `raw/` como única fuente de verdad, y
   buscan los contextos tanto en `raw/` como en `interim/`. En caso de colisión, prevalece
   el de `raw/`.

Así se respeta [D002]: lo manual vive en `raw/` y lo automático en `interim/` es
regenerable.
