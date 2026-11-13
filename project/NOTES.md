# Notas

## Proceso de categorización

> 🟢 ABIERTO

### Principio

La categoría se rige estrictamente por lo que dice la convocatoria (lugar donde se
examinó la pregunta), no por su contenido, incluso si las bases contienen algún error.
Nada se resuelve por heurística: lo que las reglas no fijan pasa a revisión.

### Asignación determinista

Para cada fuente de una entrada del banco se obtienen sus **categorías candidatas**
cotejando `rules.json` y `categories.json`:

- **Ordinaria**: su número la sitúa en una sección de su parte (las secciones están
  listadas en el orden del examen); la sección da el bloque, y el bloque, las
  categorías con temas suyos en esa convocatoria.
- **Reserva**: no está ligada a ninguna sección, así que recibe la unión de las
  categorías de todos los bloques de su parte.

La categoría de la entrada sale de la **intersección** de las candidatas de todas sus
fuentes:

- Vacía: ERROR.
- Un elemento: OK, categoría asignada.
- Dos o más: REVISIÓN.

Así, una reserva o pregunta ambigua que se resuelve por un duplicado ordinario no va a
revisión.

Pendiente: documentar en el modelo de `rules.json` que el orden de las secciones es el
del examen (comprobado en los límites de 2022E y 2025L).

### Experimento en C2_AGE

Sobre 989 entradas: 703 OK, 286 a REVISIÓN, 0 ERROR.

| Candidatas | Entradas | Origen |
|---|---|---|
| {Actividad administrativa, Ofimática} | 254 | 233 del bloque II de las L, 21 reservas de esa parte |
| {Organización pública, Psicotécnico} | 30 | reservas de la parte 1 de las L |
| {Organización pública, Ofimática, Psicotécnico} | 2 | reservas de 2022E |

Ninguna tiene contexto. Actividad administrativa no recibe ninguna asignación
determinista: depende por completo de la revisión.

Las preguntas del bloque II siguen aproximadamente el orden del temario, pero el corte
varía por examen y hay excepciones (2019L0A-2-50, sede electrónica, al final), así que
no sirve como regla.

### Revisión por agente

Por cada entrada del banco en REVISIÓN (no por fuente), se llama a un modelo por API con
la pregunta, sus opciones y las categorías candidatas, y se le pide la categoría y un
nivel de confianza. A revisión manual sólo pasan las de confianza muy baja.

Se empezará con un modelo gratuito (Gemini, OpenRouter `:free`, Groq u Ollama local),
dejando abierta la posibilidad de usar otros, como Haiku (~300 llamadas de ~1,5k
tokens: céntimos). Implica una interfaz común con un adaptador por proveedor.

Lecciones de la iteración previa (`old/prev-iter/llm_categorize*.py`):

- La confianza pedida como número no sirve: el modelo respondía 0,95 en el 83 % de los
  casos, incluidos errores. Mejor una escala cualitativa (alta, media, baja) con
  criterios explícitos.
- Preguntar "¿X o Y?" fuerza a diferenciar aunque no haya diferencia; la alternativa
  fue puntuar a ciegas cada candidata por separado.
- El psicotécnico es un tipo de pregunta, no una materia: requiere su propio criterio
  (si se resuelve sólo con la información del enunciado).
- Cada categoría se describe con su temario de esa convocatoria, no sólo con su nombre.

Ideas por decidir:

- **Señal de confianza adicional**, independiente de lo que el modelo diga de sí mismo:
  repetir la llamada N veces y medir el acuerdo, o contrastar con un segundo modelo.
- **Calibración**: las 703 entradas OK sirven para medir el acierto y fijar el umbral
  de "confianza muy baja", salvo para Actividad administrativa, que no tiene ninguna;
  para ella haría falta una pequeña muestra etiquetada a mano.
- **Temario de referencia**: el de la convocatoria de la fuente canónica (`bank_id`).
- **Salida estructurada**: JSON con la categoría restringida a las candidatas de la
  entrada y una justificación breve previa a la respuesta.
- **Almacenamiento**: `category` en `features.json` con `category_id`, método
  (`rules`, `llm`, `manual`), candidatas y, si aplica, confianza y modelo. Respuestas
  del modelo cacheadas en `interim/`, registrando modelo y versión del prompt. La
  revisión manual, como en duplicados: CSV/MD en `interim/` y `opox features add categories`.
- **Tematización conjunta**: si el modelo eligiera el tema, la categoría se derivaría
  de él, adelantando la tematización.


## Resultado de la extracción de *features*

> 🟢 ABIERTO

El resultado de la extracción de *features* será un archivo `features.json` que usa
`bank_id` como identificador. Contendrá 4 objetos para cada proceso: `category`,
`topic`, `tags`, `format`.


## Preguntas iguales con respuesta contextual

> 🟢 ABIERTO
> En C2_AGE no existe ningún caso así

En preguntas cuya respuesta sea "a y b son correctas" o "las dos primeras son correctas"
o similar, existen varios problemas que resolver:

- La forma actual de almacenamiento pierde las letras, así que hay que seguir
  garantizando que el orden en el que se guarda es el correcto.
- A la hora de deduplicar preguntas y normalizar distractores, puede darse que dos
  preguntas sean iguales, pero los distractores sean diferentes, entonces, al agruparlos
  y perderse el orden original, se impida resolverlo adecuadamente.

Con "Ninguna de las anteriores" o "Todas las anteriores" no aplica, ya que cualquier
combinación de distractores será válida.


## Nueva deduplicación automática

> 🔴 CERRADO -> [D011]


## Propuesta a alto nivel para el pipeline de generación de batería de preguntas

> 🔴 CERRADO -> [D010] y [D011]


## Propuesta de mecanismo de deduplicación

> 🔴 CERRADO -> Respuestas, enunciados, contextos y distractores en [D011]


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

> Definición y temas por convocatoria -> [D012]. Pendiente su asignación a la batería.

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

> 🔴 CERRADO -> [D008], [D009], [D010] y [D012]

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

> 🔴 CERRADO -> [D012]

### Batería de preguntas

> 🔴 CERRADO -> [D010]


## Nombre del proyecto

> 🟢 ABIERTO

"OPO" es un nombre temporal. Eventualmente habrá que buscar uno más comercial.

`opox` podrá seguir llamándose así, ya que es algo interno.