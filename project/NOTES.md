# Notas

Relación desestructurada de casos abiertos, ideas y otras notas.

Se ordenan de más recientes a más antiguas.


## Propuesta a alto nivel para el pipeline de generación de batería de preguntas

> 🟢 ABIERTO
> Propuesta casi cerrada, a falta de decidir deduplicación de contextos y distractores.

La deduplicación de **respuestas** y **enunciados** se hace en dos etapas: primero las
respuestas (`answers`) y después los enunciados (`stems`). Sustituye a
`opox extract/add/check bank`. `bank.json` ([D010]) sólo se genera después, tras
resolver contextos y distractores.

### Comandos

Para cada etapa `<s>` (`answers` o `stems`):

- `opox dedup extract <s>`: genera el JSON intermedio con los grupos automáticos (igualdad
  exacta), la hoja de revisión y su guía. Respeta [D006]: no sobrescribe el JSON ni la
  hoja si existen; con `--force`, regenera la hoja conservando las decisiones cuyos
  miembros siguen existiendo e informa de las que se pierden. La guía no contiene trabajo
  manual y siempre se regenera.
- `opox dedup add <s>`: reconstruye el JSON a partir de los grupos automáticos y la hoja
  completa. Es idempotente, y deshacer una unión en la hoja basta para deshacerla en el
  JSON. Avisa de las filas de la hoja cuyos miembros ya no existen.
- `opox dedup check <s>`: comprueba que cada pregunta con respuesta está en exactamente
  un grupo y que el JSON coincide con lo que produciría `add`. Si falla, recuerda si la
  hoja tiene casos sin rellenar. En `stems`, además, que la hoja y el JSON siguen siendo
  coherentes con el `dedup_answers.json` actual.

`stems` parte de `dedup_answers.json`: si se rehace la etapa de respuestas, hay que
repetir la de enunciados.

### Ficheros

En `interim/<oposición>/`, en el control de cambios ([D002]):

| Etapa   | JSON                 | Hoja                        | Guía                       |
|---------|----------------------|-----------------------------|----------------------------|
| answers | `dedup_answers.json` | `dedup_answers_review.csv`  | `dedup_answers_review.md`  |
| stems   | `dedup_stems.json`   | `dedup_stems_review.csv`    | `dedup_stems_review.md`    |

La hoja es la única fuente de verdad de las decisiones manuales; el JSON es un resultado
derivado de `questions.json` (y, en `stems`, de `dedup_answers.json`) y de la hoja.

Las hojas de revisión son CSV en UTF-8 con BOM, separados por ';', una fila por miembro:

```
case;member;group;max_similarity;questions;text
```

- Un **caso** reúne los miembros enlazados por similitud, directa o encadenada. Se
  ordenan de menor a mayor similitud.
- Un **miembro** es un grupo automático (A, B, C…). Se identifica por sus `question_id`
  (`questions`), no por el número de caso, para conservar las decisiones al regenerar.
- `group` se rellena a mano: los miembros de un caso con la misma etiqueta son iguales.
- `text` es la respuesta (en `answers`) o el enunciado (en `stems`) de la pregunta
  canónica del miembro.

La guía en Markdown muestra cada caso con la similitud de cada pareja y un diff por
palabras frente al miembro A. En `answers` sólo muestra respuestas; en `stems`, también
la respuesta, las opciones y la pregunta canónica resultante.

### Modelo de datos

Ambos JSON comparten modelo, en `src/opox/models/dedup.py` ([D007]):

```
DedupGroup
  canonical: str               # question_id de la pregunta canónica ([D011])
  members: list[DedupMember]   # 1 si es automático, 2+ si se unió en la revisión
DedupMember
  key: str                     # respuesta o enunciado normalizado
  sources: list[str]           # question_id con esa clave
```

- Cada pregunta con respuesta aparece en exactamente un `sources` de cada JSON.
- En `stems`, los miembros de un grupo pertenecen siempre a un mismo grupo de
  `dedup_answers.json`.
- Los grupos se ordenan por `canonical`, y los miembros y sus `sources`, por
  `question_id`, para que la salida sea estable.


## Propuesta de mecanismo de deduplicación

> 🟡 EN CURSO
> "Respuestas" y "enunciados" cerrados en otras notas y en [D011]
> "Contextos" y "distractores" pendientes.

- **Contexto**: Si sólo una de las preguntas posee contexto, se asigna y se asigna el contexto como opcional. Si dos o más preguntas, pero no todas, poseen contexto, se marcan para revisión manual y se asigna el contexto como opcional. Si todas las preguntas poseen contexto, se marca para revisión manual y no se asigna el contexto como opcional.
- **Distractores**: Se normalizan de forma conservadora. Se añaden todos los que sean totalmente diferentes.


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

> 🟢 ABIERTO -> [D010] reservado para cuando se cierre definitivamente

Acumula las preguntas deduplicadas, referenciando claramente sus versiones originales y
presentando una canónica para ser usada en la extracción de *features*.

```
BankQuestion
  bank_id: str
  sources: list[str]            # question_id de todas las apariciones
  text: str
  context: PurePosixPath | None
  context_optional: bool        # si hay contexto, pero no aparece siempre
  answer: str
  distractors: list[str]        # pool deduplicado, al menos 3
```

`bank_id` es único y no está relacionado ni con las preguntas originales ni con la
secuencia original de las preguntas. En cada regeneración del banco de preguntas puede
cambiar.

Se almacena en `bank.json`.


## Nombre del proyecto

> 🟢 ABIERTO

"OPO" es un nombre temporal. Eventualmente habrá que buscar uno más comercial.

`opox` podrá seguir llamándose así, ya que es algo interno.