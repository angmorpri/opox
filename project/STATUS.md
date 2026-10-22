# Estado actual

## 22/10/2026

- Replanteada la deduplicación de la batería desde cero, mediante experimentos acotados
  en `lab/` cuyas conclusiones se acumulan en D011.
- Primer experimento cerrado: las respuestas se comparan con normalización moderada sin
  mayúsculas.
- `bank.json` y `bank_review.md` de C2_AGE, y la implementación actual de
  `opox extract/add/check bank`, son obsoletos hasta adaptar el código.

## Próximo paso

1. Siguiente experimento: normalización y similitud del **enunciado** dentro de cada
   grupo de respuestas iguales. Medir cuántos enunciados coinciden exactamente con cada
   normalización y cómo se distribuye la similitud entre los que no coinciden, para
   fijar el criterio de igualdad y de revisión.
2. Después, el contexto (comparación por parejas y caso extremo con contextos dispares)
   y los distractores, hasta cerrar D011 y adaptar la implementación.
