# Estado actual

## 13/11/2026

- Nuevo CLI `opox <paso> extract|add|check|make [<target>]` (D004): `extract` siempre
  incremental, `--force` con confirmación (D006), `rules extract` muestra las
  instrucciones del agente (D008) y nuevo `categories check`.
- Diseñado el proceso de categorización (D013): acotación determinista por
  intersección y una consulta única al agente que devuelve categoría y tema canónico.

## Próximo paso

1. Definir el criterio de confianza y la calibración (muestra manual de temas).
2. Elegir el modelo gratuito con visión e implementar `opox features extract categories`:
   adaptador por proveedor y caché de respuestas en `interim/`.
