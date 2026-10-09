# Estado actual

## Dónde lo dejé

### 09/10/2026

Documentos para guiar a los agentes preparados. Proyecto Python iniciado como `opox` mediante `uv`. Conocimiento y resultados de la iteración previa almacenados en `old/`.

## Próximo paso

Iniciar proyecto de la mano de Claude Code. Garantizar que se comprenden los objetivos del proyecto y el estado actual, que no existen contradicciones demasiado graves en la documentación Inventariar los archivos existentes. Planificar a bajo nivel el parseo de convocatorias, exámenes y solucionaros; resolver el caso abierto sobre los contextos; cerrar modelos de datos y pipeline ETL. Aprovechar al máximo el conocimiento ya registrado en la iteración previa.

## Cuestiones abiertas

### Nombre del proyecto

"Proyecto OPO" es sólo el nombre interno. En algún momento tendré que decidir un nombre potencialmente comercial. Y puede que uno diferente para el paquete Python con todo el programa.

### Contextos

Algunas preguntas de examen requieren de un contexto en forma de imágenes o diagramas. Identificar las imágenes, extraerlas y almacenarlas es relativamente fácil, porque todos los archivos que vamos a usar (al menos, por ahora) son PDFs parseables. Sin embargo, conocer qué pregunta referencia a qué contexto puede ser más difícil de detectar.

La solución a la que llegué en la iteración previa fue la siguiente: un script detecta y almacena los contextos en `/contexts/<id_exam>/`, indicando como nombre de archivo la página del PDF en el que aparece. Manualmente, yo reviso ese contexto, y, en el mismo nombre de archivo, indico la pregunta o rango de preguntas a las que aplica. El programa de extracción de preguntas puede saber, así, a qué preguntas asignar qué contexto.

Actualmente, tengo ese contexto extraído en `/old/contexts/...`. Si se decide que el mecanismo es adecuado y suficiente, habrá que moverlo a `/data/`, no sé si a `/interim/` o a `/processed/`. Si se decide que es más conveniente otro, habrá que crear un script previo que convierta de un formato al nuevo, y luego reubicar los archivos.

### Registro de los datos crudos en repositorio

Los datos crudos en `/data/raw/` son pesados y poco cambiantes, no tiene sentido almacenarlos en el repositorio Git. Sin embargo, sí beneficiaria poder clonarlos. Sé que hay herramientas y estándares para ello, pero no estoy demasiado puesto. Por ahora, se quedan fuera del flujo de cambios. A futuro habrá que decidir qué se hace. Los datos en `/data/interim/` y `/data/processed/` se mantienen porque se asume que serán más ligeros y cambiantes.