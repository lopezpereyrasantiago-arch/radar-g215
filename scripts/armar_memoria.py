"""Arma memoria/index.html (versión pública) a partir del HTML del artefacto "Memoria de Licitaciones".
Agrega: lectura de la base desde data/memoria.json, los "Enviado" del Radar en vivo en "Empresas y contactos",
y la pestaña "Registro" con cada marca (quién y cuándo). Se usa solo si cambia el código de la Memoria en Claude."""
import sys, pathlib
src, dst = sys.argv[1], sys.argv[2]
s = pathlib.Path(src).read_text(encoding='utf-8')

HEAD = ('<script src="https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js"></script>'
        '<script src="https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore-compat.js"></script>'
        '<script src="../assets/config.js"></script>'
        '<script src="../assets/g215.js" data-base="../" data-pagina="memoria"></script>'
        '<link rel="icon" href="../assets/icono.svg" type="image/svg+xml">'
        '<meta name="robots" content="noindex">')

LIVE_FUNCS = r'''
/* ---------- G215 versión pública: Enviados del Radar en vivo + Registro ---------- */
let ENVLIVE=[], EVENTOS=[], EVOK=false, EVERR=false;
const fmtD=f=>{ const m=String(f||'').match(/^(\d{4})-(\d{2})-(\d{2})/); return m?`${m[3]}/${m[2]}/${m[1]}`:String(f||''); };
function mergeLive(c){
  const base=(c.contactos||[]).slice(); if(!ENVLIVE.length) return base;
  const em=String(c.email||'').toLowerCase(), extra=String(c.emails_extra||'').toLowerCase();
  const keys=new Set([c.empresa,...String(c.otros_nombres||'').split(';')].map(x=>x&&normEmp(x)).filter(Boolean));
  ENVLIVE.forEach(d=>{ const lic=String((d.data&&d.data.licitacion)||'');
    ((d.data&&d.data.registros)||[]).forEach(r=>{ if(r.tipo!=='enviado') return;
      const re=String(r.email||'').toLowerCase();
      const hit=(re&&(re===em||(extra&&extra.includes(re))))||(r.empresa&&keys.has(normEmp(r.empresa)));
      if(!hit) return;
      const dup=base.some(x=>String(x.email||c.email||'').toLowerCase()===re&&(String(x.licitacion||'')===lic||fkey(x.fecha)===String(r.fecha||'').slice(0,10)));
      if(dup) return;
      base.push({fecha:fmtD(r.fecha),tipo:'especifico',licitacion:lic,estado:'Enviado',email:r.email,_live:true}); }); });
  return base;
}
function liveRender(tab){
  if(S.tab!==tab) return;
  const a=document.activeElement; if(a&&$('out').contains(a)&&/^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName)) return;
  const y=window.scrollY; render(); window.scrollTo(0,y);
}
const EVT={enviado:'Marcó enviado',correo_abierto:'Abrió el correo',borrador:'Preparó borrador',envio_destildado:'Destildó un envío',novedad_quitada:'Quitó la novedad',novedad_restaurada:'Restauró la novedad',importado:'Marca importada de Claude'};
function evFecha(e){ try{ if(e.ts&&e.ts.toDate) return e.ts.toDate(); }catch(x){} return e.cuando?new Date(e.cuando):null; }
const fdt=d=>d?d.toLocaleString('es-AR',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'}):'—';
function evFiltrados(){
  const q=plain(S.rq||'');
  return EVENTOS.map(d=>d.data||{}).filter(e=>(!S.rt||e.tipo===S.rt)&&(!S.rw||e.quien===S.rw)&&(!q||plain([e.quien,e.licitacion,e.objeto,e.empresa,e.email,e.jurisdiccion,e.detalle].join(' ')).includes(q)));
}
function renderRegistro(){
  $('c-registro').textContent=EVENTOS.length||'';
  if(!EVOK){ $('out').innerHTML=`<div class="empty">${EVERR?'No se pudo conectar con el registro. Recargá la página.':'Cargando el registro…'}</div>`; return; }
  const L=evFiltrados();
  const tipos=[...new Set(EVENTOS.map(d=>d.data&&d.data.tipo).filter(Boolean))];
  const quienes=[...new Set(EVENTOS.map(d=>d.data&&d.data.quien).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'es'));
  $('out').innerHTML=`<div class="panel">
    <div class="ptools"><input type="search" id="rq" placeholder="Buscar persona, licitación, empresa o email…" value="${esc(S.rq||'')}" aria-label="Buscar en el registro" style="flex:1 1 240px">
      <div class="f"><label for="rt">Acción</label><select id="rt"><option value="">Todas</option>${tipos.map(t=>`<option value="${esc(t)}"${S.rt===t?' selected':''}>${esc(EVT[t]||t)}</option>`).join('')}</select></div>
      <div class="f"><label for="rw">Quién</label><select id="rw"><option value="">Todos</option>${quienes.map(t=>`<option${S.rw===t?' selected':''}>${esc(t)}</option>`).join('')}</select></div>
      <button class="btn" id="rx" type="button">Exportar registro</button>
      <span class="h">Cada marca que se hace en el Radar queda acá con quién la hizo y cuándo, en el momento. El registro no se puede borrar ni editar desde la página. Los filtros de arriba no aplican a esta pestaña.</span></div>
    ${L.length?`<div class="tw"><table><tr><th>Fecha y hora</th><th>Quién</th><th>Acción</th><th>Licitación</th><th>Empresa</th><th>Detalle</th></tr>
      ${L.slice(0,1000).map(e=>`<tr><td class="n">${fdt(evFecha(e))}</td><td><b>${esc(e.quien)}</b></td>
        <td><span class="pill ${/enviado|importado/.test(e.tipo)?'win':/destild|restaur/.test(e.tipo)?'sec':''}">${esc(EVT[e.tipo]||e.tipo)}</span></td>
        <td style="min-width:220px">${esc(e.objeto||e.licitacion||'')}<div class="sub">${esc([e.jurisdiccion,e.licitacion&&e.objeto?e.licitacion:''].filter(Boolean).join(' · '))}</div></td>
        <td style="min-width:170px">${esc(e.empresa||'')}${e.email?`<div class="sub">${esc(e.email)}</div>`:''}</td>
        <td><span class="sub">${esc(e.detalle||'')}</span></td></tr>`).join('')}
    </table></div>${L.length>1000?`<div class="note">Se muestran los 1000 más recientes de ${L.length}. Exportá para verlos todos.</div>`:''}`
    :`<div class="empty">${EVENTOS.length?'Ningún evento coincide con la búsqueda.':'Todavía no hay marcas registradas. Cuando alguien tilde "Enviado" o "Quitar novedad" en el Radar, aparece acá.'}</div>`}
  </div>`;
  $('rq').oninput=e=>{S.rq=e.target.value; const p=e.target.selectionStart; render(); const n=$('rq'); if(n){n.focus(); n.setSelectionRange(p,p);} };
  $('rt').onchange=e=>{S.rt=e.target.value; render();};
  $('rw').onchange=e=>{S.rw=e.target.value; render();};
  $('rx').onclick=exportRegistro;
}
async function exportRegistro(){
  if(typeof XLSX==='undefined'){ toast('No se pudo cargar el generador de Excel. Recargá la página.'); return; }
  const rows=evFiltrados().map(e=>({Fecha_hora:fdt(evFecha(e)),Quien:e.quien||'',Accion:EVT[e.tipo]||e.tipo||'',Licitacion:e.licitacion||'',Objeto:e.objeto||'',Jurisdiccion:e.jurisdiccion||'',Empresa:e.empresa||'',Email:e.email||'',Detalle:e.detalle||'',Id_licitacion:e.lic_id||''}));
  const wb=XLSX.utils.book_new(); XLSX.utils.book_append_sheet(wb,XLSX.utils.json_to_sheet(rows),'Registro');
  const dl=await window.claude.use('downloads'); await dl.save({filename:'registro-marcas-radar.xlsx',data:XLSX.write(wb,{type:'array',bookType:'xlsx'})}); toast('Registro exportado');
}
'''

SUBS = r'''D=R.map(derive); selects(); render();
  if(db.live){
    db.live('envios',docs=>{ ENVLIVE=docs; liveRender('contactos'); });
    db.live('eventos',docs=>{ EVENTOS=docs; EVOK=true; if(S.tab==='registro') liveRender('registro'); else $('c-registro').textContent=docs.length||''; },{orderBy:'ts',dir:'desc',limit:3000})
      .then(u=>{ if(!u){ EVERR=true; liveRender('registro'); } });
  }'''

reps = [
    ('</head>', HEAD + '</head>'),
    ('https://claude.ai/artifact/CtruzYYFohncSC6ZwvUjGs', '../radar/'),
    ('<button class="tab" role="tab" data-t="metodo" aria-selected="false">Método</button>',
     '<button class="tab" role="tab" data-t="registro" aria-selected="false">Registro<span id="c-registro"></span></button>\n    <button class="tab" role="tab" data-t="metodo" aria-selected="false">Método</button>'),
    ('Cargando la base histórica. Si no aparece nada, abrí esta página desde claude.ai con tu cuenta.', 'Cargando la base histórica…'),
    ('Esta vista no puede leer la base histórica. Abrí la página desde claude.ai con tu cuenta.', 'No se pudo leer la base histórica. Recargá la página.'),
    ("cq:'',cf:'todas',co:'pres'};", "cq:'',cf:'todas',co:'pres',rq:'',rt:'',rw:''};"),
    ('const cs=(c.contactos||[]).slice().sort(', 'const cs=mergeLive(c).sort('),
    ("${x.casilla_compartida?' <span class=\"pill small\">casilla compartida</span>':''}",
     "${x.casilla_compartida?' <span class=\"pill small\">casilla compartida</span>':''}${x._live?' <span class=\"pill small\">desde el Radar, en vivo</span>':''}"),
    ('metodo:renderMetodo})[S.tab](L);', 'metodo:renderMetodo,registro:renderRegistro})[S.tab](L);'),
    ("/* ---------- Excel ---------- */", LIVE_FUNCS + "\n/* ---------- Excel ---------- */"),
    ("XLSX.utils.book_append_sheet(wb,XLSX.utils.json_to_sheet(ct),'Contactos');\n  }",
     "XLSX.utils.book_append_sheet(wb,XLSX.utils.json_to_sheet(ct),'Contactos');\n  }\n  if(EVENTOS.length){ XLSX.utils.book_append_sheet(wb,XLSX.utils.json_to_sheet(EVENTOS.map(d=>d.data||{}).map(e=>({Fecha_hora:fdt(evFecha(e)),Quien:e.quien||'',Accion:EVT[e.tipo]||e.tipo||'',Licitacion:e.licitacion||'',Objeto:e.objeto||'',Empresa:e.empresa||'',Email:e.email||'',Detalle:e.detalle||''}))),'Registro'); }"),
    ('D=R.map(derive); selects(); render();\n}', SUBS + '\n}'),
]
for a, b in reps:
    n = s.count(a)
    if n < 1 or (n != 1 and 'claude.ai/artifact' not in a):
        sys.exit(f'Ancla encontrada {n} veces: {a[:70]!r}')
    s = s.replace(a, b)
pathlib.Path(dst).parent.mkdir(parents=True, exist_ok=True)
pathlib.Path(dst).write_text(s, encoding='utf-8')
print('ok', dst, len(s))
