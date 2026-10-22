# Estado actual

## 20/10/2026

- Diseñado el modelo de la batería de preguntas (D010) e implementados
  `opox extract bank`, `opox add bank` y `opox check bank`, con tests.
- Ejecutado `opox extract bank` sobre C2_AGE: 55 fusiones y 15 pares de contextos a
  revisar en `interim/C2_AGE/`. La revisión manual está empezada (4 de 55 fusiones) y
  en pausa.
- **El mecanismo de detección de preguntas iguales se está reevaluando**; el rediseño
  se anotará en `NOTES.md`. Hasta entonces, las hojas, `bank_review.md` y `bank.json`
  generados son provisionales.

## Próximo paso

1. Cerrar el rediseño de la detección de preguntas iguales y contrastarlo con D010.
2. Adaptar la implementación si procede, completar la revisión manual y validar con
   `opox check bank`.
