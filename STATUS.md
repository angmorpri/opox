# Estado actual

## Dónde lo dejé

### 11/10/2026

Documentos para guiar a los agentes preparados. Proyecto Python iniciado como `opox` mediante `uv`. Exámenes, solucionarios y bases de convocatoria de la oposición objetivo del experimento (C2_AGE) descargados y almacenados. Conocimiento y resultados de la iteración previa almacenados en `old/`.

## Próximo paso

Iniciar proyecto de la mano de Claude Code. Garantizar que se comprenden los objetivos del proyecto, inventariar archivos existentes y corregir errores en la documentación. Planificar a bajo nivel el parseo de convocatorias, exámenes y solucionarios; resolver el caso abierto sobre los contextos; cerrar modelos de datos y pipeline ETL.

## Cuestiones abiertas

### Nombre del proyecto

"Proyecto OPO" es sólo el nombre interno. En algún momento tendré que decidir un nombre potencialmente comercial. Y puede que uno diferente para el paquete Python con todo el programa.

### Contextos

Algunas preguntas de examen requieren de un contexto en forma de imágenes o diagramas. Identificar las imágenes, extraerlas y almacenarlas es relativamente fácil, porque todos los archivos que vamos a usar (al menos, por ahora) son PDFs parseables. Sin embargo, conocer qué pregunta referencia a qué contexto puede ser más difícil de detectar.

La solución a la que llegué en la iteración previa fue la siguiente: un script detecta y almacena los contextos en `/contexts/<id_exam>/`, indicando como nombre de archivo la página del PDF en el que aparece. Manualmente, yo reviso ese contexto, y, en el mismo nombre de archivo, indico la pregunta o rango de preguntas a las que aplica. El programa de extracción de preguntas puede saber, así, a qué preguntas asignar qué contexto.

Actualmente, tengo ese contexto extraído en `/old/contexts/...`. Si se decide que el mecanismo es adecuado y suficiente, habrá que moverlo a `/data/`, no sé si a `/interim/` o a `/processed/`. Si se decide que es más conveniente otro, habrá que crear un script previo que convierta de un formato al nuevo, y luego reubicar los archivos.

### Registro de los datos crudos en repositorio

Los datos crudos descargados de cada oposición (exámenes, solucionarios, términos de convocatoria...) son pesados y poco cambiantes, creo que no tiene sentido almacenarlos en un repo. Simultáneamente, sí que sería práctico tenerlos disponibles, si se migra el proyecto. En consecuencia, hay que encontrar un mecanismo alternativo a Git para "tenerlos en cueneta". El resto de datos en `/data/raw/` y aquéllos en `/data/interim/` y `/data/processed/`, se registran.