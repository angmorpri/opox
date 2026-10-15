# Estado actual

## 15/10/2026

- Documentos para guiar a los agentes preparados.
- Proyecto Python `opox` iniciado mediante `uv`, con CLI (`opox`) y modelos Pydantic (D007).
- Exámenes, solucionarios y bases de convocatoria para la C2_AGE descargados y almacenados.
- Resultados de la iteración previa en `old/`.
- Redefinido el papel de `data/` (D002, D006) y creado `RUNBOOK.md`.
- Bases de convocatoria de C2_AGE extraídas a `processed/C2_AGE/rules.json` y validadas
  con `opox check rules` (D008).
- Diseñados el modelo de preguntas por examen (D009) y el pipeline de contextos (D005).

## Próximo paso

1. Implementar los modelos de preguntas (`models/questions.py`).
2. Implementar `opox extract questions` y `opox check questions`, y revisar los resultados.
3. Script temporal de rescate desde `old/`: generar `contexts.csv` y los recortes a partir
   de los nombres de fichero (no de las asignaciones, incompletas en 5 contextos), y
   comparar las preguntas antiguas con las nuevas.
4. Implementar `opox extract contexts`, `check contexts` y `add contexts`.
5. Documentar los pasos en README y RUNBOOK.
