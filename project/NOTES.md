# Notas

Relación desestructurada de casos abiertos, ideas y otras notas.

Se ordenan de más recientes a más antiguas.


## Propuesta a alto nivel para el pipeline de generación de batería de preguntas

> 🟢 ABIERTO

1. `opox extract bank`: agrupa coincidencias exactas. Identifica candidatos y genera
   hojas de control para determinar si son equivalentes o no.
2. Manualmente se rellenan las hojas de control, comparando los candidatos.
3. `opox add bank`: añade los candidatos resueltos en las hojas de control.
4. `opox check bank`: garantiza que todas las preguntas de examen con respuesta están
   representadas en las preguntas del banco.


## Propuesta de mecanismo de deduplicación

> 🟠 EN REVISIÓN -> [D011]

Se genera un nuevo ID para cada pregunta del banco. La razón es que en varios de los procesos descritos abajos, la "pregunta canónica" puede que no sea la más reciente. Para evitar tener un criterio arbitrario a la hora de decidir qué ID se le asigna a la pregunta del banco, veo preferible generar uno desde 0.

Se añade un nuevo parámetro al modelo: contexto opcional. Marcará cuándo el contexto es obligatorio (todas las preguntas originales lo tienen) y cuándo es opcional (sólo algunas de las preguntas originales lo tiene).

El flujo cambia de forma. Ahora, se divide en 4 grandes pasos, en función de qué parámetro se esté analizando:

1. **Respuesta**: Se normaliza de forma conservadora. Dos o más respuestas exactamente iguales pasan al siguiente paso. Dos o más respuestas que superen cierto umbral de parecido marcan la opción de revisión manual y pasan al siguiente paso.

2. **Enunciado**: Se normaliza de forma agresiva. Dos o más enunciados exactamente iguales pasan al siguiente paso. Dos o más enunciados que superen cierto umbral de parecido marcan la opción de revisión manual y pasan al siguiente paso. Dos o más enunciados que no superen el umbral de parecido se descartan, desmarcan la revisión manual de sus respuestas y no pasan al siguiente paso.

3. **Contexto**: Si sólo una de las preguntas posee contexto, se asigna y se asigna el contexto como opcional. Si dos o más preguntas, pero no todas, poseen contexto, se marcan para revisión manual y se asigna el contexto como opcional. Si todas las preguntas poseen contexto, se marca para revisión manual y no se asigna el contexto como opcional.

4. **Distractores**: Se normalizan de forma conservadora. Se añaden todos los que sean totalmente diferentes.

La revisión manual requerirá:
- Comparación simultánea de todas las preguntas potencialmente iguales, así como de los contextos.
- Selección de pregunta canónica, es decir, aquella de la que se extraerá la respuesta y el enunciado (cada cual donde proceda).
- Contemplar toda la casuística antes descrita y proporcionar un formato de revisión manual que sea cómodo y abarque las condiciones expuestas.

Si este nuevo flujo complica mucho la ejecución, se podría valorar separar los pases, tal que la revisión manual ocurra entre cada uno y no al final del todo.


## Solucionarios provisionales en 2025

> 🔴 CERRADO -> Solucionarios definitivos descargados


## Procedencia de los datos

> 🔴 CERRADO -> Se confía en seguir correctamente el RUNBOOK.


## Validez temporal de preguntas y fuentes

> 🟢 ABIERTO

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

> 🟢 ABIERTO

Ahora mismo mantengo el contenido de `/data/raw/` en el control de cambios, pero si
empezara a crecer mucho por nuevos exámenes u otras oposiciones, probablemente habría
que buscar un mecanismo alternativo, sobre todo para que GitHub no se queje.


## Propuesta de pipeline agéntico para resolución de preguntas

> 🟢 ABIERTO

Asumiendo que ya disponemos de la batería de preguntas y de una primera versión del
corpus:

1. Separar *preguntas* y *respuestas*.
2. **Agente 1**: Responde a las preguntas sin conocer las respuestas. Trata de usar las fuentes del corpus, pero si no es suficiente, puede buscar en internet. Debe justificar cada respuesta con la referencia más granular posible.
3. **Agente 2**: Responde las mismas preguntas sin conocer las respuestas y **sólo** usando las referencias dadas por el agente anterior. Si con dicha referencia es incapaz de responder, la deja en blanco.
4. *Filtro 1*: Si se dejan demasiadas preguntas en blanco, se vuelve al agente 1 y se le pide matizar o buscar otra referencia.
5. **Agente 3**: Conoce las respuestas y corrige, generando una calificación. Realmente, no tiene por qué ser un agente.
6. *Filtro 2*: Evalúa la calificación, aun por definir el umbral. Si no es suficiente, hay que volver al agente 1.


## Extracción de *features* de preguntas

> 🟢 ABIERTO

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

Servirán también para evaluar si los distractores acumulados en la batería ([D010]) son
útiles o pueden generarse sintéticamente, y para detectar formatos que exijan opciones
fijas ("a y b son correctas", "todas las anteriores", elemento discordante).

### Etiquetado libre

Son **libres**. Aquí la idea es detectar materias a más bajo nivel que la clasificación
oficial. Representaría el tercer nivel de clasificación.


## Preguntas con contexto

> 🔴 CERRADO -> [D005]


## Modelo de datos para C2_AGE

> 🟡 EN CURSO
> "Bases de convocatoria" -> [D008]
> "Preguntas por examen" -> [D009]
> "Batería de preguntas" -> [D010]

Se propone una extracción en dos fases:

*Fase 1*

1. De las **bases de convocatoria** se extrae el formato de examen y el programa (bloques, temas).
2. De los **exámenes** y **solucionarios** se extraen las preguntas por examen.

*Fase 2*

1. Del programa se extraen las **categorías**, transversales a todas las convocatorias, y dentro de cada una se organizan los **temarios** contenidos en cada una de las convocatorias.
2. De las preguntas por examen se extrae una **batería completa de preguntas**, deduplicando, agrupando y eliminando preguntas con respuestas inválidas.

Los modelos a bajo nivel propuestos se detallan a continuación.

### Bases de convocatoria

> 🔴 CERRADO -> [D008]

### Preguntas por examen

> 🔴 CERRADO -> [D009]

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

> 🟡 EN CURSO -> [D010]


## Nombre del proyecto

> 🟢 ABIERTO

"OPO" es un nombre temporal. Eventualmente habrá que buscar uno más comercial.

`opox` podrá seguir llamándose así, ya que es algo interno.