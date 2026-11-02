# Estado actual

## 02/11/2026

- Limpiados los restos de la deduplicación manual (movidos a `old/dedup-manual/`).
  Añadido `testpaths = ["tests"]` a `pyproject.toml` para que pytest ignore `old/`.
- `opox extract questions` y `opox extract contexts` son ahora incrementales por examen;
  `--force` los regenera. `opox add contexts` ya no requiere `--force`: siempre reasigna
  desde la hoja (D005, D006, D009).
- Experimento 1 de la nueva deduplicación automática: umbrales de similitud sobre
  (pregunta, respuesta). Resultados en NOTES.md.

## Próximo paso

1. Inspeccionar las uniones de cada franja de similitud (95–100, 90–95…) y contar
   cuántas tienen respuestas distintas, para fijar el umbral sin falsos positivos.
2. Decidir el mecanismo de agrupación y el tratamiento de los contextos, y trasladarlo
   a D011.
3. Reimplementar la deduplicación y `opox extract bank` (D010).
