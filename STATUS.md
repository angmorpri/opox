# Estado actual

## 15/10/2026

- Documentos para guiar a los agentes preparados.
- Proyecto Python iniciado como `opox` mediante `uv`.
- Exámenes, solucionarios y bases de convocatoria para la C2_AGE descargados y almacenados.
- Resultados de la iteración previa en `old/`.
- Revisión de incongruencias graves completada: D003 aclarado, contextos cerrados en D005, validez temporal añadida a NOTES.
- Modelo de bases de convocatoria revisado en NOTES (bloques, psicotécnico, identificadores).
- Redefinido el papel de `data/`: `interim/` y `processed/` admiten trabajo de agentes y manual (D002, D005), con protección frente a sobrescrituras (D006). Creado `RUNBOOK.md`.

## Próximo paso

- Definir en `opox`, en inglés, los modelos de bases de convocatoria.
- Extraer las 10 bases de C2_AGE a `processed/C2_AGE/rules/` (agente) y validarlas con un `opox check`. Registrar el paso en `RUNBOOK.md`.
- Continuar con la planificación a bajo nivel del parseo de exámenes y solucionarios.
