# Proyecto OPO

Inteligencia artificial aplicada a la preparación de oposiciones.

## Motivación

Los mecanismos tradicionales para preparar oposiciones en España están obsoletos. Con temario público, exámenes de otros años, y acceso ilimitado a internet, mediante agentes se podría elaborar un corpus de información pública trazable, mediante los que preparar individualmente una oposición. Se podrían fabricar temarios ad-hoc, preguntas y exámenes sintéticos, y hasta usar un agente con acceso a toda esta información como profesor particular.

## Objetivos

El principal objetivo de este proyecto es resolver la siguiente hipótesis:

> Un agente o conjunto de agentes pueden aprobar con la máxima nota cualquier examen de oposición usando fuentes públicas de internet y referenciando adecuadamente cada respuesta.

El resultado de este proceso implicaría la elaboración de un corpus curado de fuentes públicas que, sumado a las bases de convocatoria y preguntas históricas de exámenes, permitirían:

- Generar un temario optimizado, que disponga de todo lo que teóricamente entra en la oposición según las bases, pero que pueda hacer foco en lo que realmente se suele preguntar.
- Generar preguntas y exámenes sintéticos, agrupados por categorías, temas y otras etiquetas, basándose en los formatos de preguntas previas y en los contenidos posibles.
- Habilitar a un agente para que actúe de profesor, dándole acceso a todo este corpus.

## Fases del proyecto

Este proceso, al completo, se probaría en primer lugar sobre una oposición concreta, por ejemplo, la C2_AGE. El flujo sería equivalente para cualquiera otra.

1. Recopilar información pública oficial sobre la oposición, especialmente: exámenes y solucionarios de otros años, bases de convocatoria de otros años.
2. Parsear y extraer datos relevantes de estos documentos: parametrizar preguntas, extraer temarios, identificar formatos... Esto implica también categorizar, tematizar y etiquetar de otras maneras todas las preguntas recopiladas, tareas para las cuales habrá que implicar agentes y, probablemente, acciones manuales.
3. Diseñar e implementar el pipeline de resolución agéntica de preguntas. Hay que garantizar que las preguntas se resuelven usando información pública en internet, priorizando fuentes fiables y comunes. Daríamos por válida la hipótesis si el modelo alcanza un porcentaje de acierto muy alto (digamos, cercano al 99%).
4. De cumplirse la hipótesis, habría que seguir desarrollando el proyecto para alcanzar los otros objetivos, en función del análisis económico: temario, preguntas sintéticas, agente-profesor.