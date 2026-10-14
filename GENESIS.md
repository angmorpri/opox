# Proyecto OPO

Inteligencia artificial aplicada a la preparación de oposiciones.

## Motivación

Los mecanismos tradicionales para preparar oposiciones en España están obsoletos. Con
temario público, exámenes de otros años, acceso a internet y agentes IA, se puede renovar,
optimizar y abaratar todo el proceso de preparación de oposiciones.

## Objetivos

La premisa es la siguiente: basándonos en el histórico de convocatorias y exámenes de
una oposición y disponiendo de acceso a internet, se puede crear un **corpus** de
conocimiento formado por fuentes públicas, formatos de preguntas y exámenes,
estadísticas de a qué se le suele dar más importancia... De tal manera que:

- Un agente o conjunto de agentes fueran capaces de resolver cualquier oposición sólo usando este corpus.
- Se pudieran generar compendios o temarios optimizados, que contuvieran tanto lo que teóricamente se puede preguntar como lo que realmente luego se acaba preguntando.
- Se pudieran generar exámenes sintéticos y personalizados, y detectar y actualizar preguntas obsoletas.
- Se pudiera habilitar a un agente para que actúe de profesor particular.

Parte de esto ya se ha llevado a cabo, e internet está plagado de plataformas que usan
IA para ayudarte con oposiciones. El objetivo diferencial de este proyecto será:

- Sólo fuentes públicas y que han probado contener la referencia exacta para resolver preguntas reales de oposición.
- Herramientas innovadoras: corpus como plataforma interactiva, compendios dinámicos, exámenes ajustados al usuario.
- Puerta de entrada gratuita: el corpus y todos o algunos compendios y exámenes sintéticos serán siempre accesibles y gratuitos.

## Fases planteadas

El proyecto es ambicioso, así que primero hay que responder a la siguiente hipótesis:

> ¿Existe un corpus de fuentes públicas y accesibles por internet tal que un agente
> medianamente potente fuera capaz de responder sin fallos cualquier pregunta de
> examen de oposición referenciando claramente la fuente y contenido usado?

Para ello, comenzaremos centrándonos en los **Cuerpos Generales del Estado** ("CGE") y, más
concretamente, en el **Cuerpo General Auxiliar de la Administración del Estado** ("C2_AGE").

### Fase experimental

El objetivo es ver si se cumple la hipótesis, centrándonos en la C2_AGE.

Los pasos propuestos son los siguientes:

1. Recopilar toda información oficial relevante de cada año o convocatoria: reglas, exámenes, solucionarios...
2. Extraer y transformar la información en crudo en datos prácticos: batería de todas las preguntas, categorías, temarios, formatos de pregunta, formatos de examen, estadísticas de contenido...
3. Construir una primera versión del corpus basado en los datos recopilados.
4. Diseñar e implementar un pipeline agéntico que trate de resolver las preguntas recopiladas usando el corpus o hallando nuevas fuentes útiles en internet, referenciando y justificando debidamente cada respuesta.
5. Probar el cumplimiento de la hipótesis.

De cumplirse la hipótesis, se repetiría el proceso completo con otra de las oposiciones
dentro del CGE.

### Fase alfa

Por definir una vez se resuelva la hipótesis.

## Fuentes relevantes

- [Web oficial de los Cuerpos Generales del Estado](https://www.inap.es/es/seleccion/procesos-selectivos-de-cuerposescalas-generales)
- [Web oficial del Cuerpo General Auxiliar de la Administración del Estado](https://www.inap.es/es/seleccion/procesos-selectivos-de-cuerposescalas-generales/cuerpo-general-auxiliar-de-la-administracion-del-estado)

