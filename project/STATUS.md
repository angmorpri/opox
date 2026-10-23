# Estado actual

## 23/10/2026

- Cerrados los experimentos de deduplicación de respuestas y enunciados (D011):
  normalización base/extendida, igualdad exacta y revisión manual por similitud
  (respuestas ≥ 70%, enunciados ≥ 75%).
- Propuesto el flujo `opox dedup extract/add/check answers|stems` (NOTES).
- `bank.json`, `bank_review.md` y `opox extract/add/check bank` siguen obsoletos.

## 22/10/2026

- Replanteada la deduplicación de la batería desde cero, mediante experimentos acotados
  en `lab/` cuyas conclusiones se acumulan en D011.
- Primer experimento cerrado: las respuestas se comparan con normalización moderada sin
  mayúsculas.
- `bank.json` y `bank_review.md` de C2_AGE, y la implementación actual de
  `opox extract/add/check bank`, son obsoletos hasta adaptar el código.

## Próximo paso

1. Implementar `opox dedup` para `answers` y `stems`: modelo `dedup.py`, normalización,
   hojas y guías, prefijos de subcomandos y tests. Retirar `opox ... bank`.
2. Probar el pipeline desde cero en C2_AGE: revisión de respuestas (29 casos),
   revisión de enunciados y `check` de ambas etapas. Añadir los pasos al RUNBOOK.
3. Una vez validado, cerrar contextos y distractores, generar `bank.json` y cerrar D010.
