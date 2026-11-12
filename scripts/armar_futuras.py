"""Arma futuras/index.html (versión pública de "Licitaciones a futuro") a partir del HTML del artefacto de Claude.
La página lleva sus datos adentro, así que publicar.py --futuras la regenera completa en cada corrida.
Agrega: Firebase + g215.js (marcas "Quitar novedad" compartidas y registro de quién marcó), links a ../radar/ y
../memoria/, y la escucha en vivo de novedades_vistas."""
import sys, pathlib
src, dst = sys.argv[1], sys.argv[2]
s = pathlib.Path(src).read_text(encoding='utf-8')

HEAD = ('<script src="https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js"></script>'
        '<script src="https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore-compat.js"></script>'
        '<script src="../assets/config.js"></script>'
        '<script src="../assets/g215.js" data-base="../" data-pagina="futuras"></script>'
        '<link rel="icon" href="../assets/icono.svg" type="image/svg+xml">'
        '<meta name="robots" content="noindex">')
LIVE = r'''
/* ---------- G215 versión pública: marcas en vivo para todos ---------- */
onCaps(()=>{ const db=CAP.db; if(!db||!db.live) return;
  db.live('novedades_vistas', docs=>{ Object.keys(VISTOS).forEach(k=>delete VISTOS[k]); Object.keys(VFECHA).forEach(k=>delete VFECHA[k]);
    docs.forEach(d=>{ if(d.data&&d.data.clave){ VISTOS[d.id]=d.data.clave; if(d.data.fecha) VFECHA[d.id]=String(d.data.fecha).slice(0,10); } });
    const a=document.activeElement; if(a&&(a.tagName==='INPUT'&&a.type!=='checkbox'||a.tagName==='SELECT')) return;
    const y=window.scrollY; rerender(); window.scrollTo(0,y); });
});
'''
reps = [
    ('</head>', HEAD + '</head>'),
    ('https://claude.ai/artifact/CtruzYYFohncSC6ZwvUjGs', '../radar/'),
    ('https://claude.ai/artifact/TaetpDjgkuFVwtb1hcC2wF', '../memoria/'),
    ('/*__FIN_FUTURAS__*/', LIVE + '/*__FIN_FUTURAS__*/'),
]
for a, b in reps:
    n = s.count(a)
    if n < 1 or (n != 1 and 'claude.ai/artifact' not in a):
        sys.exit(f'Ancla encontrada {n} veces (se esperaba 1): {a[:60]!r}')
    s = s.replace(a, b)
pathlib.Path(dst).parent.mkdir(parents=True, exist_ok=True)
pathlib.Path(dst).write_text(s, encoding='utf-8')
print('ok', dst, len(s))
