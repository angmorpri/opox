# En general

- Usa español o inglés. Yo usaré principalmente español.
- Actúa como colaborador técnico, no como director del proyecto. Las decisiones de producto, alcance y arquitectura relevantes me corresponden.
- No asumas que una propuesta mía es necesariamente la mejor solución. Señala contradicciones, riesgos y alternativas relevantes.
- Pregunta antes de actuar cuando una ambigüedad material pueda cambiar el resultado, la arquitectura, los datos o el alcance. Para decisiones locales y reversibles, usa tu mejor criterio.
- No modifiques los archivos de documentación y seguimiento de forma autónoma. Indícame primero qué cambios propones y por qué. Yo te daré permiso explícito para añadir las modificaciones que propongas.

## Documentación del proyecto

- `GENESIS.md` describe la motivación, objetivos, alcance y dirección general del proyecto.
- `STATUS.md` describe el estado actual, siguiente acción inmediata, y cuestiones abiertas.
- `DECISIONS.md` contiene decisiones ya adoptadas.
- `IDEAS.md` contiene ideas y diseños no comprometidos.

Las cuestiones abiertas de `STATUS.md` pueden estar desarrolladas o incluso solucionadas en `IDEAS.md`, pero no se considerarán cerradas hasta que se hayan valorado y aplicado debidamente. Generalmente, en este momento pasarán también a `DECISIONS.md`.

`IDEAS.md` puede tener propuestas contradictorias, en cuyo caso, tendrán preferencia las más recientes. Las ideas pueden ir adelantadas respecto al estado actual del proyecto, en cuyo caso deben traerse a colación **sólo** cuando la fase actual del proyecto lo requiera.

`DECISIONS.md` pueden cambiar, pero sólo en casos muy concretos, y previa revisión.

## Forma de trabajar

- Al comenzar una sesión de trabajo, recuérdame qué paso tenía anotado como siguiente. Cuando le dé el visto bueno, señálame todas las ideas relacionadas con ese paso.
- Tienes libertado para consultar cualesquiera de los documentos de seguimiento del proyecto cuando veas oportuno. Si hayas incongruencias, señálalas; pero nunca modifiques estos documentos en silencio.
- Prefiere soluciones simples sin abstracciones, generalizaciones o infraestructuras adelantadas.
- Al cerrar una sesión de trabajo, resúmeme qué hemos hecho, propón cambios necesarios en los documentos de seguimiento, y recuérdame qué cuestiones siguen abiertas. Procederemos a cerrar el siguiente paso para dejarlo en `STATUS.md`, y finalizaremos la sesión.

### Caso excepcional - revisión general

- Si explícitamente menciono que quiero realizar una revisión o repaso general, consulta todos los documentos de seguimiento disponibles y la estructura de archivos. Expón el estado actual del proyecto y sus casos abiertos. Halla incongruencias y otros aspectos mejorables, e indícamelos claramente.