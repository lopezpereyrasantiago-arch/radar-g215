"""Arma radar/index.html (versión pública) a partir del HTML del artefacto de Claude.
Se usa una sola vez, o cuando cambie el código del Radar en Claude. El día a día lo hace publicar.py,
que solo reemplaza el bloque de datos."""
import sys, pathlib
src, dst = sys.argv[1], sys.argv[2]
s = pathlib.Path(src).read_text(encoding='utf-8')

HEAD = ('<script src="https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js"></script>'
        '<script src="https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore-compat.js"></script>'
        '<script src="../assets/config.js"></script>'
        '<script src="../assets/g215.js" data-base="../" data-pagina="radar"></script>'
        '<link rel="icon" href="../assets/icono.svg" type="image/svg+xml">'
        '<meta name="robots" content="noindex">')
LIVE = r'''
/* ---------- G215 versión pública: marcas en vivo para todos ---------- */
onCaps(()=>{ const db=CAP.db; if(!db||!db.live) return;
  let pend=false;
  const safe=()=>{ const a=document.activeElement;
    if(a&&(a.tagName==='TEXTAREA'||a.tagName==='SELECT'||(a.tagName==='INPUT'&&a.type!=='checkbox'))){
      if(!pend){ pend=true; a.addEventListener('blur',()=>{ pend=false; setTimeout(safe,0); },{once:true}); } return; }
    const y=window.scrollY; rerender(); window.scrollTo(0,y); };
  db.live('novedades_vistas', docs=>{ Object.keys(VISTOS).forEach(k=>delete VISTOS[k]);
    docs.forEach(d=>{ if(d.data&&d.data.clave) VISTOS[d.id]=d.data.clave; }); safe(); });
  db.live('envios', docs=>{ docs.forEach(d=>{ ENV[d.id]={registros:Array.isArray(d.data&&d.data.registros)?d.data.registros:[]}; }); safe(); });
});
'''
reps = [
    ('</head>', HEAD + '</head>'),
    ('https://claude.ai/artifact/TaetpDjgkuFVwtb1hcC2wF', '../memoria/'),
    ('header(); render(); foot(); route();\n})();', 'header(); render(); foot(); route();\n' + LIVE + '})();'),
]
for a, b in reps:
    n = s.count(a)
    if n < 1 or (n != 1 and 'claude.ai/artifact' not in a):
        sys.exit(f'Ancla encontrada {n} veces (se esperaba 1): {a[:60]!r}')
    s = s.replace(a, b)
pathlib.Path(dst).parent.mkdir(parents=True, exist_ok=True)
pathlib.Path(dst).write_text(s, encoding='utf-8')
print('ok', dst, len(s))
