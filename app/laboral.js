// =====================================================================
// BeeHuman · Etapa 1 · Historia laboral e IDSE (altas)
// Toda regla vive en la base (funciones laboral_* e idse_*): esta pantalla
// solo la refleja y llama a esas funciones. El navegador no escribe en las
// tablas de historial (no tiene permiso).
// Usa del archivo principal: sb, rolActual, empresas, escapeHtml,
// detalleActual, abrirDetalle, cargarPersonal.
// =====================================================================
(function () {
  'use strict';
  const esc = (v) => (typeof escapeHtml === 'function' ? escapeHtml(v == null ? '' : String(v)) : String(v == null ? '' : v));
  const puedeOperar = () => ['administrador', 'nomina'].includes(rolActual);
  const esAdmin = () => rolActual === 'administrador';
  const fechaMx = (f) => { if (!f) return '—'; const [a, m, d] = String(f).slice(0, 10).split('-'); return `${d}/${m}/${a}`; };
  const dinero = (n) => (n == null || n === '' ? '—' : Number(n).toLocaleString('es-MX', { style: 'currency', currency: 'MXN' }));
  const msgError = (e) => {
    const t = (e && (e.message || e.details || e.hint)) || String(e || 'Error');
    return t.replace(/^BeeHuman:\s*/, '');
  };

  const TIPOS = { ingreso: 'Ingreso', reingreso: 'Reingreso', baja: 'Baja', modificacion_salario: 'Modificación de salario',
    cambio_esquema_pago: 'Esquema de pago', cambio_puesto: 'Cambio de puesto', cambio_jefe: 'Cambio de jefe directo',
    cambio_organizacion: 'Cambio de organización', cambio_registro_patronal: 'Cambio de registro patronal',
    cambio_empresa: 'Cambio de empresa', correccion_datos: 'Corrección de datos' };
  const TIPOS_IMSS = ['ingreso', 'reingreso', 'baja', 'modificacion_salario'];
  const TIPO_TRAB = { '1': 'Permanente', '2': 'Eventual de la ciudad', '3': 'Eventual de la construcción', '4': 'Eventual del campo' };
  const TIPO_SAL = { '0': 'Fijo', '1': 'Variable', '2': 'Mixto' };
  const JORNADA = { '0': 'Semana completa', '1': '1 día', '2': '2 días', '3': '3 días', '4': '4 días', '5': '5 días', '6': 'Jornada reducida' };
  const IDSE_ESTADO = { pendiente: 'IDSE pendiente', en_archivo: 'IDSE en archivo', presentado: 'IDSE presentado',
    confirmado: 'IDSE confirmado', rechazado: 'IDSE rechazado', cancelado: 'IDSE cancelado' };
  const PENDIENTE = { sin_fecha_ingreso: 'Sin fecha de ingreso', baja_sin_fecha: 'Baja sin fecha', historica_por_reconstruir: 'Empleo anterior por reconstruir' };
  const ETIQUETAS = { empresa: 'Empresa', registro_patronal: 'Registro patronal', fecha_ingreso: 'Ingreso', fecha_baja: 'Baja',
    fecha_reconocimiento_antiguedad: 'Antigüedad reconocida', sbc: 'SBC', sdi: 'SDI', numero_interno: 'Número interno',
    tipo_trabajador: 'Tipo de trabajador', tipo_salario: 'Tipo de salario', jornada: 'Jornada', umf: 'UMF',
    puesto: 'Puesto', jefe: 'Jefe directo', area: 'Área', departamento: 'Departamento', localidad: 'Localidad',
    centro_costo: 'Centro de costo', proyecto: 'Proyecto', coordinador: 'Coordinador', coordinador_externo: 'Coordinador externo',
    clasificacion: 'Clasificación', sueldo: 'Importe', modalidad_sueldo: 'Modalidad', periodicidad: 'Periodicidad',
    dias_periodo: 'Días del periodo', activo: 'Activo', causa_baja: 'Causa', comentario_baja: 'Comentario', estado: 'Estado' };
  const OCULTAR = ['empresa_id', 'registro_patronal_id', 'puesto_id', 'jefe_id', 'area_id', 'departamento_id', 'localidad_id',
    'centro_costo_id', 'proyecto_id', 'coordinador_id', 'esquemas_desactivados', 'fecha_ingreso_origen'];
  function valorLegible(k, v) {
    if (v == null || v === '') return '—';
    if (k === 'tipo_trabajador') return TIPO_TRAB[v] || v;
    if (k === 'tipo_salario') return TIPO_SAL[v] || v;
    if (k === 'jornada') return JORNADA[v] || v;
    if (k === 'causa_baja') return (causas.find((c) => c.codigo === v) || {}).descripcion || v;
    if (/^fecha/.test(k)) return fechaMx(v);
    if (['sbc', 'sdi', 'sueldo'].includes(k)) return dinero(v);
    if (k === 'activo') return v ? 'Sí' : 'No';
    return v;
  }

  // ---------- estilos (línea visual V2.1) ----------
  const css = `
.hl-wrap{font-size:13.5px}
.hl-cab{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin:0 0 12px}
.hl-cab h3{margin:0}
.hl-card{border:1px solid var(--v21-borde,#E5E9F1);border-radius:12px;padding:14px 16px;margin:0 0 14px;background:var(--v21-superficie,#fff)}
.hl-card.baja{background:#FAFBFD}
.hl-card h4{margin:0 0 6px;font-size:14.5px;color:var(--v21-navy,#16264A);display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.hl-datos{display:flex;gap:6px 16px;flex-wrap:wrap;color:var(--v21-texto-2,#5B6680);margin:4px 0 8px}
.hl-datos b{color:var(--v21-texto,#16264A);font-weight:600}
.hl-chip{display:inline-block;border-radius:999px;padding:2px 9px;font-size:11.5px;font-weight:600;background:#EEF2F8;color:#3B4A6B}
.hl-chip.vigente{background:#E8F4E5;color:#1F6B33}.hl-chip.baja{background:#FDECEA;color:#A33A3A}
.hl-chip.aviso{background:#FFF3D6;color:#8A6400}.hl-chip.idse{background:#EAF0FB;color:#24427A}
.hl-chip.idse.rechazado{background:#FDECEA;color:#A33A3A}.hl-chip.idse.confirmado{background:#E8F4E5;color:#1F6B33}
.hl-acc{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}
.hl-acc button,.hl-form button{margin:0}
.hl-btn2{background:#fff;color:var(--v21-navy,#16264A);border:1px solid var(--v21-borde,#E5E9F1);border-radius:9px;padding:7px 13px;font:600 12.5px Inter,sans-serif;cursor:pointer}
.hl-btn2.peligro{color:#B42318;border-color:#F2C6C0}
.hl-linea{list-style:none;margin:8px 0 0;padding:0;border-left:2px solid var(--v21-borde,#E5E9F1)}
.hl-linea li{position:relative;padding:6px 0 8px 16px}
.hl-linea li::before{content:"";position:absolute;left:-6px;top:11px;width:10px;height:10px;border-radius:50%;background:#C9D2E3}
.hl-linea li.imss::before{background:var(--v21-navy,#16264A)}
.hl-linea li.anulado{opacity:.55}.hl-linea li.anulado .hl-tit{text-decoration:line-through}
.hl-tit{font-weight:600;color:var(--v21-texto,#16264A)}
.hl-meta{color:var(--v21-texto-2,#5B6680);font-size:12px}
.hl-cambios{margin:3px 0 0;color:var(--v21-texto,#16264A)}
.hl-cambios span{display:inline-block;margin:0 12px 0 0}
.hl-form{border:1px dashed #C9D2E3;border-radius:10px;padding:12px;margin:8px 0;background:#FBFCFE}
.hl-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px 12px;align-items:end}
.hl-grid label{display:block;font-size:12px;font-weight:600;color:var(--v21-texto-2,#5B6680);margin:0 0 4px}
.hl-grid input,.hl-grid select{width:100%;box-sizing:border-box}
.hl-msg{margin:8px 0;padding:8px 12px;border-radius:9px;font-size:13px;display:none}
.hl-msg.ok{display:block;background:#E8F4E5;color:#1F6B33}.hl-msg.err{display:block;background:#FDECEA;color:#B42318}
.hl-pend{border:1px solid #F4D99A;background:#FFFBEF;border-radius:12px;padding:12px 14px;margin:0 0 14px}
.hl-bloqueado{font-size:12px;color:#8A6400;margin:4px 0 0}
#panel-idse .idse-tabla{width:100%;border-collapse:collapse;font-size:13px}
#panel-idse .idse-tabla th,#panel-idse .idse-tabla td{text-align:left;padding:8px;border-bottom:1px solid var(--v21-borde,#E5E9F1);vertical-align:top}
#panel-idse .idse-err{color:#B42318;font-size:12px}#panel-idse .idse-aviso{color:#8A6400;font-size:12px}
@media (max-width:640px){.hl-card{padding:12px}.hl-grid{grid-template-columns:1fr}}
`;
  const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);

  // ---------- datos compartidos ----------
  let causas = [];
  let rps = [];
  async function cargarCatalogos() {
    const [c, r] = await Promise.all([
      sb.from('causas_baja').select('codigo,descripcion').eq('activo', true).order('codigo'),
      sb.from('empresas_registros_patronales').select('id,empresa_id,registro_patronal,activo,guia_idse,zona_salario_minimo').order('registro_patronal'),
    ]);
    if (!c.error) causas = c.data || [];
    if (!r.error) rps = r.data || [];
  }
  const nombreEmpresa = (id) => ((typeof empresas !== 'undefined' ? empresas : []).find((e) => e.id === id) || {}).nombre || '—';
  const textoRP = (id) => (rps.find((r) => r.id === id) || {}).registro_patronal || null;
  const opciones = (mapa, sel) => '<option value="">Sin capturar</option>' +
    Object.entries(mapa).map(([k, v]) => `<option value="${k}" ${String(sel) === k ? 'selected' : ''}>${k} · ${esc(v)}</option>`).join('');

  // =====================================================================
  // Historia laboral (sección de la ficha)
  // =====================================================================
  let estado = { personaId: null, persona: null, relaciones: [], eventos: [], pendientes: [], formAbierto: null };
  let fichaBloqueadaPara = null; // id de la persona cuya ficha tiene bloqueados los datos de Historia laboral
  let msgPendiente = null; // mensaje a mostrar después de volver a pintar

  async function alAbrirDetalle(p) {
    const raiz = document.getElementById('hl-raiz');
    if (!raiz || !p) return;
    estado = { personaId: p.id, persona: p, relaciones: [], eventos: [], pendientes: [], formAbierto: null };
    bloquearFicha(false);
    raiz.innerHTML = '<p class="hint">Cargando historia laboral…</p>';
    if (!causas.length || !rps.length) await cargarCatalogos();
    const id = p.id;
    const [rel, hist, pend] = await Promise.all([
      sb.from('relaciones_laborales').select('*').eq('personal_id', id),
      sb.rpc('laboral_historial', { p_personal_id: id }),
      sb.from('personal_registros_pago').select('id,sueldo,modalidad_sueldo,empresa_id,registro_patronal_id,clasificacion_id,fecha_inicio')
        .eq('personal_id', id).eq('activo', true).is('relacion_laboral_id', null),
    ]);
    if (estado.personaId !== id) return; // se abrió otra ficha mientras cargaba
    if (rel.error || hist.error) {
      raiz.innerHTML = `<div class="hl-msg err">No se pudo cargar la historia laboral: ${esc(msgError(rel.error || hist.error))}</div>`;
      return;
    }
    estado.relaciones = (rel.data || []).filter((r) => r.estado !== 'anulada');
    estado.eventos = hist.data || [];
    estado.pendientes = pend.error ? [] : (pend.data || []);
    bloquearFicha(estado.relaciones.length > 0);
    pintar();
  }

  // Con historial, estos datos solo cambian desde aquí (la base lo exige).
  function bloquearFicha(si) {
    fichaBloqueadaPara = si ? estado.personaId : null;
    ['d-empresa', 'd-registro-patronal', 'd-numero-interno', 'd-fechabaja', 'd-comentariobaja'].forEach((idc) => {
      const el = document.getElementById(idc); if (!el) return;
      el.disabled = si; el.title = si ? 'Se registra en Historia laboral' : '';
    });
    const est = document.getElementById('d-estatus');
    if (est) {
      const enBaja = est.value === 'Baja';
      est.disabled = si && enBaja;
      [...est.options].forEach((o) => { if (o.value === 'Baja' || o.text === 'Baja') o.disabled = si && !enBaja; });
      est.title = si ? 'Las bajas se registran en Historia laboral' : '';
    }
    let aviso = document.getElementById('hl-aviso-ficha');
    const ancla = document.getElementById('d-empresa');
    if (si && ancla && !aviso) {
      aviso = document.createElement('p'); aviso.id = 'hl-aviso-ficha'; aviso.className = 'hl-bloqueado';
      aviso.innerHTML = 'Empresa, registro patronal, número interno y bajas se registran en <a href="#" onclick="cambiarSeccionDetalle(\'historia\');return false;">Historia laboral</a>.';
      ancla.closest('.grid3, .grid2, div').parentNode.appendChild(aviso);
    }
    if (aviso) aviso.style.display = si ? 'block' : 'none';
  }

  function pintar() {
    const raiz = document.getElementById('hl-raiz');
    const rels = [...estado.relaciones].sort((a, b) => (a.estado === 'vigente' ? 0 : 1) - (b.estado === 'vigente' ? 0 : 1)
      || String(b.fecha_ingreso || '').localeCompare(String(a.fecha_ingreso || '')));
    let h = `<div class="hl-wrap"><div class="hl-cab"><h3>Historia laboral</h3>
      ${puedeOperar() ? '<button type="button" class="primary" style="margin:0" id="hl-btn-ingreso">Registrar ingreso</button>' : ''}</div>
      <div class="hl-msg" id="hl-msg"></div>
      <div id="hl-form-ingreso"></div>`;
    if (estado.pendientes.length && puedeOperar()) {
      const vig = rels.filter((r) => r.estado === 'vigente');
      h += `<div class="hl-pend"><b>Esquemas de pago sin relación laboral</b>
        <p class="hint" style="margin:4px 0 8px">La base no los asignó porque hay más de una relación posible. Elige a cuál pertenece cada uno.</p>`;
      estado.pendientes.forEach((e) => {
        const comp = vig.filter((r) => !e.empresa_id || r.empresa_id === e.empresa_id);
        h += `<div class="hl-grid" style="margin:6px 0"><div><label>Esquema</label><div>${dinero(e.sueldo)} ${esc(e.modalidad_sueldo || '')} · ${esc(e.empresa_id ? nombreEmpresa(e.empresa_id) : 'sin empresa')}</div></div>
          <div><label>Relación</label><select id="hl-pend-${e.id}"><option value="">Elige…</option>${comp.map((r) =>
            `<option value="${r.id}">${esc(nombreEmpresa(r.empresa_id))} · ${esc(textoRP(r.registro_patronal_id) || 'Sin registro patronal')}</option>`).join('')}</select></div>
          <div><button type="button" class="hl-btn2" data-asignar="${e.id}">Asignar</button></div></div>`;
      });
      h += '</div>';
    }
    if (!rels.length) {
      h += `<p class="hint">Esta persona todavía no tiene relaciones laborales registradas.${puedeOperar() ? ' Usa «Registrar ingreso».' : ''}</p>`;
    }
    rels.forEach((r) => { h += tarjeta(r); });
    h += '</div>';
    raiz.innerHTML = h;
    enlazarEventos();
    if (msgPendiente) { mensaje(msgPendiente, true); msgPendiente = null; }
  }

  function ultimoAnulable(relId) {
    const evs = estado.eventos.filter((e) => e.relacion_id === relId && e.estado === 'vigente' && TIPOS_IMSS.includes(e.tipo))
      .sort((a, b) => String(b.registrado_en).localeCompare(String(a.registrado_en)));
    const u = evs[0];
    if (!u || u.origen === 'migracion') return null;
    if (u.idse_estado && !['pendiente', 'rechazado', 'cancelado'].includes(u.idse_estado)) return null;
    return u.evento_id;
  }

  function tarjeta(r) {
    const evs = estado.eventos.filter((e) => e.relacion_id === r.id);
    const rpTxt = textoRP(r.registro_patronal_id);
    const anulable = puedeOperar() ? ultimoAnulable(r.id) : null;
    let h = `<div class="hl-card ${r.estado}" data-relacion="${r.id}"><h4>${esc(nombreEmpresa(r.empresa_id))} · ${esc(rpTxt ? 'RP ' + rpTxt : 'Sin registro patronal (sin IDSE)')}
      <span class="hl-chip ${r.estado}">${r.estado === 'vigente' ? 'Vigente' : 'Baja'}</span>
      ${(r.pendientes_migracion || []).map((p) => `<span class="hl-chip aviso">${esc(PENDIENTE[p] || p)}</span>`).join('')}</h4>
      <div class="hl-datos"><span>Ingreso <b>${fechaMx(r.fecha_ingreso)}</b></span>
        <span>Antigüedad reconocida <b>${fechaMx(r.fecha_reconocimiento_antiguedad)}</b></span>
        ${r.estado === 'baja' ? `<span>Baja <b>${fechaMx(r.fecha_baja)}</b>${r.causa_baja ? ' · ' + esc(valorLegible('causa_baja', r.causa_baja)) : ''}</span>` : ''}
        ${rpTxt ? `<span>SBC <b>${dinero(r.sbc)}</b></span><span>Tipo <b>${esc(valorLegible('tipo_trabajador', r.tipo_trabajador))}</b></span>
        <span>Salario <b>${esc(valorLegible('tipo_salario', r.tipo_salario))}</b></span><span>Jornada <b>${esc(valorLegible('jornada', r.jornada))}</b></span>
        <span>UMF <b>${esc(r.umf || '—')}</b></span>` : ''}<span>Número interno <b>${esc(r.numero_interno || '—')}</b></span></div>`;
    if (puedeOperar()) {
      h += '<div class="hl-acc">';
      if (r.estado === 'vigente') {
        if (rpTxt) h += `<button type="button" class="hl-btn2" data-accion="salario" data-rel="${r.id}">Modificar salario</button>`;
        h += `<button type="button" class="hl-btn2" data-accion="baja" data-rel="${r.id}">Dar de baja</button>`;
      }
      h += `<button type="button" class="hl-btn2" data-accion="corregir" data-rel="${r.id}">Corregir datos</button></div>
        <div id="hl-form-${r.id}"></div>`;
    }
    h += '<ul class="hl-linea">';
    evs.forEach((e) => {
      const cambios = Object.keys({ ...(e.valores_anteriores || {}), ...(e.valores_nuevos || {}) })
        .filter((k) => !OCULTAR.includes(k))
        .map((k) => {
          const a = (e.valores_anteriores || {})[k], n = (e.valores_nuevos || {})[k];
          const et = esc(ETIQUETAS[k] || k);
          return a === undefined ? `<span>${et}: ${esc(valorLegible(k, n))}</span>` : `<span>${et}: ${esc(valorLegible(k, a))} → ${esc(valorLegible(k, n))}</span>`;
        }).join('');
      h += `<li class="${TIPOS_IMSS.includes(e.tipo) ? 'imss' : ''} ${e.estado}">
        <div class="hl-tit">${fechaMx(e.fecha_efectiva)} · ${esc(TIPOS[e.tipo] || e.tipo)}
          ${e.idse_estado ? `<span class="hl-chip idse ${e.idse_estado}">${esc(IDSE_ESTADO[e.idse_estado] || e.idse_estado)}</span>` : ''}
          ${e.estado === 'anulado' ? '<span class="hl-chip">Anulado</span>' : ''}</div>
        ${cambios ? `<div class="hl-cambios">${cambios}</div>` : ''}
        ${e.causa_descripcion ? `<div class="hl-meta">Causa: ${esc(e.causa_descripcion)}</div>` : ''}
        ${e.motivo ? `<div class="hl-meta">${esc(e.motivo)}</div>` : ''}
        <div class="hl-meta">Registrado ${fechaMx(e.registrado_en)} por ${esc(e.registrado_por || '—')}</div>
        ${anulable === e.evento_id ? `<button type="button" class="hl-btn2 peligro" style="margin-top:6px" data-anular="${e.evento_id}">Anular</button><div id="hl-anular-${e.evento_id}"></div>` : ''}
      </li>`;
    });
    h += '</ul></div>';
    return h;
  }

  function mensaje(texto, ok) {
    const m = document.getElementById('hl-msg'); if (!m) return;
    m.textContent = texto; m.className = 'hl-msg ' + (ok ? 'ok' : 'err');
  }

  async function ejecutar(fn, args, okTexto) {
    const { error } = await sb.rpc(fn, args);
    if (error) { mensaje(msgError(error), false); return false; }
    const id = estado.personaId;
    msgPendiente = okTexto;
    if (typeof cargarPersonal === 'function') await cargarPersonal();
    // Se vuelve a abrir la ficha para que sus campos reflejen lo que dejó la base.
    if (typeof abrirDetalle === 'function') await abrirDetalle(id, 'historia');
    return true;
  }

  function enlazarEventos() {
    const raiz = document.getElementById('hl-raiz');
    const bi = document.getElementById('hl-btn-ingreso');
    if (bi) bi.onclick = () => formIngreso();
    raiz.querySelectorAll('[data-accion]').forEach((b) => {
      b.onclick = () => ({ salario: formSalario, baja: formBaja, corregir: formCorregir })[b.dataset.accion](b.dataset.rel);
    });
    raiz.querySelectorAll('[data-anular]').forEach((b) => { b.onclick = () => formAnular(b.dataset.anular); });
    raiz.querySelectorAll('[data-asignar]').forEach((b) => {
      b.onclick = async () => {
        const sel = document.getElementById('hl-pend-' + b.dataset.asignar);
        if (!sel.value) { mensaje('Elige la relación del esquema.', false); return; }
        const { error } = await sb.from('personal_registros_pago').update({ relacion_laboral_id: sel.value }).eq('id', b.dataset.asignar);
        if (error) { mensaje(msgError(error), false); return; }
        await alAbrirDetalle(detalleActual); mensaje('Esquema asignado a su relación laboral.', true);
      };
    });
  }

  function cerrarForms() { document.querySelectorAll('#hl-raiz [id^="hl-form-"], #hl-raiz [id^="hl-anular-"]').forEach((d) => { d.innerHTML = ''; }); }
  const botones = (okTxt) => `<div class="hl-acc"><button type="submit" class="primary" style="margin:0">${okTxt}</button><button type="button" class="hl-btn2" data-cancelar>Cancelar</button></div>`;
  function montar(contId, html, alEnviar) {
    cerrarForms();
    const c = document.getElementById(contId); if (!c) return;
    c.innerHTML = `<form class="hl-form" novalidate>${html}</form>`;
    const f = c.querySelector('form');
    f.querySelector('[data-cancelar]').onclick = () => { c.innerHTML = ''; };
    f.onsubmit = async (ev) => {
      ev.preventDefault();
      const b = f.querySelector('button[type=submit]'); b.disabled = true;
      try { await alEnviar(f); } finally { if (document.body.contains(b)) b.disabled = false; }
    };
    const primero = f.querySelector('input,select'); if (primero) primero.focus();
  }
  const val = (f, n) => { const el = f.querySelector(`[name="${n}"]`); return el ? (el.value || '').trim() : ''; };
  const num = (f, n) => { const v = val(f, n).replace(/,/g, ''); return v === '' ? null : Number(v); };

  function formIngreso() {
    const p = detalleActual || {};
    const emps = (typeof empresas !== 'undefined' ? empresas : []).filter((e) => e.activo !== false);
    montar('hl-form-ingreso', `<b>Registrar ingreso o reingreso</b>
      <p class="hint" style="margin:4px 0 8px">La fecha de ingreso es la que va al IMSS. La antigüedad reconocida es aparte y no la modifica.</p>
      <div class="hl-grid">
        <div><label>Empresa</label><select name="empresa" required><option value="">Elige…</option>${emps.map((e) => `<option value="${e.id}" ${e.id === p.empresa_id ? 'selected' : ''}>${esc(e.nombre)}</option>`).join('')}</select></div>
        <div><label>Registro patronal</label><select name="rp"></select></div>
        <div><label>Fecha de ingreso</label><input name="fecha" type="date" required></div>
        <div><label>Antigüedad reconocida (opcional)</label><input name="antig" type="date"></div>
        <div><label>SBC diario</label><input name="sbc" inputmode="decimal" placeholder="Ej. 450.00"></div>
        <div><label>SDI (si es distinto)</label><input name="sdi" inputmode="decimal"></div>
        <div><label>Tipo de trabajador</label><select name="tt">${opciones(TIPO_TRAB, '1')}</select></div>
        <div><label>Tipo de salario</label><select name="ts">${opciones(TIPO_SAL, '0')}</select></div>
        <div><label>Jornada</label><select name="jo">${opciones(JORNADA, '0')}</select></div>
        <div><label>UMF</label><input name="umf" maxlength="3" inputmode="numeric" placeholder="3 dígitos"></div>
        <div><label>Número interno (clave IDSE)</label><input name="num" maxlength="10" value="${esc(p.numero_interno_trabajador || '')}"></div>
        <div><label>Motivo / nota (opcional)</label><input name="motivo"></div>
      </div>${botones('Registrar ingreso')}`, async (f) => {
      if (!val(f, 'empresa') || !val(f, 'fecha')) { mensaje('Indica empresa y fecha de ingreso.', false); return; }
      await ejecutar('laboral_registrar_ingreso', {
        p_personal_id: estado.personaId, p_empresa_id: val(f, 'empresa'), p_registro_patronal_id: val(f, 'rp') || null,
        p_fecha_ingreso: val(f, 'fecha'), p_fecha_reconocimiento_antiguedad: val(f, 'antig') || null,
        p_sbc: num(f, 'sbc'), p_sdi: num(f, 'sdi'), p_tipo_trabajador: val(f, 'tt') || null, p_tipo_salario: val(f, 'ts') || null,
        p_jornada: val(f, 'jo') || null, p_umf: val(f, 'umf') || null, p_numero_interno: val(f, 'num') || null, p_motivo: val(f, 'motivo') || null,
      }, 'Ingreso registrado.');
    });
    const f = document.querySelector('#hl-form-ingreso form');
    const selE = f.querySelector('[name=empresa]'), selR = f.querySelector('[name=rp]');
    const llenarRP = () => {
      const lista = rps.filter((r) => r.empresa_id === selE.value && r.activo !== false);
      selR.innerHTML = '<option value="">Sin registro patronal (sin IDSE)</option>' + lista.map((r) => `<option value="${r.id}" ${r.id === (detalleActual || {}).registro_patronal_id ? 'selected' : ''}>${esc(r.registro_patronal)}</option>`).join('');
      if (lista.length && !selR.value) selR.value = lista[0].id;
    };
    selE.onchange = llenarRP; llenarRP();
  }

  function formBaja(relId) {
    montar('hl-form-' + relId, `<b>Dar de baja esta relación</b>
      <p class="hint" style="margin:4px 0 8px">Se desactivan sus esquemas de pago. Si tiene registro patronal, queda el movimiento de baja en la bandeja IDSE.</p>
      <div class="hl-grid"><div><label>Fecha de baja</label><input name="fecha" type="date" required></div>
        <div><label>Causa (IMSS)</label><select name="causa" required><option value="">Elige…</option>${causas.map((c) => `<option value="${esc(c.codigo)}">${esc(c.codigo)} · ${esc(c.descripcion)}</option>`).join('')}</select></div>
        <div><label>Comentario (opcional)</label><input name="motivo"></div></div>${botones('Registrar baja')}`, async (f) => {
      await ejecutar('laboral_registrar_baja', { p_relacion_id: relId, p_fecha_baja: val(f, 'fecha') || null, p_causa: val(f, 'causa') || null, p_motivo: val(f, 'motivo') || null }, 'Baja registrada.');
    });
  }

  function formSalario(relId) {
    const r = estado.relaciones.find((x) => x.id === relId) || {};
    montar('hl-form-' + relId, `<b>Modificación de salario</b>
      <p class="hint" style="margin:4px 0 8px">SBC actual: ${dinero(r.sbc)}. La fecha debe ser posterior a la última modificación.</p>
      <div id="hl-faltan-07-${relId}"></div>
      <div class="hl-grid"><div><label>Fecha efectiva del cambio (no la fecha de captura)</label><input name="fecha" type="date" required value="${hoyMexico()}"></div>
        <div><label>Nuevo SBC diario</label><input name="sbc" inputmode="decimal" required></div>
        <div><label>SDI (si es distinto)</label><input name="sdi" inputmode="decimal"></div>
        <div><label>Tipo de salario</label><select name="ts">${opciones(TIPO_SAL, r.tipo_salario)}</select></div>
        <div><label>Motivo (opcional)</label><input name="motivo"></div></div>${botones('Registrar modificación')}`, async (f) => {
      await ejecutar('laboral_modificar_salario', { p_relacion_id: relId, p_fecha_efectiva: val(f, 'fecha') || null, p_sbc: num(f, 'sbc'),
        p_sdi: num(f, 'sdi'), p_tipo_salario: val(f, 'ts') || null, p_motivo: val(f, 'motivo') || null }, 'Modificación de salario registrada.');
    });
    const form = document.querySelector('#hl-form-' + relId + ' form');
    const pintarFaltantes = () => {
      const caja = document.getElementById('hl-faltan-07-' + relId);
      if (!caja) return;
      const faltan = faltantesIdse07(r, form ? val(form, 'ts') : null);
      caja.innerHTML = faltan.length
        ? `<div class="hl-msg err" style="margin:0 0 8px">Puedes registrar la modificación, pero para generar su archivo IDSE falta: ${faltan.map(esc).join(', ')}. `
          + 'Los datos de la relación se completan con «Corregir datos»; los de la persona, en su ficha.</div>'
        : '';
    };
    if (form) { const ts = form.querySelector('[name=ts]'); if (ts) ts.addEventListener('change', pintarFaltantes); }
    pintarFaltantes();
  }

  // Fecha de hoy en la hora de México (no UTC: después de las 18:00 UTC ya sería «mañana»).
  function hoyMexico() {
    try { return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Mexico_City', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date()); }
    catch (e) { const d = new Date(); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); }
  }

  // Lo mismo que exige idse_validar para un 07. Es solo un aviso anticipado:
  // la base vuelve a validar al generar el archivo.
  function faltantesIdse07(r, tipoSalarioElegido) {
    const p = estado.persona || {};
    const rp = rps.find((x) => x.id === r.registro_patronal_id) || {};
    const curpOk = typeof CURP_REGEX !== 'undefined' ? CURP_REGEX.test(String(p.curp || '')) : String(p.curp || '').length === 18;
    const f = [];
    if (!rp.guia_idse) f.push('número de guía IDSE del registro patronal');
    if (!/^[0-9]{11}$/.test(String(p.nss || ''))) f.push('NSS de 11 dígitos');
    if (!String(p.primer_apellido || '').trim()) f.push('primer apellido');
    if (!String(p.nombres || '').trim()) f.push('nombre(s) separado del apellido');
    if (!curpOk) f.push('CURP válida');
    if (!r.numero_interno) f.push('número interno (clave del trabajador)');
    if (!r.tipo_trabajador) f.push('tipo de trabajador');
    if (!(tipoSalarioElegido || r.tipo_salario)) f.push('tipo de salario');
    if (!r.jornada) f.push('jornada');
    return f;
  }

  function formCorregir(relId) {
    const r = estado.relaciones.find((x) => x.id === relId) || {};
    const migrado = estado.eventos.some((e) => e.relacion_id === relId && ['ingreso', 'reingreso'].includes(e.tipo) && e.estado === 'vigente' && e.origen === 'migracion')
      && !estado.eventos.some((e) => e.relacion_id === relId && e.tipo === 'modificacion_salario' && e.estado === 'vigente');
    montar('hl-form-' + relId, `<b>Corregir datos</b>
      <p class="hint" style="margin:4px 0 8px">Solo se guardan los campos que cambies. ${migrado ? 'Por ser un dato migrado también puedes corregir la fecha de ingreso y el SBC.' : 'La fecha de ingreso y el SBC de un movimiento real no se corrigen aquí: usa anular o modificación de salario.'}</p>
      <div class="hl-grid">
        ${migrado ? `<div><label>Fecha de ingreso</label><input name="fecha_ingreso" type="date" value="${r.fecha_ingreso || ''}"></div>
        <div><label>SBC diario</label><input name="sbc" inputmode="decimal" value="${r.sbc == null ? '' : r.sbc}"></div>` : ''}
        <div><label>Antigüedad reconocida</label><input name="fecha_reconocimiento_antiguedad" type="date" value="${r.fecha_reconocimiento_antiguedad || ''}"></div>
        <div><label>Número interno</label><input name="numero_interno" maxlength="10" value="${esc(r.numero_interno || '')}"></div>
        <div><label>Tipo de trabajador</label><select name="tipo_trabajador">${opciones(TIPO_TRAB, r.tipo_trabajador)}</select></div>
        <div><label>Tipo de salario</label><select name="tipo_salario">${opciones(TIPO_SAL, r.tipo_salario)}</select></div>
        <div><label>Jornada</label><select name="jornada">${opciones(JORNADA, r.jornada)}</select></div>
        <div><label>UMF</label><input name="umf" maxlength="3" inputmode="numeric" value="${esc(r.umf || '')}"></div>
        <div><label>Motivo de la corrección</label><input name="motivo" required></div>
      </div>${botones('Guardar corrección')}`, async (f) => {
      const cambios = {};
      ['fecha_ingreso', 'sbc', 'fecha_reconocimiento_antiguedad', 'numero_interno', 'tipo_trabajador', 'tipo_salario', 'jornada', 'umf'].forEach((k) => {
        const el = f.querySelector(`[name="${k}"]`); if (!el) return;
        let v = el.value.trim(); const actual = r[k] == null ? '' : String(r[k]);
        if (k === 'sbc') { if (v === '' || Number(v) === Number(actual)) return; cambios[k] = Number(v.replace(/,/g, '')); return; }
        if (v !== actual) cambios[k] = v === '' ? null : v;
      });
      if (!Object.keys(cambios).length) { mensaje('No cambiaste ningún dato.', false); return; }
      await ejecutar('laboral_corregir_datos', { p_relacion_id: relId, p_cambios: cambios, p_motivo: val(f, 'motivo') }, 'Corrección registrada.');
    });
  }

  function formAnular(evId) {
    montar('hl-anular-' + evId, `<div class="hl-grid"><div><label>Motivo de la anulación</label><input name="motivo" required></div></div>
      <p class="hint" style="margin:6px 0">El evento queda en el historial marcado como anulado y se deshace su efecto.</p>${botones('Anular movimiento')}`, async (f) => {
      await ejecutar('laboral_anular_evento', { p_evento_id: evId, p_motivo: val(f, 'motivo') }, 'Movimiento anulado.');
    });
  }

  // =====================================================================
  // Alta de personal: fecha de ingreso → laboral_registrar_ingreso
  // =====================================================================
  function prepararAlta() {
    const rp = document.getElementById('f-registro-patronal');
    if (!rp || document.getElementById('f-fecha-ingreso-laboral')) return;
    const caja = document.createElement('div');
    caja.innerHTML = '<label>Fecha de ingreso (alta IMSS)</label><input id="f-fecha-ingreso-laboral" type="date"><p class="hint" style="margin:4px 0 0">Con empresa y esta fecha se registra el ingreso en su Historia laboral.</p>';
    const fila = rp.closest('div').parentNode;
    fila.appendChild(caja);
  }
  async function trasAlta(nueva, enviado) {
    const f = document.getElementById('f-fecha-ingreso-laboral');
    const fecha = f ? f.value : '';
    if (!enviado || !enviado.empresa_id) return 'Sin empresa: el ingreso se registra después en su Historia laboral.';
    if (!fecha) return 'Sin fecha de ingreso: regístrala en su Historia laboral para que aparezca en la bandeja IDSE.';
    const { error } = await sb.rpc('laboral_registrar_ingreso', {
      p_personal_id: nueva.id, p_empresa_id: enviado.empresa_id, p_registro_patronal_id: enviado.registro_patronal_id || null,
      p_fecha_ingreso: fecha, p_numero_interno: enviado.numero_interno_trabajador || null,
    });
    if (error) return 'La persona se guardó, pero su ingreso no: ' + msgError(error) + ' Regístralo en su Historia laboral.';
    return 'Ingreso registrado en su Historia laboral.' + (enviado.registro_patronal_id ? ' Completa SBC, UMF y tipos en la ficha antes de generar el IDSE.' : '');
  }

  // =====================================================================
  // Bandeja IDSE
  // =====================================================================
  let idse = { rp: null, filas: [], archivos: [] };
  async function abrirIdse() {
    const raiz = document.getElementById('idse-raiz');
    if (!raiz) return;
    if (!puedeOperar()) { raiz.innerHTML = '<div class="card"><p>La bandeja IDSE es para Nómina y Administrador.</p></div>'; return; }
    await cargarCatalogos();
    const activos = rps.filter((r) => r.activo !== false);
    if (!idse.rp || !activos.some((r) => r.id === idse.rp)) idse.rp = activos.length ? activos[0].id : null;
    raiz.innerHTML = `<div class="card"><div class="hl-cab"><h3>Movimientos IDSE</h3></div>
      <p class="hint" style="margin:0 0 10px">Un archivo por registro patronal. BeeHuman genera el archivo; tú lo subes al IDSE y registras aquí el lote y el resultado.</p>
      <div class="hl-grid" style="max-width:820px"><div><label>Registro patronal</label><select id="idse-rp">${activos.map((r) =>
        `<option value="${r.id}" ${r.id === idse.rp ? 'selected' : ''}>${esc(r.registro_patronal)} · ${esc(nombreEmpresa(r.empresa_id))}</option>`).join('')}</select></div>
        <div><label>Guía IDSE</label><input id="idse-guia" maxlength="5" inputmode="numeric" ${esAdmin() ? '' : 'disabled'}></div>
        <div><label>Zona de salario mínimo</label><select id="idse-zona" ${esAdmin() ? '' : 'disabled'}><option value="general">General</option><option value="zlfn">Zona libre de la frontera norte</option></select></div>
        ${esAdmin() ? '<div><button type="button" class="hl-btn2" id="idse-guardar-rp">Guardar datos del RP</button></div>' : ''}</div>
      <div class="hl-msg" id="idse-msg"></div>
      <h4 style="margin:18px 0 6px">Altas y reingresos pendientes</h4><div id="idse-pend-08"></div>
      <h4 style="margin:18px 0 6px">Bajas pendientes</h4><div id="idse-pend-02"></div>
      <h4 style="margin:18px 0 6px">Modificaciones de salario pendientes</h4><div id="idse-pend-07"></div>
      <h4 style="margin:18px 0 6px">Archivos generados</h4><div id="idse-arch"></div></div>`;
    document.getElementById('idse-rp').onchange = (e) => { idse.rp = e.target.value; abrirIdse(); };
    const g = document.getElementById('idse-guardar-rp');
    if (g) g.onclick = guardarRP;
    pintarRP();
    if (idse.rp) await refrescarIdse();
  }
  function idseMsg(t, ok) { const m = document.getElementById('idse-msg'); if (m) { m.textContent = t; m.className = 'hl-msg ' + (ok ? 'ok' : 'err'); } }
  function pintarRP() {
    const r = rps.find((x) => x.id === idse.rp) || {};
    const gi = document.getElementById('idse-guia'), zo = document.getElementById('idse-zona');
    if (gi) gi.value = r.guia_idse || ''; if (zo) zo.value = r.zona_salario_minimo || 'general';
  }
  async function guardarRP() {
    const guia = document.getElementById('idse-guia').value.trim();
    if (guia && !/^\d{5}$/.test(guia)) { idseMsg('La guía IDSE tiene 5 dígitos.', false); return; }
    const { error } = await sb.from('empresas_registros_patronales').update({ guia_idse: guia || null, zona_salario_minimo: document.getElementById('idse-zona').value }).eq('id', idse.rp);
    if (error) { idseMsg(msgError(error), false); return; }
    await cargarCatalogos(); await refrescarIdse(); idseMsg('Datos del registro patronal guardados.', true);
  }

  const TITULO_TIPO = { '08': 'altas', '02': 'bajas', '07': 'modificaciones' };
  function pintarPendientes(tipo, v, movs) {
    const pend = document.getElementById('idse-pend-' + tipo);
    if (!pend) return;
    if (v.error) {
      // si la base todavía no habilita este tipo, se explica sin marcarlo como error
      const msg = msgError(v.error);
      pend.innerHTML = /se habilita cuando/.test(msg) ? `<p class="hint">${esc(msg)}</p>` : `<div class="hl-msg err">${esc(msg)}</div>`;
      return;
    }
    const filas = v.data || [];
    if (!filas.length) { pend.innerHTML = `<p class="hint">No hay ${TITULO_TIPO[tipo]} pendientes en este registro patronal.</p>`; return; }
    const sbcDe = (id) => { const m = movs.find((x) => x.id === id); return m && m.sbc != null ? Number(m.sbc).toLocaleString('es-MX', { style: 'currency', currency: 'MXN' }) : '—'; };
    const causaDe = (id) => { const m = movs.find((x) => x.id === id); if (!m || !m.causa_baja) return '—'; const c = causas.find((x) => x.codigo === m.causa_baja); return m.causa_baja + (c ? ' · ' + c.descripcion : ''); };
    let h = `<div style="overflow-x:auto"><table class="idse-tabla"><thead><tr><th><input type="checkbox" class="idse-todos" data-tipo="${tipo}" aria-label="Seleccionar todos"></th><th>Persona</th><th>${tipo === '02' ? 'Fecha de baja' : 'Fecha'}</th>${tipo === '02' ? '<th>Causa</th>' : ''}${tipo === '07' ? '<th>SBC nuevo</th>' : ''}<th>Revisión</th></tr></thead><tbody>`;
    filas.forEach((f) => {
      const okF = !(f.errores || []).length;
      h += `<tr><td><input type="checkbox" class="idse-sel" data-tipo="${tipo}" value="${f.movimiento_id}" ${okF ? '' : 'disabled'}></td><td>${esc(f.nombre)}</td><td>${fechaMx(f.fecha_movimiento)}</td>${tipo === '02' ? `<td>${esc(causaDe(f.movimiento_id))}</td>` : ''}${tipo === '07' ? `<td>${esc(sbcDe(f.movimiento_id))}</td>` : ''}
        <td>${(f.errores || []).map((x) => `<div class="idse-err">Falta: ${esc(x)}</div>`).join('')}${(f.avisos || []).map((x) => `<div class="idse-aviso">${esc(x)}</div>`).join('')}${okF && !(f.avisos || []).length ? '<span class="hl-chip vigente">Lista</span>' : ''}</td></tr>`;
    });
    h += `</tbody></table></div><div class="hl-acc"><button type="button" class="primary" style="margin:0" data-generar="${tipo}">Generar archivo de ${TITULO_TIPO[tipo]} con los seleccionados</button></div>`;
    pend.innerHTML = h;
    const t = pend.querySelector('.idse-todos');
    if (t) t.onchange = () => pend.querySelectorAll('.idse-sel:not(:disabled)').forEach((c) => { c.checked = t.checked; });
    pend.querySelector('[data-generar]').onclick = () => generar(tipo);
  }

  async function refrescarIdse() {
    const arch = document.getElementById('idse-arch');
    const [v08, v02, v07, a, otros] = await Promise.all([
      sb.rpc('idse_validar', { p_registro_patronal_id: idse.rp, p_tipo: '08' }),
      sb.rpc('idse_validar', { p_registro_patronal_id: idse.rp, p_tipo: '02' }),
      sb.rpc('idse_validar', { p_registro_patronal_id: idse.rp, p_tipo: '07' }),
      sb.from('idse_archivos').select('id,nombre_archivo,num_registros,estado,lote_idse,fecha_presentacion,acuse_folio,generado_en,hash_sha256,tipo_movimiento')
        .eq('registro_patronal_id', idse.rp).order('generado_en', { ascending: false }),
      sb.from('idse_movimientos').select('id,tipo_movimiento,causa_baja,sbc').eq('registro_patronal_id', idse.rp).in('tipo_movimiento', ['02', '07']).in('estado', ['pendiente', 'rechazado']),
    ]);
    const movs = otros.data || [];
    idse.filas = [...(v08.data || []), ...(v02.data || []), ...(v07.data || [])];
    pintarPendientes('08', v08, movs);
    pintarPendientes('02', v02, movs);
    pintarPendientes('07', v07, movs);
    idse.archivos = a.error ? [] : (a.data || []);
    const ESTA = { generado: 'Generado', presentado: 'Presentado', con_resultado: 'Con resultado', cancelado: 'Cancelado' };
    arch.innerHTML = !idse.archivos.length ? '<p class="hint">Todavía no hay archivos.</p>' :
      `<div style="overflow-x:auto"><table class="idse-tabla"><thead><tr><th>Archivo</th><th>Movimientos</th><th>Estado</th><th>Lote / acuse</th><th></th></tr></thead><tbody>${idse.archivos.map((x) => `
        <tr><td>${esc(x.nombre_archivo)}<div class="hl-meta">${fechaMx(x.generado_en)} · huella ${esc(x.hash_sha256.slice(0, 12))}…</div></td><td>${x.num_registros}</td><td>${esc(ESTA[x.estado] || x.estado)}</td>
        <td>${esc(x.lote_idse || '—')}${x.fecha_presentacion ? ' · ' + fechaMx(x.fecha_presentacion) : ''}${x.acuse_folio ? '<div class="hl-meta">Acuse ' + esc(x.acuse_folio) + '</div>' : ''}</td>
        <td><div class="hl-acc" style="margin:0"><button type="button" class="hl-btn2" data-desc="${x.id}">Descargar</button>
          ${x.estado === 'generado' ? `<button type="button" class="hl-btn2" data-pres="${x.id}">Marcar presentado</button><button type="button" class="hl-btn2 peligro" data-canc="${x.id}">Cancelar</button>` : ''}
          ${x.estado === 'presentado' ? `<button type="button" class="hl-btn2" data-res="${x.id}">Registrar resultado</button>` : ''}</div>
          <div id="idse-f-${x.id}"></div></td></tr>`).join('')}</tbody></table></div>`;
    arch.querySelectorAll('[data-desc]').forEach((b) => { b.onclick = () => descargar(b.dataset.desc); });
    arch.querySelectorAll('[data-pres]').forEach((b) => { b.onclick = () => formPresentado(b.dataset.pres); });
    arch.querySelectorAll('[data-canc]').forEach((b) => { b.onclick = () => formCancelar(b.dataset.canc); });
    arch.querySelectorAll('[data-res]').forEach((b) => { b.onclick = () => formResultado(b.dataset.res); });
  }

  async function generar(tipo) {
    const ids = [...document.querySelectorAll(`.idse-sel[data-tipo="${tipo}"]:checked`)].map((c) => c.value);
    if (!ids.length) { idseMsg('Selecciona al menos un movimiento.', false); return; }
    const { data, error } = await sb.rpc('idse_generar_archivo', { p_registro_patronal_id: idse.rp, p_tipo: tipo, p_movimientos: ids });
    if (error) { idseMsg(msgError(error), false); return; }
    await refrescarIdse(); await descargar(data);
    idseMsg('Archivo generado y descargado. Cuando lo subas al IDSE, registra aquí el número de lote.', true);
  }
  async function descargar(id) {
    const { data, error } = await sb.from('idse_archivos').select('nombre_archivo,contenido').eq('id', id).single();
    if (error) { idseMsg(msgError(error), false); return; }
    const blob = new Blob([data.contenido], { type: 'text/plain' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = data.nombre_archivo;
    document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  }
  function formIdse(id, html, alEnviar) {
    document.querySelectorAll('#idse-arch [id^="idse-f-"]').forEach((d) => { d.innerHTML = ''; });
    const c = document.getElementById('idse-f-' + id);
    c.innerHTML = `<form class="hl-form">${html}<div class="hl-acc"><button type="submit" class="primary" style="margin:0">Guardar</button><button type="button" class="hl-btn2" data-cancelar>Cancelar</button></div></form>`;
    const f = c.querySelector('form');
    f.querySelector('[data-cancelar]').onclick = () => { c.innerHTML = ''; };
    f.onsubmit = async (ev) => { ev.preventDefault(); await alEnviar(f); };
  }
  async function rpcIdse(fn, args, ok) {
    const { error } = await sb.rpc(fn, args);
    if (error) { idseMsg(msgError(error), false); return; }
    await refrescarIdse(); idseMsg(ok, true);
  }
  function formPresentado(id) {
    formIdse(id, `<div class="hl-grid"><div><label>Número de lote IDSE</label><input name="lote" required></div><div><label>Fecha de presentación</label><input name="fecha" type="date" required></div></div>`,
      (f) => rpcIdse('idse_marcar_presentado', { p_archivo_id: id, p_lote: val(f, 'lote'), p_fecha: val(f, 'fecha') || null }, 'Archivo marcado como presentado.'));
  }
  function formCancelar(id) {
    formIdse(id, `<div class="hl-grid"><div><label>Motivo de la cancelación</label><input name="motivo" required></div></div><p class="hint">Sus movimientos vuelven a pendientes.</p>`,
      (f) => rpcIdse('idse_cancelar_archivo', { p_archivo_id: id, p_motivo: val(f, 'motivo') }, 'Archivo cancelado.'));
  }
  async function formResultado(id) {
    const { data, error } = await sb.from('idse_archivo_renglones').select('movimiento_id,linea,texto').eq('archivo_id', id).order('linea');
    if (error) { idseMsg(msgError(error), false); return; }
    const filas = (data || []).map((r) => `<div class="hl-grid" style="margin:4px 0"><div><label><input type="checkbox" name="rech" value="${r.movimiento_id}"> Rechazado · línea ${r.linea}</label>
      <div class="hl-meta">${esc(r.texto.slice(22, 103).replace(/\s+/g, ' ').trim())}</div></div><div><label>Motivo del rechazo</label><input name="mot-${r.movimiento_id}"></div></div>`).join('');
    formIdse(id, `<p class="hint">Marca solo los rechazados; el resto queda confirmado.</p>${filas}
      <div class="hl-grid"><div><label>Folio del acuse (opcional)</label><input name="folio"></div><div><label>Fecha del acuse</label><input name="facuse" type="date"></div></div>`, (f) => {
      const rech = [...f.querySelectorAll('[name=rech]:checked')].map((c) => ({ movimiento_id: c.value, motivo: val(f, 'mot-' + c.value) }));
      return rpcIdse('idse_registrar_resultado', { p_archivo_id: id, p_rechazados: rech, p_acuse_folio: val(f, 'folio') || null, p_acuse_fecha: val(f, 'facuse') || null }, 'Resultado registrado.');
    });
  }

  // ---------- conexión con el archivo principal ----------
  // La ficha general no debe enviar los datos que administra Historia laboral
  // cuando esta persona ya tiene historial (la base los rechaza).
  function fichaBloqueada(personaId) { return !!personaId && fichaBloqueadaPara === personaId; }
  window.BH_laboral = { alAbrirDetalle, trasAlta, abrirIdse, fichaBloqueada };
  prepararAlta();
  const bIdse = document.querySelector('nav.tabs button[data-tab="idse"]');
  if (bIdse) bIdse.addEventListener('click', () => { abrirIdse(); });
})();
