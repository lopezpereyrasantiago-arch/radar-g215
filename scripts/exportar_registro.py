"""Copia el registro de marcas de Firestore a archivos (lo corre GitHub Actions cada 15 minutos).
Genera en la carpeta indicada:
  eventos.jsonl  - un evento por línea, del más viejo al más nuevo (registro completo, solo crece)
  registro.csv   - lo mismo en CSV para abrir en Excel
  marcas.json    - estado actual de "envios" y "novedades_vistas" (lo lee la tarea diaria)
"""
import csv, json, sys, pathlib, urllib.request

PROYECTO = 'radar-g215'
BASE = f'https://firestore.googleapis.com/v1/projects/{PROYECTO}/databases/(default)/documents'
out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'registro')
out.mkdir(parents=True, exist_ok=True)


def val(v):
    if 'stringValue' in v: return v['stringValue']
    if 'integerValue' in v: return int(v['integerValue'])
    if 'doubleValue' in v: return v['doubleValue']
    if 'booleanValue' in v: return v['booleanValue']
    if 'timestampValue' in v: return v['timestampValue']
    if 'nullValue' in v: return None
    if 'arrayValue' in v: return [val(x) for x in v['arrayValue'].get('values', [])]
    if 'mapValue' in v: return {k: val(x) for k, x in v['mapValue'].get('fields', {}).items()}
    return None


def doc(d):
    return {'id': d['name'].rsplit('/', 1)[1], **{k: val(x) for k, x in d.get('fields', {}).items()}}


def post(url, body):
    r = urllib.request.Request(url, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(r, timeout=60))


def listar(col):
    docs, tok = [], None
    while True:
        u = f'{BASE}/{col}?pageSize=300' + (f'&pageToken={tok}' if tok else '')
        j = json.load(urllib.request.urlopen(u, timeout=60))
        docs += [doc(d) for d in j.get('documents', [])]
        tok = j.get('nextPageToken')
        if not tok:
            return docs


def eventos():
    res, ultimo = [], None
    while True:
        q = {'from': [{'collectionId': 'eventos'}], 'orderBy': [{'field': {'fieldPath': 'ts'}, 'direction': 'ASCENDING'}], 'limit': 500}
        if ultimo:
            q['startAt'] = {'values': [{'timestampValue': ultimo['ts']}, {'referenceValue': ultimo['_ref']}], 'before': False}
            q['orderBy'].append({'field': {'fieldPath': '__name__'}, 'direction': 'ASCENDING'})
        else:
            q['orderBy'].append({'field': {'fieldPath': '__name__'}, 'direction': 'ASCENDING'})
        filas = [r for r in post(f'{BASE}:runQuery', {'structuredQuery': q}) if 'document' in r]
        for r in filas:
            d = doc(r['document']); d['_ref'] = r['document']['name']; res.append(d)
        if len(filas) < 500:
            break
        ultimo = res[-1]
    for d in res:
        d.pop('_ref', None)
    return res


ev = eventos()
with open(out / 'eventos.jsonl', 'w', encoding='utf-8') as f:
    for e in ev:
        f.write(json.dumps(e, ensure_ascii=False) + '\n')
CAMPOS = ['ts', 'quien', 'tipo', 'licitacion', 'objeto', 'jurisdiccion', 'empresa', 'email', 'detalle', 'lic_id', 'pagina', 'id']
with open(out / 'registro.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=CAMPOS, extrasaction='ignore')
    w.writeheader()
    for e in ev:
        w.writerow(e)
marcas = {'envios': listar('envios'), 'novedades_vistas': listar('novedades_vistas')}
(out / 'marcas.json').write_text(json.dumps(marcas, ensure_ascii=False, indent=1), encoding='utf-8')
print(f'{len(ev)} eventos, {len(marcas["envios"])} envios, {len(marcas["novedades_vistas"])} novedades quitadas')
