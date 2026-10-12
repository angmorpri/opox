# Proyecto OPO

Inteligencia artificial aplicada a la preparación de oposiciones.

## Motivación

Los mecanismos tradicionales para preparar oposiciones en España están obsoletos. Con temario público, exámenes de otros años, y acceso ilimitado a internet, mediante agentes se podría elaborar un corpus de información pública trazable, mediante los que preparar individualmente una oposición. Se podrían fabricar temarios ad-hoc, preguntas y exámenes sintéticos y hasta usar un agente con acceso a toda esta información como profesor particular.

## Objetivos

El objetivo inicial de este proyecto es resolver la siguiente hipótesis:

> Un agente o conjunto de agentes pueden resolver preguntas de oposición usando fuentes
> públicas de internet y referenciando adecuadamente cada respuesta.

Como consecuencia de este proceso, se generará un corpus curado de fuentes públicas que permitirían:

- Generar un temario optimizado, que contenga todo lo que teóricamente puede entrar en un examen según sus bases, pero permita hacer foco en lo que realmente se suele preguntar.
- Generar preguntas sintéticas, clasificadas según categoría, tema u otras etiquetas, basándose en los formatos reales de las preguntas de otros años.
- Habilitar a un agente para que actúe de profesor, dándole acceso a todo este corpus.

De cumplirse la hipótesis, desbloquearíamos dos nuevos objetivos:

1. Valorar el potencial comercial de los resultados.
2. Aplicar el pipeline resultante a otras oposiciones.

## Fases del proyecto

### Fase experimental

En la que trataremos de cumplir la hipótesis sobre una oposición concreta, que será la del **Cuerpo General Auxiliar de la Administración del Estado** (C2_AGE).

Los pasos propuestos son los siguientes:

1. Recopilar información pública oficial relevante sobre la oposición.
2. Parsear y extraer datos relevantes. Mínimo, requeriremos preguntas, temarios, formatos de preguntas, reglas de la convocatoria... Esto implica también categorizar, tematizar y etiquetar de otras maneras todas las preguntas recopiladas, tareas para las cuales habrá que implicar agentes y, probablemente, acciones manuales.
3. Diseñar e implementar el pipeline de resolución agéntica de preguntas. Hay que garantizar que las preguntas se resuelven usando información pública en internet, priorizando fuentes fiables y comunes.
4. Probar si se cumple la hipótesis.

### Fase de producto

Todavía por definir en detalle, consistiría en extender el proceso a otras oposiciones y valorar paralelamente el potencial comercial de los resultados.

## Contexto previo

Este proyecto ya se inicializó una vez, sin llegar a finalizar la fase experimental al completo.
Esta nueva iteración es un reinicio puro, pero el contenido y resultados de la previa se almacena temporalmente en `old/` hasta que dejen de hacer falta. Se deben utilizar como referencia o guía, pero nunca como ejemplo o norma.

## Fuentes relevantes

- [Web oficial de los Cuerpos Generales del Estado](https://www.inap.es/es/seleccion/procesos-selectivos-de-cuerposescalas-generales)

