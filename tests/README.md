# Tests del pipeline MVP

```
$env:TNB_DEMO_ROOT = "C:\Users\javie\OneDrive\Escritorio\Generador_Excel_Enfermedades"
pytest tests -q
```

Cubre: catálogo, jerarquía API→RSS→scrape, normalize, dedup, relevancia &lt;0.15,
estructura de claims, NLI, risk (sin FAKE/REAL), average-hash, CNN heurística,
ciclo con semilla demo → SQLite.
