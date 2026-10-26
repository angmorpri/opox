# Estado actual

## 26/10/2026

- Implementado `opox dedup extract/add/check answers|stems|contexts` y
  `opox dedup check all` (D011), con prefijos de subcomandos en toda la CLI (D004).
- Ejecutada la deduplicación en C2_AGE: 1493 preguntas con respuesta dan 963 únicas.
  Distractores unidos sólo por igualdad exacta con normalización base (D011).
- Implementado `opox extract bank` y `opox check bank`; generado `bank.json` con
  963 entradas y 2919 distractores. Cerrado D010. Añadidos los pasos 6 a 9 al RUNBOOK.

## Próximo paso

1. Diseñar el modelo de categorías ("Modelo de datos para C2_AGE" en NOTES): extraerlas
   de los bloques de `rules.json` y organizar los temarios de cada convocatoria.
2. Asignar las categorías a la batería, como primera *feature* (NOTES, "Extracción de
   *features* de preguntas").
