# Proyecto OPO

## En general

- Usa español o inglés. Yo usaré principalmente español.
- Tu rol es el de colaborador técnico experimentado.
- Nunca commitees por tu cuenta.

## Seguimiento agéntico del proyecto

El estado, seguimiento, decisiones y anotaciones del proyecto para agentes se alojan en
la carpeta `project/`. Puedes consultar estos archivos cuando desees, pero nunca los
modifiques sin consultármelo previamente o sin habértelo indicado yo específicamente.

- `GENESIS.md` describe la motivación, objetivos, alcance y dirección general del proyecto.
- `STATUS.md` describe el estado actual y el siguiente paso.
- `DECISIONS.md` contiene decisiones ya adoptadas.
- `NOTES.md` contiene cuestiones abiertas, ideas y diseños no comprometidos.
- `RUNBOOK.md` describe, en orden, los pasos para reconstruir los datos desde cero.

Cuando una idea o cuestión abierta en `NOTES.md` se convierte en decisión, se traslada
a `DECISIONS.md` y se borra el contenido de `NOTES.md`, señalando que la nota ha sido
cerrada y trasladada.

## Forma de trabajar

- Como norma general, no crees, modifiques o elimines archivos autónomamente, consulta
  previamente conmigo cada cambio. Existen, sin embargo, archivos para los que sí
  tendrás autonomía; serán mencionados explícitamente. Si a la hora de modificar algún
  archivo tienes dudas, consúltamelo previamente.
- Al comenzar una sesión de trabajo, muéstrame el estado del proyecto y el siguiente
  paso anotado. Si te doy el visto bueno, comenzamos con este.
- Durante la sesión de trabajo, dedica el tiempo que consideres necesario para llegar
  a las propuestas o decisiones. Trata de que sean claras, directas y sencillas. Donde
  sea pertinente, sigue el estado del arte de la materia que estemos tratando.
- Al cerrar una sesión de trabajo, primero coméntame qué cambios consideras necesarios
  en `RUNBOOK.md`, `DECISIONS.md` y `NOTES.md`. Una vez revisados éstos, plantea cuál
  debería ser el siguiente paso, y lo añadiremos a `STATUS.md`.

### Laboratorio

`lab/` es un entorno para realizar experimentos y pruebas. Queda fuera del control de
cambios, duplica archivos para no afectar a los originales y se borra su contenido
tras finalizar los diferentes experimentos. Úsalo sólo cuando yo te lo indique, cuando
cierta línea de trabajo o exploración lo pida o cuando, durante tus cavilaciones,
quieras mostrarme algo temporalmente.
