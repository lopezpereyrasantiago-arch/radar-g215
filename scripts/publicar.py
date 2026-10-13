"""Actualiza la versión pública con los datos del día. Lo corre la tarea diaria del Radar.

Uso:
  python3 scripts/publicar.py --radar /ruta/radar-licitaciones.html --memoria-dir /ruta/export/memoria

--radar        el mismo HTML que se publicó en el artefacto del Radar. Solo se toma su bloque
               <script id="data">; el resto de radar/index.html (versión pública) no se toca.
--memoria-dir  carpeta con la base de la Memoria bajada con ArtifactData (list con out_dir):
               <dir>/licitaciones/*.json, <dir>/contactos/*.json, <dir>/fuentes/*.json, <dir>/config/*.json
               (y <dir>/empresas/*.json si existe). Genera data/memoria.json.
Después hay que hacer git add/commit/push.
"""
import argparse, json, pathlib, re, sys, datetime

RAIZ = pathlib.Path(__file__).resolve().parent.parent
TAG = '<script id="data" type="application/json">'


def bloque(html):
    i = html.find(TAG)
    if i < 0:
        sys.exit('No encontré el bloque de datos <script id="data"> en el HTML.')
    j = html.find('</script>', i + len(TAG))
    return i + len(TAG), j


def radar(src):
    s = pathlib.Path(src).read_text(encoding='utf-8')
    a, b = bloque(s)
    datos = s[a:b]
    d = json.loads(datos.replace('<\\/', '</'))
    dst = RAIZ / 'radar' / 'index.html'
    t = dst.read_text(encoding='utf-8')
    c, e = bloque(t)
    t = t[:c] + datos + t[e:]
    dst.write_text(t, encoding='utf-8')
    return {'items': len(d.get('items', [])), 'generado': d.get('generado')}


def memoria(carpeta):
    base = pathlib.Path(carpeta)
    cols = {}
    for nombre in ['licitaciones', 'contactos', 'fuentes', 'config', 'empresas']:
        dd = base / nombre
        if not dd.is_dir():
            continue
        docs = []
        for f in sorted(dd.glob('*.json')):
            docs.append({'id': f.stem, 'data': json.loads(f.read_text(encoding='utf-8'))})
        cols[nombre] = docs
    if not cols.get('licitaciones'):
        sys.exit(f'No hay licitaciones en {base}/licitaciones: no se publica una Memoria vacía.')
    out = {'generado': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'), 'colecciones': cols}
    dst = RAIZ / 'data' / 'memoria.json'
    dst.parent.mkdir(exist_ok=True)
    dst.write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    return {k: len(v) for k, v in cols.items()}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--radar')
    ap.add_argument('--memoria-dir')
    a = ap.parse_args()
    res = {}
    if a.radar:
        res['radar'] = radar(a.radar)
    if a.memoria_dir:
        res['memoria'] = memoria(a.memoria_dir)
    est = RAIZ / 'data' / 'estado.json'
    est.parent.mkdir(exist_ok=True)
    prev = json.loads(est.read_text()) if est.exists() else {}
    prev.update(res)
    prev['publicado'] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
    est.write_text(json.dumps(prev, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(res, ensure_ascii=False))
