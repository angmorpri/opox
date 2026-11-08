# Estado actual

## 08/11/2026

- Deduplicación automática mediante `opox extract | check | add duplicates` y
  `opox make bank` (D010 y D011). La única tarea manual obligatoria es la revisión
  de contextos. La revisión manual de duplicados no 100% se vuelve opcional.
- Organización de categorías y temas en `categories.json` mediante `opox extract categories` (D012).

## Próximo paso

1. Decidir el orden de extracción de las *features* y su modelo de almacenamiento.
2. Asignar categorías a la batería: de forma determinista por sección, bloque y tema;
   propagando por duplicados; y clasificando el resto (bloque II de las L y reservas).
