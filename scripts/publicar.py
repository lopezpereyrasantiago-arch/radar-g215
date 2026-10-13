"""Actualiza la versión pública con los datos del día. Lo corre la tarea diaria del Radar.

Uso:
  python3 scripts/publicar.py --radar /ruta/radar-licitaciones.html --memoria-dir /ruta/export/memoria

--radar        el mismo HTML que se publicó en el artefacto del Radar. Solo se toma su bloque
               <script id="data">; el resto de radar/index.html (versión pública) no se toca.
--memoria-html (opcional) el HTML actual del artefacto "Memoria de Licitaciones" (Artifact action read).
               Si su código cambió desde la última publicación, se regenera memoria/index.html.
--memoria-dir  carpeta con la base de la Memoria bajada con ArtifactData (list con out_dir):
               <dir>/licitaciones/*.json, <dir>/contactos/*.json, <dir>/fuentes/*.json, <dir>/config/*.json
               Genera data/memoria.json (la colección "empresas" no se publica).
Después hay que hacer git add/commit/push.
"""
import argparse, json, pathlib, re, sys, datetime, hashlib, subprocess, tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent
TAG = '<script id="data" type="application/json">'


def bloque(html):
    i = html.find(TAG)
    if i < 0:
        sys.exit('No encontré el bloque de datos <script id="data"> en el HTML.')
    j = html.find('</script>', i + len(TAG))
    return i + len(TAG), j


def huella(html, sin_datos=False):
    if sin_datos:
        a, b = bloque(html)
        html = html[:a] + html[b:]
    return hashlib.sha256(html.encode('utf-8')).hexdigest()[:16]


def rearmar(script, src, dst, avisos):
    """Regenera la versión pública con el código nuevo. Si falla, deja la anterior y avisa."""
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / 'index.html'
        r = subprocess.run([sys.executable, str(RAIZ / 'scripts' / script), str(src), str(tmp)], capture_output=True, text=True)
        if r.returncode != 0:
            avisos.append(f'El código de {dst.parent.name} cambió en Claude pero no se pudo adaptar solo '
                          f'({(r.stdout + r.stderr).strip()[:200]}). Se mantuvo la versión pública anterior con los datos nuevos: '
                          f'hay que pedirle a Claude que actualice scripts/{script}.')
            return False
        dst.write_text(tmp.read_text(encoding='utf-8'), encoding='utf-8')
        return True


def radar(src, estado, avisos):
    s = pathlib.Path(src).read_text(encoding='utf-8')
    a, b = bloque(s)
    datos = s[a:b]
    h = huella(s, sin_datos=True)
    codigo_nuevo = h != estado.get('radar_codigo')
    if codigo_nuevo and rearmar('armar_radar.py', src, RAIZ / 'radar' / 'index.html', avisos):
        estado['radar_codigo'] = h
    d = json.loads(datos.replace('<\\/', '</'))
    dst = RAIZ / 'radar' / 'index.html'
    t = dst.read_text(encoding='utf-8')
    c, e = bloque(t)
    t = t[:c] + datos + t[e:]
    dst.write_text(t, encoding='utf-8')
    return {'items': len(d.get('items', [])), 'generado': d.get('generado'), 'codigo_actualizado': codigo_nuevo and estado.get('radar_codigo') == h}


def memoria_html(src, estado, avisos):
    s = pathlib.Path(src).read_text(encoding='utf-8')
    h = huella(s)
    if h == estado.get('memoria_codigo'):
        return {'codigo_actualizado': False}
    ok = rearmar('armar_memoria.py', src, RAIZ / 'memoria' / 'index.html', avisos)
    if ok:
        estado['memoria_codigo'] = h
    return {'codigo_actualizado': ok}


def memoria(carpeta):
    base = pathlib.Path(carpeta)
    cols = {}
    # 'empresas' (BCRA, autoridades) no se publica: la página no la usa.
    for nombre in ['licitaciones', 'contactos', 'fuentes', 'config']:
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
    ap.add_argument('--memoria-html')
    a = ap.parse_args()
    est = RAIZ / 'data' / 'estado.json'
    est.parent.mkdir(exist_ok=True)
    prev = json.loads(est.read_text()) if est.exists() else {}
    res, avisos = {}, []
    if a.radar:
        res['radar'] = radar(a.radar, prev, avisos)
    if a.memoria_html:
        res['memoria_html'] = memoria_html(a.memoria_html, prev, avisos)
    if a.memoria_dir:
        res['memoria'] = memoria(a.memoria_dir)
    res['avisos'] = avisos
    prev.update(res)
    prev['publicado'] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
    est.write_text(json.dumps(prev, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(res, ensure_ascii=False))
    for x in avisos:
        print('AVISO:', x)
