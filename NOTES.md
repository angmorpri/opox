# Notas

Relación desestructurada de casos abiertos, ideas y otras notas.

Se ordenan de más recientes a más antiguas.

## Nombre del proyecto

> ABIERTO

"Proyecto OPO" es sólo el nombre interno y `opox`, también. En algún momento tendré que decidir un nombre más comercial.

## Contextos

> ABIERTO

Algunas preguntas de examen requieren de un contexto en forma de imágenes, diagramas o tablas. Identificarlas, extraerlas y almacenarlas es relativamente fácil, porque todos los archivos que vamos a usar (al menos, por ahora) son PDFs parseables. Sin embargo, conocer qué pregunta referencia a qué contexto puede ser más difícil de detectar.

La solución a la que llegué en la iteración previa fue la siguiente: un script detecta y almacena los contextos en `/contexts/<id_exam>/`, indicando como nombre de archivo la página del PDF en el que aparece. Manualmente, yo reviso ese contexto, y, en el mismo nombre de archivo, indico la pregunta o rango de preguntas a las que aplica. El programa de extracción de preguntas puede saber, así, a qué preguntas asignar qué contexto.

Actualmente, tengo ese contexto extraído en `/old/contexts/...`. Si se decide que el mecanismo es adecuado y suficiente, habrá que moverlo a `/data/`, no sé si a `/interim/` o a `/processed/`. Si se decide que es más conveniente otro, habrá que crear un script previo que convierta de un formato al nuevo, y luego reubicar los archivos.

### Propuesta 1

Manualmente se genera una tabla, en formato hoja de cálculo, con cuatro columnas:

* `test_id`: nombre del archivo del examen al que pertenece este contexto.
* `page`: página en la que se haya la figura del contexto. Numeración según el PDF, no la que aparezca en las páginas del examen.
* `q_first`: primera pregunta que referencia a la figura del contexto.
* `q_last`: última pregunta que referencia a la figura del contexto.

Esta hoja de cálculo se almacena en `raw/`. El programa que extraiga las preguntas simplemente consulta esta tabla, valida que haya una figura en la página en cuestión, extrae el contexto a `processed/contexts/`, y lo asigna en el parámetro adecuado según el modelo de datos. Podría también simplificar previamente la hoja de cálculo a un CSV. Si halla cualquier error en el camino, lo reporta en tiempo real, sin tener que cortar la ejecución. El programa puede ser idempotente, tal que, si se vuelve a ejecutar, sólo actualiza.

Este mecanismo simplifica bastante el proceso respecto al usado en la iteración anterior, que requería ejecutar un script previo, modificar a mano nombres de archivo, y luego ejecutar el extractor de preguntas. Además, resuelve el conflicto de dónde ubicar `contexts/`, que no deberían estar en `raw/` porque son datos procesados, pero tampoco en `interim/` ni `processed/` porque requieren atención manual y, por tanto, no son regenerables reejecutando el programa.

## Registro de los datos crudos en repositorio

> ABIERTO

Los datos crudos descargados de cada oposición (exámenes, solucionarios, términos de convocatoria...) son pesados y poco cambiantes, creo que no tiene sentido almacenarlos en un repo. Simultáneamente, sí que sería práctico tenerlos disponibles, si se migra el proyecto. En consecuencia, hay que encontrar un mecanismo alternativo a Git para "tenerlos en cueneta". El resto de datos en `/data/raw/` y aquéllos en `/data/interim/` y `/data/processed/`, se registran.

## Pipeline de resolución agéntica

> ABIERTO

Formado por cuatro agentes independientes:

1. **Resolvedor.** Resuelve la pregunta buscando las respuestas en fuentes públicas de internet. Puede disponer de un catálogo de partida. Debe indicar con la mayor granularidad posible la referencia de la respuesta dada (fuente, sección, párrafo, frase...). No tiene acceso al solucionario.
2. **Validador de referencias.** Responde a cada pregunta usando exclusivamente las referencias del agente anterior. Si no halla información suficiente, deja la respuesta en blanco. No tiene acceso al solucionario y tiene acceso limitado a internet.
3. **Evaluador.** Evalúa las respuestas contra el solucionario disponible y obtiene una calificación. Desconoce las fuentes usadas para responder.
4. **Curador.** Juzga si las respuestas dadas son adecuadas, matiza y agrupa referencias, y acumula el repositorio definitivo de fuentes.

Matices al flujo:

- A la salida del agente 2 hay un filtro: si no se responde un porcentaje X de preguntas, no se pasa al agente 3. Se vuelve al agente 1, pidiéndole que busque nuevas referencias o que las afine.
- A la salida del agente 3 hay un filtro: si no se obtiene una calificación adecuada, se vuelve al agente 1 para que vuelva a responder.

Este flujo solo aplica a las preguntas que deban responderse con información de internet. Las que se responden mediante lógica y conocimientos generales se excluyen.

## Modelo de datos básico

> ABIERTO

Propongo los siguientes cuatro modelos de datos, basándome en el análisis de los documentos oficiales de bases de convocatoria, exámenes y solucionarios.

### Bases de convocatoria

Extraídas directamente de los documentos, con poca o ninguna limpieza de datos.

```
año: int
tipo_convocatoria: str
formato {
	n_plazas: int
	info_versiones: str     # en referencia a las versiones de Windows o paquete Office usado
	penalizaciones: float
	partes [
		{
			id_parte
			n_preguntas_total: int
			n_reservas: int
			secciones [
				{
					n_preguntas: int
					id_materia: str
				}
			]
		}
	]
	programa [
		{
			id_materia
			materia: str
			temario: list[str]
		}
	]
}
```

### Preguntas de examen (iteración 1)

Se extraen directamente de los documentos de examen y los solucionarios, sin limpieza alguna:

```
id_global
fuente: str		# ruta al archivo
bases: str		# apunta al ID de las bases asociadas
año: int
tipo_convocatoria: str
llamamiento: int
modelo: int
parte: int
es_reserva: int
numero_de_la_pregunta_en_su_parte: int
hay_contexto: bool  # imágenes y diagramas asociados a una o varias preguntas
contexto: str?      # ruta al contexto
texto: str
opciones: list[str]
respuesta: int   # si fue anulada, -1
```

### Categorías

Se extraen de las bases. Se deben realizar algunas divisiones de categorías en exámenes donde están fusionadas.

```
id_categoría
nombre: str
convocatorias [
	{
		año: int
		tipo_convocatoria: str
		temario: list[str]
	}
]
```

### Preguntas de examen (iteración 2)

Se extraen de la primera iteración de preguntas. Se eliminan duplicadas y preguntas con respuesta anulada.

```
id
fuentes: list[int]		# lista de IDs de la iteración 1
hay_contexto?: bool
contexto: str?
texto: str
opciones: list[str] 	# ordenadas tal que la primera siempre es la opción correcta
categoría: int			# --> id de categoría.
```

*Requisitos/Retos conocidos*
- Diferenciar contextos. Probablemente también mecanismo híbrido.
- Dos o más preguntas iguales en formulación y respuesta se consideran la misma incluso si sus otras opciones son distintas. `opciones` puede tener más de 4 elementos.
- `categoría` se queda a 0 en una primera pasada, luego habrá que diseñar un mecanismo programático o agéntico para asignar categorías adecuadamente.

## Etiquetado

> ABIERTO

### Categorización

Las categorías, al menos en C2 AGE, parecen bastante estables entre convocatorias. Se podrían asignar a cada pregunta de forma automática según lo que describan las bases, usando un agente clasificador sencillo para los casos ambiguos.

### Tematización

Los temas dependen de cada convocatoria y están contenidos en las categorías. Tematizar implica escoger una convocatoria concreta y clasificar las preguntas contra ella, con un agente clasificador.

```
rules: id
questions: [
	{
		question_id: int
		category: int
		topic: str
	}
]
```

### Mecanismo de clasificación asistida

1. El agente clasifica según el contexto y las posibilidades, y otorga un nivel de confianza (por definir).
2. Un programa sencillo permite repasar manualmente las decisiones más controvertidas y cambiarlas.

### Otras etiquetas

Quedan por definir etiquetas de más bajo nivel. Las categorías y temas son relativamente objetivos, porque salen directamente de las bases, pero conviene conocer otras formas de granularizar las preguntas. Extraer el "formato de pregunta" también podría ser muy práctico, sobre todo para generar preguntas sintéticas.