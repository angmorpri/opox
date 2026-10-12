# Decisiones

## [D001] Estructura de datos

> ACTIVO

La carpeta raíz de datos es `data/`, dividida en tres, según la convención habitual en ciencia de datos:

- `raw/`, para documentos oficiales sin modificar y otros archivos que se utilicen como fuente de información.
- `interim/`, para archivos y resultados intermedios.
- `processed/`, para resultados definitivos.

Todos los archivos en `interim` y `processed` deben poder ser regenerables a partir de `raw` mediante los scripts y programas del proyecto.

Dentro de cada una, las diferentes oposiciones se organizan por sus identificadores (p. ej. `C2_AGE`).

## [D002] Nomenclatura para exámenes y bases de convocatorias

> ACTIVO

Se adoptan las siguientes nomenclaturas para cada tipo de archivo:

- ***Bases de convocatoria***: `YYYYT`.
- ***Exámenes y solucionarios***: `YYYYTNMS`.

Donde:

- `YYYY` es la fecha oficial de publicación de la convocatoria.
- `T` es el tipo de convocatoria, que puede ser "L" (acceso libre), "I" (promoción interna) o "E" (estabilización de empleo temporal).
- `N` es el llamamiento. Si no hay diferentes llamamientos, es `0`.
- `M` es el modelo. Generalmente, variará entre "A" y "B". "X" se reserva para los llamamientos extraordinarios.
- `S` distingue entre "T" para los exámenes y "R" para los solucionarios oficiales.

## [D003] Core del código: `opox`

> ACTIVO

El código utilizado para dar vida al proyecto será un proyecto Python llamado `opox`, gestionado mediante `uv` y `pyproject.toml`. Se almacena en `src/opox/`.

`opox` deberá tener una interfaz por línea de comandos para ejecutar cada una de las funcionalidades que se vayan desarrollando.

`README.md` se usará exclusivamente para describir el código y se redactará en inglés.

## [D004] Preguntas de carácter psicotécnico

> ACTIVO

Dado que estas preguntas se responden mediante lógica o razonamiento, quedan fuera del pipeline de resolución agéntica. Se parsearán y categorizarán como las demás para futuros usos.

## [D005] Convocatoria de 2018

> ACTIVO

Dado que los exámenes de la convocatoria de 2018 requieren OCR, quedan fuera de la fase experimental.