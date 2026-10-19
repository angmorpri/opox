# Estado actual

## 19/10/2026

- Añadido modo `-v` a los comandos de `opox`.
- Preguntas extraídas (1510) y validadas; coinciden con `old/` salvo errores de la
  iteración previa.
- Contextos extraídos, revisados manualmente (47), validados con `opox check contexts` y
  asignados con `opox add contexts`; coinciden con `old/contexts/`.

## 15/10/2026

- Redefinido el papel de `data/` (D002, D006) y creado `RUNBOOK.md`.
- Bases de convocatoria de C2_AGE extraídas a `processed/C2_AGE/rules.json` y validadas
  con `opox check rules` (D008).
- Diseñados el modelo de preguntas por examen (D009) y el pipeline de contextos (D005).

## Próximo paso

1. Diseñar el modelo de la batería de preguntas (Fase 2): criterio de igualdad, contextos
   equivalentes entre modelos y trazabilidad a los exámenes originales.
2. Implementar su generación y validación.
