# Notas

Relación desestructurada de casos abiertos, ideas y otras notas.

Se ordenan de más recientes a más antiguas.


## Solucionarios provisionales en 2025

> CERRADO -> Solucionarios definitivos descargados


## Procedencia de los datos

> ABIERTO

Desde [D002], `interim/` y `processed/` mezclan resultados de código, de agentes y
manuales, y dejan de ser regenerables. Puede ser necesario registrar quién produjo cada
dato y si ha sido revisado, sobre todo en los que sirven de referencia para evaluar la
hipótesis (p. ej., las respuestas del solucionario). Se valorará en la primera situación
que lo requiera.


## Validez temporal de preguntas y fuentes

> ABIERTO

Cada pregunta se respondió conforme a la normativa (y versiones de software) vigentes en
la fecha del examen. Si la fuente ha cambiado desde entonces, un agente que use el corpus
actual podría fallar con razón, o acertar apoyándose en una fuente que entonces no
existía. Esto afecta a:

- **La hipótesis**: "sin fallos" debe entenderse respecto a la fuente vigente en la fecha
  del examen, respecto a la actual, o distinguir ambos casos.
- **El corpus**: puede requerir versionado temporal de las fuentes (p. ej., textos
  consolidados del BOE a una fecha dada).
- **La batería de preguntas**: preguntas que eran correctas pueden haber quedado
  obsoletas; habría que detectarlas y marcarlas en lugar de contarlas como fallos.
- **El criterio de éxito**: falta definir el umbral del *Filtro 2* y cómo tratar las
  preguntas impugnadas o con errores en el solucionario definitivo.


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

> CERRADO -> [D005]


## Modelo de datos para C2_AGE

> EN CURSO
> "Bases de convocatoria" -> [D008]
> "Preguntas por examen" -> [D009]

Se propone una extracción en dos fases:

*Fase 1*

1. De las **bases de convocatoria** se extrae el formato de examen y el programa (bloques, temas).
2. De los **exámenes** y **solucionarios** se extraen las preguntas por examen.

*Fase 2*

1. Del programa se extraen las **categorías**, transversales a todas las convocatorias, y dentro de cada una se organizan los **temarios** contenidos en cada una de las convocatorias.
2. De las preguntas por examen se extrae una **batería completa de preguntas**, deduplicando, agrupando y eliminando preguntas con respuestas inválidas.

Los modelos a bajo nivel propuestos se detallan a continuación.

### Bases de convocatoria

> CERRADO -> [D008]

### Preguntas por examen

> CERRADO -> [D009]

### Categorías

Las **categorías** son transversales a todas las convocatorias. Se mantienen estables. Se extraen a partir de los bloques y los temas, con cambios mínimos.
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

*Retos conocidos*
- Algunas convocatorias fusionan "ofimática" y "actividad administrativa". Se pueden dividir teniendo en cuenta los temas.
- Algunas convocatorias no denominan explícitamente su bloque. Se puede inferir de aquéllas en las que sí.

### Batería de preguntas

Se eliminan duplicados y preguntas con respuesta anulada.

En caso de preguntas iguales con misma respuesta pero diferentes opciones, se agrupan
las opciones. Además, en cualquiera de los casos, se ordenan las opciones tal que la
primera siempre sea la correcta.

Dos preguntas iguales en texto, respuesta y opciones dejan de serlo si sus contextos son diferentes.

```
id_pregunta: int
ids_originales: list[str]
ruta_contexto: path?
texto: str
opciones: list[str]
```

*Retos conocidos*
- Detectar si dos preguntas tienen contextos iguales puede requerir intervención manual.


## Nombre del proyecto

> ABIERTO

"OPO" es un nombre temporal. Eventualmente habrá que buscar uno más comercial.

`opox` podrá seguir llamándose así, ya que es algo interno.