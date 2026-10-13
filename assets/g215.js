/*
 * G215 · puente de datos para la versión pública del Radar y la Memoria.
 *
 * Los tableros se escribieron para claude.ai y piden sus datos con window.claude.use(...).
 * Este archivo da esa misma interfaz fuera de Claude:
 *   - "db": las marcas (envios, novedades_vistas) viven en Firestore y se ven en vivo;
 *           la base histórica de la Memoria se lee de data/memoria.json (la publica la tarea diaria).
 *   - "user": cualquiera puede marcar.
 *   - "downloads": descarga el archivo en el navegador.
 * Cada marca deja un evento en la colección "eventos" (solo se agregan, nunca se borran),
 * con quién la hizo y cuándo.
 */
(function () {
  'use strict';
  var CFG = window.G215_CONFIG || {};
  var BASE = (document.currentScript && document.currentScript.dataset.base) || '../';
  var PAGINA = (document.currentScript && document.currentScript.dataset.pagina) || '';
  var LIVE = { envios: 1, novedades_vistas: 1, eventos: 1 };

  /* ---------- Firestore ---------- */
  var fsPromise = null;
  function fs() {
    if (fsPromise) return fsPromise;
    fsPromise = new Promise(function (res) {
      try {
        if (!window.firebase || !CFG.firebase) return res(null);
        var app = firebase.apps && firebase.apps.length ? firebase.app() : firebase.initializeApp(CFG.firebase);
        res(firebase.firestore(app));
      } catch (e) { console.warn('[G215] Firestore no disponible', e); res(null); }
    });
    return fsPromise;
  }

  /* cache de lo último que se vio de cada documento vivo (para armar el registro de cambios) */
  var CACHE = { envios: {}, novedades_vistas: {} };

  /* ---------- datos estáticos de la Memoria ---------- */
  var staticPromise = null;
  function stat() {
    if (!staticPromise) {
      staticPromise = fetch(BASE + 'data/memoria.json', { cache: 'no-cache' })
        .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
        .then(function (j) { return (j && j.colecciones) || {}; })
        .catch(function (e) { console.warn('[G215] sin data/memoria.json', e); return {}; });
    }
    return staticPromise;
  }

  /* ---------- quién marca ---------- */
  function quien() { try { return localStorage.getItem('g215-quien') || ''; } catch (e) { return ''; } }
  function setQuien(n) { try { localStorage.setItem('g215-quien', n); } catch (e) {} pintarChip(); }
  var pidiendo = null;
  function pedirNombre(forzar) {
    var n = quien();
    if (n && !forzar) return Promise.resolve(n);
    if (pidiendo) return pidiendo;
    pidiendo = new Promise(function (res) {
      var ov = document.createElement('div');
      ov.className = 'g215-ov';
      ov.innerHTML =
        '<form class="g215-dlg" role="dialog" aria-modal="true" aria-labelledby="g215-t">' +
        '<h2 id="g215-t">¿Quién está marcando?</h2>' +
        '<p>Tu nombre queda en el registro junto a cada marca, para saber quién tildó qué y cuándo. Se pide una sola vez en este navegador.</p>' +
        '<input id="g215-n" type="text" maxlength="60" autocomplete="name" placeholder="Nombre y apellido" required>' +
        '<div class="g215-row"><button type="button" class="g215-b2">Cancelar</button><button type="submit" class="g215-b1">Guardar</button></div></form>';
      document.body.appendChild(ov);
      var inp = ov.querySelector('#g215-n'); inp.value = n || ''; setTimeout(function () { inp.focus(); }, 30);
      function fin(v) { ov.remove(); pidiendo = null; res(v); }
      ov.querySelector('form').onsubmit = function (e) { e.preventDefault(); var v = inp.value.trim().slice(0, 60); if (!v) return; setQuien(v); fin(v); };
      ov.querySelector('.g215-b2').onclick = function () { fin(n || null); };
      ov.addEventListener('keydown', function (e) { if (e.key === 'Escape') fin(n || null); });
    });
    return pidiendo;
  }

  /* ---------- registro de eventos ---------- */
  function evento(db, base, extra) {
    var e = Object.assign({
      ts: firebase.firestore.FieldValue.serverTimestamp(),
      cuando: new Date().toISOString(),
      quien: quien() || 'Sin nombre',
      pagina: PAGINA
    }, base, extra || {});
    Object.keys(e).forEach(function (k) {
      if (e[k] === undefined) delete e[k];
      else if (typeof e[k] === 'string') e[k] = e[k].slice(0, k === 'detalle' ? 500 : 300);
    });
    return db.collection('eventos').add(e).catch(function (err) { console.warn('[G215] no se pudo registrar el evento', err); });
  }
  var TIPO_ENVIO = { enviado: 'enviado', abierto: 'correo_abierto', borrador: 'borrador' };
  function diffEnvios(db, id, antes, despues) {
    var meta = { coleccion: 'envios', lic_id: id, licitacion: despues.licitacion, jurisdiccion: despues.jurisdiccion, objeto: despues.objeto };
    var A = {}, B = {};
    ((antes && antes.registros) || []).forEach(function (r) { A[String(r.email || r.empresa || '').toLowerCase()] = r; });
    (despues.registros || []).forEach(function (r) { B[String(r.email || r.empresa || '').toLowerCase()] = r; });
    var ps = [];
    Object.keys(B).forEach(function (k) {
      var r = B[k], p = A[k];
      if (!p || p.tipo !== r.tipo) ps.push(evento(db, meta, { tipo: TIPO_ENVIO[r.tipo] || String(r.tipo || 'marca'), empresa: r.empresa, email: r.email, detalle: r.via ? 'vía ' + r.via : undefined }));
    });
    Object.keys(A).forEach(function (k) {
      if (!B[k]) ps.push(evento(db, meta, { tipo: 'envio_destildado', empresa: A[k].empresa, email: A[k].email, detalle: 'antes: ' + (A[k].tipo || '') }));
    });
    return Promise.all(ps);
  }

  /* ---------- API compatible con claude.use("db") ---------- */
  function wrapDoc(id, data) { return { id: id, data: function () { return data; } }; }
  function Coll(name) { this.name = name; this.n = 1000; }
  Coll.prototype.limit = function (n) { this.n = n; return this; };
  Coll.prototype.get = function () {
    var name = this.name, n = this.n;
    if (LIVE[name]) {
      return fs().then(function (db) {
        if (!db) throw { code: 'unavailable' };
        return db.collection(name).limit(n).get().then(function (s) {
          return { docs: s.docs.map(function (d) { var v = d.data(); if (CACHE[name]) CACHE[name][d.id] = v; return wrapDoc(d.id, v); }) };
        });
      });
    }
    return stat().then(function (c) { return { docs: (c[name] || []).slice(0, n).map(function (d) { return wrapDoc(d.id, d.data); }) }; });
  };
  Coll.prototype.doc = function (id) { return new Doc(this.name + '/' + id); };

  function Doc(path) { var p = path.split('/'); this.c = p[0]; this.id = p.slice(1).join('/'); }
  Doc.prototype.get = function () {
    var c = this.c, id = this.id;
    if (LIVE[c]) {
      return fs().then(function (db) {
        if (!db) throw { code: 'unavailable' };
        return db.collection(c).doc(id).get().then(function (s) {
          var v = s.exists ? s.data() : null; if (CACHE[c]) CACHE[c][id] = v;
          return { exists: s.exists, data: function () { return v; } };
        });
      });
    }
    return stat().then(function (cc) {
      var d = (cc[c] || []).filter(function (x) { return x.id === id; })[0];
      return { exists: !!d, data: function () { return d ? d.data : null; } };
    });
  };
  Doc.prototype.set = function (data) {
    var c = this.c, id = this.id;
    if (!LIVE[c] || c === 'eventos') return Promise.reject({ code: 'read_only' });
    return pedirNombre().then(function (n) {
      if (!n) throw { code: 'declined' };
      return fs();
    }).then(function (db) {
      if (!db) throw { code: 'unavailable' };
      var ref = db.collection(c).doc(id);
      var antes = CACHE[c][id];
      var pre = antes === undefined ? ref.get().then(function (s) { return s.exists ? s.data() : null; }) : Promise.resolve(antes);
      return pre.then(function (prev) {
        return ref.set(data).then(function () {
          CACHE[c][id] = data;
          if (c === 'envios') return diffEnvios(db, id, prev, data);
          if (c === 'novedades_vistas') return evento(db, { coleccion: c, lic_id: id, objeto: data.objeto, tipo: 'novedad_quitada', detalle: data.clave });
        });
      });
    });
  };
  Doc.prototype.delete = function () {
    var c = this.c, id = this.id;
    if (c !== 'novedades_vistas') return Promise.reject({ code: 'read_only' });
    return pedirNombre().then(function (n) {
      if (!n) throw { code: 'declined' };
      return fs();
    }).then(function (db) {
      if (!db) throw { code: 'unavailable' };
      var prev = CACHE[c][id];
      return db.collection(c).doc(id).delete().then(function () {
        delete CACHE[c][id];
        return evento(db, { coleccion: c, lic_id: id, objeto: prev && prev.objeto, tipo: 'novedad_restaurada', detalle: prev && prev.clave });
      });
    });
  };

  var dbApi = {
    collection: function (name) { return new Coll(name); },
    doc: function (path) { return new Doc(path); },
    /* Suscripción en vivo: cb([{id, data}]) cada vez que cambia la colección. */
    live: function (name, cb, opts) {
      opts = opts || {};
      return fs().then(function (db) {
        if (!db) return null;
        var q = db.collection(name);
        if (opts.orderBy) q = q.orderBy(opts.orderBy, opts.dir || 'asc');
        q = q.limit(opts.limit || 2000);
        return q.onSnapshot(function (s) {
          var docs = s.docs.map(function (d) { var v = d.data(); if (CACHE[name]) CACHE[name][d.id] = v; return { id: d.id, data: v }; });
          try { cb(docs); } catch (e) { console.error(e); }
        }, function (err) { console.warn('[G215] suscripción', name, err); });
      });
    }
  };

  var userApi = {
    can: function () { return Promise.resolve(true); },
    canEdit: function () { return Promise.resolve(false); },
    isOwner: function () { return Promise.resolve(false); },
    nombre: quien,
    cambiarNombre: function () { return pedirNombre(true); }
  };

  var dlApi = {
    save: function (o) {
      try {
        var blob = o.data instanceof Blob ? o.data : new Blob([o.data], { type: /\.xlsx$/i.test(o.filename) ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' : 'text/plain;charset=utf-8' });
        var a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = o.filename || 'archivo';
        document.body.appendChild(a); a.click(); setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1500);
        return Promise.resolve();
      } catch (e) { return Promise.reject({ code: 'error' }); }
    }
  };

  window.claude = {
    use: function (name) {
      if (name === 'db') return fs().then(function () { return dbApi; });
      if (name === 'user') return Promise.resolve(userApi);
      if (name === 'downloads') return Promise.resolve(dlApi);
      return Promise.resolve(null);
    }
  };
  window.G215 = { db: dbApi, quien: quien, cambiarNombre: function () { return pedirNombre(true); } };

  /* ---------- estilos del diálogo y chip de nombre ---------- */
  var css = document.createElement('style');
  css.textContent =
    '.g215-ov{position:fixed;inset:0;background:rgba(10,20,18,.45);display:flex;align-items:center;justify-content:center;z-index:50;padding:16px}' +
    '.g215-dlg{background:var(--surface,#fff);color:var(--ink,#18221F);border:1px solid var(--line,#D3DAD4);border-radius:12px;padding:20px;max-width:420px;width:100%;display:flex;flex-direction:column;gap:10px;font:15px/1.5 var(--body,system-ui,sans-serif)}' +
    '.g215-dlg h2{margin:0;font:700 20px/1.2 var(--display,system-ui,sans-serif)}' +
    '.g215-dlg p{margin:0;color:var(--muted,#56655F);font-size:14px}' +
    '.g215-dlg input{font:15px var(--body,system-ui,sans-serif);padding:9px 11px;border:1px solid var(--line,#D3DAD4);border-radius:8px;background:var(--ground,#F1F4F2);color:inherit}' +
    '.g215-row{display:flex;gap:8px;justify-content:flex-end}' +
    '.g215-row button{font:600 14px var(--body,system-ui,sans-serif);padding:9px 14px;border-radius:8px;cursor:pointer;border:1px solid var(--line,#D3DAD4);background:var(--surface,#fff);color:inherit}' +
    '.g215-row .g215-b1{background:var(--accent,#1D5C78);border-color:var(--accent,#1D5C78);color:var(--accent-ink,#fff)}' +
    '.g215-chip{position:fixed;left:12px;bottom:calc(12px + env(safe-area-inset-bottom,0px));z-index:15;font:12.5px var(--mono,ui-monospace,monospace);background:var(--surface,#fff);color:var(--muted,#56655F);border:1px solid var(--line,#D3DAD4);border-radius:999px;padding:6px 11px;cursor:pointer}' +
    '.g215-chip b{color:var(--ink,#18221F);font-weight:500}';
  document.head.appendChild(css);
  function pintarChip() {
    var n = quien(), ch = document.querySelector('.g215-chip');
    if (!n) { if (ch) ch.remove(); return; }
    if (!ch) { ch = document.createElement('button'); ch.type = 'button'; ch.className = 'g215-chip'; ch.title = 'Cambiar el nombre con el que marcás'; ch.onclick = function () { pedirNombre(true); }; document.body.appendChild(ch); }
    ch.innerHTML = 'Marcando como <b></b> · cambiar'; ch.querySelector('b').textContent = n;
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', pintarChip); else pintarChip();
})();
