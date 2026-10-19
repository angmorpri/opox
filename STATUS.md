# Estado actual

## 15/10/2026

- Redefinido el papel de `data/` (D002, D006) y creado `RUNBOOK.md`.
- Bases de convocatoria de C2_AGE extraídas a `processed/C2_AGE/rules.json` y validadas
  con `opox check rules` (D008).
- Diseñados el modelo de preguntas por examen (D009) y el pipeline de contextos (D005).

## Próximo paso

1. Lanzar `opox extract questions` y `opox check questions`, y revisar los resultados.
2. Script temporal de rescate desde `old/`: generar `contexts.csv` y los recortes a partir
   de los nombres de fichero (no de las asignaciones, incompletas en 5 contextos), y
   comparar las preguntas antiguas con las nuevas.
3. Implementar `opox extract contexts`, `check contexts` y `add contexts`.
