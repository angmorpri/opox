# Decisiones

**Solo decisiones cerradas, que no deberían cambiar en nuevas iteraciones.** Las entradas no se editan: si una decisión cambia, se añade una nueva que la sustituye y se marca la antigua como sustituida.

## [D001] Estructura de datos

* **Estado**: ACTIVO
* **Contexto**: el proyecto transforma documentos oficiales en datos estructurados a través de varias fases (extracción, limpieza, deduplicación, etiquetado). Cada fase debe poder regenerarse a partir de la anterior.
* **Decisión**: la carpeta raíz de datos es `data/`, en la raíz del repositorio, dividida en `raw/`, `interim/` y `processed/`, según la convención habitual en ciencia de datos. Dentro de cada una, las oposiciones se organizan por su identificador (p. ej. `C2_AGE`). En `raw/` están los documentos oficiales sin modificar: exámenes, solucionarios, bases de convocatoria y otros.
* **Consecuencias**: `raw/` no se modifica nunca. Todo lo que hay en `interim/` y `processed/` debe poder regenerarse con los scripts del proyecto.
* **Alternativas descartadas**: -

## [D002] Nomenclatura para exámenes y bases de convocatorias

* **Estado**: ACTIVO
* **Contexto**: Los archivos oficiales de exámenes, solucionarios y bases de convocatoria, que son la fuente de la que parten los datos que se usarán en el proyecto, requieren un nombre que permita identificar fácilmente cada una.
* **Decisión**: Se adoptan las siguientes nomenclaturas para cada tipo de archivo:
	* ***Bases de convocatoria***: `YYYYT`.
	* ***Exámenes y solucionarios***: `YYYYTNMS`.
	Donde:
	* `YYYY` es el año de la convocatoria.
	* `T` es el tipo de convocatoria, que puede ser "L" (acceso libre), "I" (promoción interna) o "E" (estabilización de empleo temporal).
	* `N` es el llamamiento. Si no hay diferentes llamamientos, vale `0`.
	* `M` es el modelo. Generalmente, variará entre "A", "B" y "X", este último para señalar convocatorias extraordinarias.
	* `S` distingue entre "T" para los exámenes y "R" para los solucionarios oficiales.
* **Consecuencias**: -
* **Alternativas descartadas**: -

## [D003] Core del código: `opox`

* **Estado**: ACTIVO
* **Contexto**: Este proyecto implica bastante carga de código y numerosas funcionalidades. Crear un proyecto Python sería bastante práctico.
* **Decisión**: El código utilizado para dar vida al proyecto será un proyecto Python llamado `opox`. Un programa en línea de comandos `opox` actuará también como interfaz para centralizar funcionalidades.
* **Consecuencias**: El código se centraliza en `src/opox/`. Se crea un `README.md` que debe estar centrado exclusivamente en decsribir el código a medida que este avance. Coexistimos con ecosistema `uv` y `pyproject.toml`.
* **Alternativas descartadas**: Hacerlo todo por scripts, sin paquetizar.

## [D004] `old/` queda fuera del flujo de cambios

* **Estado**: ACTIVO
* **Contexto**: La carpeta `old/` contiene restos de la iteración pasada. Eventualmente, dejará de ser útil.
* **Decisión**: Se deja fuera del repositorio y flujo de cambios. Se añade al `.gitignore`.
* **Consecuencias**: -
* **Alternativas descartadas**: -