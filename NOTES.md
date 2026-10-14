# Notas

Relación desestructurada de casos abiertos, ideas y otras notas.

Se ordenan de más recientes a más antiguas.


## Escalabilidad de `data/raw/`

> ABIERTO

Ahora mismo mantengo el contenido de `/data/raw/` en el control de cambios, pero si
empezara a crecer mucho por nuevos exámenes u otras oposiciones, probablemente habría
que buscar un mecanismo alternativo, sobre todo para que GitHub no se queje.


## Propuesta de pipeline agéntico para resolución de preguntas

> ABIERTO

Asumiendo que ya disponemos de la batería de preguntas y de una primera versión del
corpus:

1. Separar *preguntas* y *respuestas*.
2. **Agente 1**: Responde a las preguntas sin conocer las respuestas. Trata de usar las fuentes del corpus, pero si no es suficiente, puede buscar en internet. Debe justificar cada respuesta con la referencia más granular posible.
3. **Agente 2**: Responde las mismas preguntas sin conocer las respuestas y **sólo** usando las referencias dadas por el agente anterior. Si con dicha referencia es incapaz de responder, la deja en blanco.
4. *Filtro 1*: Si se dejan demasiadas preguntas en blanco, se vuelve al agente 1 y se le pide matizar o buscar otra referencia.
5. **Agente 3**: Conoce las respuestas y corrige, generando una calificación. Realmente, no tiene por qué ser un agente.
6. *Filtro 2*: Evalúa la calificación, aun por definir el umbral. Si no es suficiente, hay que volver al agente 1.


## Extracción de *features* de preguntas

> ABIERTO

Bajo este concepto se agruparían todos los procesos de categorización, tematización,
detección de formatos y cualesquiera otros etiquetados pertinentes sobre las preguntas.

Actualmente, con la C2_AGE en mente, se identifican las siguientes *features*.

### Categorías

Son **oficiales**, según se exponen en las bases de la convocatoria. Son comunes a lo
largo de los años. Representan el primer nivel de clasificación.

Dado que no dependen de la convocatoria, se podrían asignar a la batería de preguntas
nada más ésta estuviera generada.

### Temas

Son **oficiales** según se exponen en las bases de cada convocatoria. Cada una define
sus propios temas, aunque puedan ser muy parecidos entre años. Representan el segundo
nivel de clasificación.

Dado que sí dependen de la convocatoria, habría que retematizar la batería de preguntas
para cada una según fuera necesario, aunque, normalmente, sólo será útil contra la
convocatoria más reciente. Nótese también que algunos temas pueden dejar de aparecer,
en cuyo caso, habrá preguntas que queden "descartadas".

### Formato de preguntas

Son **libres**. La idea es que un agente o modelo pudieran detectar formatos comunes
de preguntas, que será útil en un futuro para generar preguntas sintéticas.

### Etiquetado libre

Son **libres**. Aquí la idea es detectar materias a más bajo nivel que la clasificación
oficial. Representaría el tercer nivel de clasificación.


## Preguntas con contexto

> ABIERTO

Algunas preguntas están asociadas a un contexto en forma de imagen, diagrama o tabla.
En la iteración previa se vio complicado extraerlos automáticamente y luego detectar qué
preguntas requerían su uso, así que se decidió resolverlo manualmente.

En la iteración previa, el proceso consistía en un script que, examen por examen,
recortaba cada figura o tabla detectada y la almacenaba en una carpeta `contexts/` con el código
del examen y el nombre de la página en la que se halló (según la numeración del PDF,
no la del examen). A continuación, manualmente se revisaba que se hubiera recogido todo
el contexto y se completaba lo que faltase. A su vez, se modificaba el nombre del
archivo para incluir el rango de preguntas que hacían referencia a ese contexto (usando
para las preguntas la numeración en el examen). El script que finalmente extraía las
preguntas de los exámenes consultaba en la carpeta y asignaba el contexto
según se indicase. Los resultados de este mecanismo se hallan en `old/contexts/`.

Este mecanismo no es el más adecuado. Primero, indicar las preguntas que hacen
referencia al contexto mediante el propio nombre del archivo es chapucero. La solución
más elegante sería hacerlo mediante una hoja de cálculo en la que indicar, al menos,
el código del examen, la página donde se halla el contexto, y los índices de la primera
y última pregunta (ambas incluidas) que lo requieren. Segundo, no queda del todo claro
dónde debería vivir la carpeta `contexts/`, ya que mezcla acción automática (script que
detecta y recorta figuras y tablas) y acción manual (revisión y añadido de contextos
no detectados).


## Modelo de datos para C2_AGE

> ABIERTO

Se propone una extracción en dos fases:

*Fase 1*

1. De las **bases de convocatoria** se extrae el formato de examen y el programa (categorías, temas).
2. De los **exámenes** y **solucionarios** se extraen las preguntas por examen.

*Fase 2*

1. Del programa se extraen las **categorías**, transversales a todas las convocatorias, y dentro de cada una se organizan los **temarios** contenidos en cada una de las convocatorias.
2. De las preguntas por examen se extrae una **batería completa de preguntas**, deduplicando, agrupando y eliminando preguntas con respuestas inválidas.

Los modelos a bajo nivel propuestos se detallan a continuación.

### Bases de convocatoria

```
id_convocatoria: str
fuente: path
año: int
tipo_convocatoria: str		# "L", "I" o "E"
formato {
	n_plazas: int
	info_versiones: str		# texto libre en el que se indique qué versiones de software se preguntan
	penalización: float
	partes [
		{
			id_parte: int
			n_total_preguntas: int
			n_extra_preguntas: int
			secciones [
				{
					n_preguntas: int
					id_materia: int
				}
			]
		}
	]
	programa [
		{
			id_materia: int
			nombre_materia: str
			temario: list[str]
		}
	]
}
```

### Preguntas por examen

```
id_pregunta: int
fuente: str
año: int
tipo_convocatoria: str		# "L", "I" o "E"
modelo: str 				# "A", "B" o "X"
id_convocatoria: str 		# -> Bases de convocatoria
parte: int
es_reserva: bool
num_en_examen: int
tiene_contexto?: bool
ruta_contexto: str?
texto: str
opciones: list[str]
respuesta: int				# Si no tiene (pregunta anulada), vale -1
```

### Categorías

Las **categorías** son transversales a todas las convocatorias. Se mantienen estables.
Los **temas** pueden ser similares, pero cada convocatoria puede tener sus matices.

```
id_categoría: int
nombre: str
convocatorias: [
	{
		id_convocatoria: str	# -> Bases de convocatoria
		temario: list[str]
	}
]
```

### Batería de preguntas

Se eliminan duplicados y preguntas con respuesta anulada.

En caso de preguntas iguales con misma respuesta pero diferentes opciones, se agrupan
las opciones. Además, en cualquiera de los casos, se ordenan las opciones tal que la
primera siempre sea la correcta.

Dos preguntas iguales en texto, respuesta y opciones dejan de serlo si sus contextos son diferentes.

```
id_pregunta: int
ids_originales: list[int]
ruta_contexto: str?
texto: str
opciones: list[str]
```

*Retos conocidos*
- Detectar si dos preguntas tienen contextos iguales puede requerir intervención manual.


## Nombre del proyecto

> ABIERTO

"OPO" es un nombre temporal. Eventualmente habrá que buscar uno más comercial.

`opox` podrá seguir llamándose así, ya que es algo interno.