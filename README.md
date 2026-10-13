# Radar y Memoria de Licitaciones de Obra · G215 S.A.

Versión pública (sin cuenta) de los tableros del proyecto "Radar de Licitaciones".

- `radar/` y `memoria/`: los tableros. Se publican con GitHub Pages.
- `data/memoria.json`: base histórica de la Memoria. La reemplaza la tarea diaria.
- `assets/g215.js`: conecta los tableros con Firestore (marcas en vivo y registro).
- `firestore.rules`: reglas de la base (copia de las publicadas en Firebase).
- Rama `registro`: copia automática del registro de marcas cada 15 minutos (`registro.csv`).

## Actualización diaria

La tarea programada del Radar, después de publicar los artefactos en Claude, corre:

```
python3 scripts/publicar.py --radar <html del Radar> --memoria-html <html de la Memoria> --memoria-dir <export de la Memoria>
git add -A && git commit -m "Datos <fecha>" && git push
```

Si cambia el código de los tableros en Claude, `publicar.py` lo detecta y regenera la versión pública con `scripts/armar_radar.py` y `scripts/armar_memoria.py`. Si un cambio rompe esa adaptación, mantiene la versión anterior con los datos nuevos y lo avisa.
