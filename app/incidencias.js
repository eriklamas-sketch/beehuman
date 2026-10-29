// =====================================================================
// BeeHuman · Ola 1 · Incidencias (hoja semanal del coordinador)
// Etapas 2 y 3: configuración (Administrador), periodos (Nómina y
// Administrador) y hoja del coordinador. Las pantallas de revisión de
// Nómina, concentrado, comparativo y exportaciones son la siguiente etapa.
// Toda regla de negocio y de permisos vive en la base (tablas inc_*):
// esta pantalla solo la refleja. El coordinador nunca recibe importes
// calculados con sueldo: la base no se los entrega.
// Usa del archivo principal: sb, rolActual, rolPersonalId, empresas,
// periodicidades, escapeHtml.
// =====================================================================
(function () {
  'use strict';

  // ---------- estilos de la sección (línea visual V2.1) ----------
  const css = `
#panel-incidencias .inc-sub{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 14px}
#panel-incidencias .inc-sub button,#panel-incidencias .inc-seg button{background:var(--v21-superficie,#fff);border:1px solid var(--v21-borde,#E5E9F1);color:var(--v21-texto-2,#5B6680);border-radius:999px;padding:7px 14px;font:600 13px Inter,sans-serif;cursor:pointer;margin:0}
#panel-incidencias .inc-sub button.activo,#panel-incidencias .inc-seg button.activo{background:var(--v21-navy,#16264A);border-color:var(--v21-navy,#16264A);color:#fff}
#panel-incidencias .inc-seg{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0}
#panel-incidencias .inc-fila{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;align-items:end;margin:10px 0}
#panel-incidencias .inc-fila label{display:block;font-size:12px;color:var(--v21-texto-2,#5B6680);margin:0 0 4px;font-weight:600}
#panel-incidencias .inc-fila input,#panel-incidencias .inc-fila select{width:100%;box-sizing:border-box}
#panel-incidencias .inc-acciones{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:12px 0}
#panel-incidencias .inc-acciones button{margin:0}
#panel-incidencias button.inc-sec{background:var(--v21-superficie,#fff);color:var(--v21-navy,#16264A);border:1px solid var(--v21-borde,#E5E9F1);border-radius:9px;padding:8px 14px;font:600 13px Inter,sans-serif;cursor:pointer}
#panel-incidencias button.inc-peligro{background:#fff;color:#B42318;border:1px solid #F2C6C0;border-radius:9px;padding:8px 14px;font:600 13px Inter,sans-serif;cursor:pointer}
#panel-incidencias .inc-msg{margin:10px 0;padding:9px 12px;border-radius:9px;font-size:13px;display:none}
#panel-incidencias .inc-msg.ok{display:block;background:#E8F4E5;color:#1F6B33}
#panel-incidencias .inc-msg.err{display:block;background:#FDECEA;color:#B42318}
#panel-incidencias .inc-msg.info{display:block;background:#EAF0FC;color:#22489E}
#panel-incidencias .inc-tabla-wrap{overflow:auto;border:1px solid var(--v21-borde,#E5E9F1);border-radius:12px;max-height:70vh}
#panel-incidencias table.inc-tabla{border-collapse:separate;border-spacing:0;width:100%;font-size:13px}
#panel-incidencias .inc-tabla th{position:sticky;top:0;background:#F3F5FA;color:#45506A;font-weight:600;font-size:12px;padding:8px 6px;border-bottom:1px solid var(--v21-borde,#E5E9F1);text-align:center;white-space:nowrap;z-index:2}
#panel-incidencias .inc-tabla td{padding:5px 6px;border-bottom:1px solid #EDF0F6;text-align:center;vertical-align:middle;background:#fff}
#panel-incidencias .inc-tabla th.inc-col-persona,#panel-incidencias .inc-tabla td.inc-col-persona{position:sticky;left:0;text-align:left;z-index:3;min-width:190px;max-width:230px;box-shadow:1px 0 0 #E5E9F1}
#panel-incidencias .inc-tabla th.inc-col-persona{z-index:4}
#panel-incidencias .inc-tabla td.inc-col-persona b{display:block;font-size:13px;color:var(--v21-texto,#1C2840);white-space:normal}
#panel-incidencias .inc-tabla td.inc-col-persona small{color:var(--v21-texto-3,#8690A6);font-size:11px}
#panel-incidencias .inc-tabla td.inc-fuera{background:#F5F6F8;color:#A0A7B6;font-size:11px}
#panel-incidencias .inc-tabla select,#panel-incidencias .inc-tabla input{margin:0;padding:5px 4px;font-size:13px;border:1px solid var(--v21-borde,#E5E9F1);border-radius:7px;background:#fff;width:64px;box-sizing:border-box;text-align:center}
#panel-incidencias .inc-tabla select.inc-proy{width:130px;text-align:left}
#panel-incidencias .inc-tabla input.inc-texto{width:180px;text-align:left}
#panel-incidencias .inc-tabla td.inc-total{font-weight:600;color:var(--v21-navy,#16264A);background:#FAFBFD;white-space:nowrap}
#panel-incidencias .inc-tabla tr.inc-sum td{font-weight:700;background:#F3F5FA}
#panel-incidencias .inc-cod-F{background:#FDECEA!important;color:#B42318}
#panel-incidencias .inc-cod-I{background:#FFF4D6!important;color:#8A5A00}
#panel-incidencias .inc-cod-D,#panel-incidencias .inc-cod-V,#panel-incidencias .inc-cod-P{background:#EAF0FC!important;color:#22489E}
#panel-incidencias .inc-aviso{display:inline-block;background:#FFF4D6;color:#8A5A00;border-radius:999px;padding:2px 8px;font-size:11px;font-weight:600;white-space:nowrap}
#panel-incidencias .inc-leyenda{font-size:12px;color:var(--v21-texto-2,#5B6680);margin:8px 0;display:flex;gap:14px;flex-wrap:wrap}
#panel-incidencias .inc-estado{display:inline-block;border-radius:999px;padding:3px 10px;font-size:12px;font-weight:600}
#panel-incidencias .inc-estado.borrador{background:#F1F2F4;color:#4B5565}
#panel-incidencias .inc-estado.enviada{background:#E8F4E5;color:#1F6B33}
#panel-incidencias .inc-estado.devuelta{background:#FDECEA;color:#B42318}
#panel-incidencias .inc-estado.procesada{background:#EAF0FC;color:#22489E}
#panel-incidencias .inc-lista{width:100%;border-collapse:collapse;font-size:13px}
#panel-incidencias .inc-lista th{text-align:left;font-size:12px;color:#45506A;background:#F3F5FA;padding:8px 10px}
#panel-incidencias .inc-lista td{padding:9px 10px;border-top:1px solid #EDF0F6;vertical-align:middle}
#panel-incidencias .inc-cab{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:flex-start}
#panel-incidencias .inc-cab h2{margin:0}
#panel-incidencias .inc-nota{font-size:12px;color:var(--v21-texto-3,#8690A6)}
#panel-incidencias textarea{width:100%;box-sizing:border-box;min-height:60px}
@media (max-width:700px){
  #panel-incidencias .inc-tabla th.inc-col-persona,#panel-incidencias .inc-tabla td.inc-col-persona{min-width:128px;max-width:140px}
  #panel-incidencias .inc-tabla td.inc-col-persona b{font-size:12px}
  #panel-incidencias .inc-tabla-wrap{max-height:none}
}`;
  const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);

  // ---------- utilidades ----------
  const $ = id => document.getElementById(id);
  const esc = v => escapeHtml(v);
  const DIAS = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
  const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
  const CODIGOS = [['', '·'], ['F', 'F'], ['I', 'I'], ['D', 'D'], ['V', 'V'], ['P', 'P']];
  const NOMBRE_CODIGO = { F: 'Falta', I: 'Incapacidad', D: 'Descanso', V: 'Vacaciones', P: 'Permiso' };
  const ESTADOS = { borrador: 'Borrador', enviada: 'Enviada', devuelta: 'Devuelta', procesada: 'Procesada' };
  const fechaUTC = s => new Date(s + 'T12:00:00Z');
  const dia = s => { const d = fechaUTC(s); return `${DIAS[d.getUTCDay()]} ${d.getUTCDate()}`; };
  const fechaLarga = s => { const d = fechaUTC(s); return `${d.getUTCDate()} ${MESES[d.getUTCMonth()]} ${d.getUTCFullYear()}`; };
  const sumar = (s, n) => { const d = fechaUTC(s); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
  const rango = (a, b) => { const r = []; for (let f = a; f <= b; f = sumar(f, 1)) r.push(f); return r; };
  const semana = s => { const d = fechaUTC(s); const w = (d.getUTCDay() + 6) % 7; return sumar(s, -w); };
  const dinero = n => Number(n || 0).toLocaleString('es-MX', { style: 'currency', currency: 'MXN' });
  const num = v => { const n = Number(String(v).replace(',', '.')); return isFinite(n) ? n : 0; };
  const limpiarError = e => String((e && (e.message || e.details)) || e || 'Error desconocido').replace(/^BeeHuman:\s*/, '');
  const nombreEmpresa = id => { const e = (typeof empresas !== 'undefined' ? empresas : []).find(x => x.id === id); return e ? e.nombre : ''; };
  const conEmpresa = id => { const n = nombreEmpresa(id); return n ? n + ' · ' : ''; };
  function msg(id, tipo, texto) { const el = $(id); if (!el) return; el.className = 'inc-msg ' + tipo; el.textContent = texto; }

  const S = { vista: null, usuarioId: null, tenantId: null, cfg: { empresaId: null }, hoja: null, obsGral: {} };
  // La observación general se guarda en la base al enviar; mientras tanto se conserva como borrador local.
  const obsGralLeer = id => { if (S.obsGral[id] != null) return S.obsGral[id]; try { return localStorage.getItem('bh-inc-obs-' + id); } catch (e) { return null; } };
  const obsGralGuardar = (id, v) => { S.obsGral[id] = v; try { v ? localStorage.setItem('bh-inc-obs-' + id, v) : localStorage.removeItem('bh-inc-obs-' + id); } catch (e) { /* sin almacenamiento */ } };

  async function contexto() {
    if (S.usuarioId) return;
    const { data: { user } } = await sb.auth.getUser();
    S.usuarioId = user ? user.id : null;
    const { data } = await sb.from('usuarios_tenant').select('tenant_id').eq('user_id', S.usuarioId).maybeSingle();
    S.tenantId = data ? data.tenant_id : null;
  }

  // ---------- entrada ----------
  async function abrir() {
    const raiz = $('inc-raiz'); if (!raiz) return;
    await contexto();
    const vistas = rolActual === 'administrador' ? [['periodos', 'Periodos'], ['config', 'Configuración']]
      : rolActual === 'nomina' ? [['periodos', 'Periodos']]
      : rolActual === 'coordinador' ? [['hojas', 'Mis hojas']] : [];
    if (!vistas.length) { raiz.innerHTML = '<div class="card"><p class="hint">Esta sección no está disponible para tu rol.</p></div>'; return; }
    if (!S.vista || !vistas.some(v => v[0] === S.vista)) S.vista = vistas[0][0];
    raiz.innerHTML = (vistas.length > 1 ? `<div class="inc-sub">${vistas.map(([k, n]) => `<button type="button" data-inc-vista="${k}" class="${k === S.vista ? 'activo' : ''}">${n}</button>`).join('')}</div>` : '')
      + '<div id="inc-vista"></div>';
    raiz.querySelectorAll('[data-inc-vista]').forEach(b => b.addEventListener('click', () => { S.vista = b.dataset.incVista; S.hoja = null; abrir(); }));
    if (S.vista === 'periodos') return vistaPeriodos();
    if (S.vista === 'config') return vistaConfig();
    if (S.vista === 'hojas') return S.hoja ? vistaHoja(S.hoja.id) : vistaMisHojas();
  }

  // =====================================================================
  // Periodos (Nómina y Administrador)
  // =====================================================================
  async function vistaPeriodos() {
    const cont = $('inc-vista');
    const emps = (typeof empresas !== 'undefined' ? empresas : []).filter(e => e.activo !== false);
    const pers = (typeof periodicidades !== 'undefined' ? periodicidades : []);
    cont.innerHTML = `<div class="card">
      <div class="inc-cab"><div><h2>Periodos de incidencias</h2><p class="hint">Cada periodo abre una hoja por coordinador. Los coordinadores capturan, envían y la hoja queda cerrada para ellos.</p></div></div>
      <div class="inc-fila">
        <div><label for="inc-p-emp">Empresa</label><select id="inc-p-emp">${emps.map(e => `<option value="${esc(e.id)}">${esc(e.nombre)}</option>`).join('')}</select></div>
        <div><label for="inc-p-per">Periodicidad</label><select id="inc-p-per">${pers.map(p => `<option value="${esc(p.id)}" data-dias="${esc(p.dias_default || 7)}">${esc(p.nombre)}</option>`).join('')}</select></div>
        <div><label for="inc-p-ini">Inicio</label><input type="date" id="inc-p-ini"></div>
        <div><label for="inc-p-fin">Fin</label><input type="date" id="inc-p-fin"></div>
      </div>
      <div class="inc-acciones"><button type="button" class="primary" id="inc-p-crear">Crear periodo</button><span class="inc-nota">El fin se calcula con los días de la periodicidad; puedes ajustarlo.</span></div>
      <div class="inc-msg" id="inc-p-msg"></div>
      <div id="inc-p-lista"><p class="hint">Cargando…</p></div>
      <p class="inc-nota">El tablero de quién falta por enviar, la revisión con importes y el concentrado son la siguiente etapa.</p>
    </div>`;
    const ajustarFin = () => {
      const ini = $('inc-p-ini').value; const opt = $('inc-p-per').selectedOptions[0];
      if (ini && opt) $('inc-p-fin').value = sumar(ini, Math.max(1, Math.round(num(opt.dataset.dias))) - 1);
    };
    const hoy = new Date(); const lun = new Date(Date.UTC(hoy.getFullYear(), hoy.getMonth(), hoy.getDate()));
    lun.setUTCDate(lun.getUTCDate() + ((8 - (lun.getUTCDay() || 7)) % 7 || 7));
    $('inc-p-ini').value = lun.toISOString().slice(0, 10); ajustarFin();
    $('inc-p-ini').addEventListener('change', ajustarFin); $('inc-p-per').addEventListener('change', ajustarFin);
    $('inc-p-crear').addEventListener('click', async () => {
      const b = $('inc-p-crear'); b.disabled = true;
      const { error } = await sb.rpc('inc_crear_periodo', { p_empresa: $('inc-p-emp').value, p_periodicidad: $('inc-p-per').value || null, p_inicio: $('inc-p-ini').value, p_fin: $('inc-p-fin').value });
      b.disabled = false;
      if (error) return msg('inc-p-msg', 'err', limpiarError(error));
      msg('inc-p-msg', 'ok', 'Periodo creado. Los coordinadores ya pueden abrir su hoja.'); listarPeriodos();
    });
    listarPeriodos();
  }
  async function listarPeriodos() {
    const { data, error } = await sb.from('inc_periodos').select('id, empresa_id, inicio, fin, procesado_en').order('inicio', { ascending: false }).limit(60);
    const el = $('inc-p-lista'); if (!el) return;
    if (error) { el.innerHTML = `<div class="inc-msg err" style="display:block">${esc(limpiarError(error))}</div>`; return; }
    if (!data.length) { el.innerHTML = '<p class="hint">Todavía no hay periodos.</p>'; return; }
    const { data: hojas } = await sb.from('inc_hojas').select('periodo_id, estado, tipo');
    const porPer = new Map(); (hojas || []).filter(h => h.tipo === 'normal').forEach(h => { const a = porPer.get(h.periodo_id) || { env: 0, tot: 0 }; a.tot++; if (h.estado !== 'borrador') a.env++; porPer.set(h.periodo_id, a); });
    el.innerHTML = `<table class="inc-lista"><thead><tr><th>Empresa</th><th>Periodo</th><th>Hojas enviadas</th><th>Estado</th></tr></thead><tbody>${data.map(p => {
      const a = porPer.get(p.id) || { env: 0, tot: 0 };
      return `<tr><td>${esc(nombreEmpresa(p.empresa_id))}</td><td>${esc(fechaLarga(p.inicio))} – ${esc(fechaLarga(p.fin))}</td><td>${a.env} de ${a.tot} abiertas</td><td>${p.procesado_en ? '<span class="inc-estado procesada">Procesado</span>' : '<span class="inc-estado borrador">Abierto</span>'}</td></tr>`;
    }).join('')}</tbody></table>`;
  }

  // =====================================================================
  // Configuración (Administrador)
  // =====================================================================
  const TIPOS = [['horas_extra', 'Horas extra'], ['domingo', 'Domingo trabajado'], ['turno', 'Turno'], ['descuento', 'Descuento operativo'], ['otro', 'Otro']];
  const UNIDADES = [['horas', 'Horas'], ['turnos', 'Turnos'], ['dias', 'Días'], ['importe', 'Importe']];
  const MODOS = [['beehuman', 'Calcula BeeHuman'], ['tarifa', 'Tarifa propia'], ['sin_importe', 'Sin importe']];
  const PLANTILLAS = {
    he: { nombre: 'Horas extra', abreviatura: 'HE', tipo: 'horas_extra', unidad: 'horas', modo: 'beehuman', factor: 2 },
    dom: { nombre: 'Domingo trabajado', abreviatura: 'DOM', tipo: 'domingo', unidad: 'dias', modo: 'beehuman' },
    tn: { nombre: 'Turno nocturno', abreviatura: 'T', tipo: 'turno', unidad: 'turnos', modo: 'tarifa', tarifa: 700 },
    desc: { nombre: 'Descuento operativo', abreviatura: 'DESC', tipo: 'descuento', unidad: 'importe', modo: 'tarifa', tarifa: 1 }
  };
  const opciones = (lista, v) => lista.map(([k, n]) => `<option value="${k}" ${k === v ? 'selected' : ''}>${n}</option>`).join('');

  async function vistaConfig() {
    const cont = $('inc-vista');
    const emps = (typeof empresas !== 'undefined' ? empresas : []).filter(e => e.activo !== false);
    if (!S.cfg.empresaId && emps.length) S.cfg.empresaId = emps[0].id;
    cont.innerHTML = `<div class="card">
      <div class="inc-cab"><div><h2>Configuración de incidencias</h2><p class="hint">Conceptos, cálculo y responsables por empresa. Los cambios no alteran hojas ya enviadas: cada envío conserva la configuración con la que se calculó.</p></div>
      <div style="min-width:240px"><label for="inc-c-emp" class="inc-nota">Empresa</label><select id="inc-c-emp">${emps.map(e => `<option value="${esc(e.id)}" ${e.id === S.cfg.empresaId ? 'selected' : ''}>${esc(e.nombre)}</option>`).join('')}</select></div></div>
      <div id="inc-c-cuerpo"><p class="hint">Cargando…</p></div></div>`;
    $('inc-c-emp').addEventListener('change', e => { S.cfg.empresaId = e.target.value; S.cfg.editando = null; cargarConfig(); });
    cargarConfig();
  }
  async function cargarConfig() {
    const emp = S.cfg.empresaId;
    const [prm, con, are] = await Promise.all([
      sb.from('inc_parametros').select('*').eq('empresa_id', emp).maybeSingle(),
      sb.from('inc_conceptos').select('*').eq('empresa_id', emp).order('orden').order('nombre'),
      sb.from('areas').select('id, nombre').order('nombre')
    ]);
    const err = prm.error || con.error;
    if (err) { $('inc-c-cuerpo').innerHTML = `<div class="inc-msg err" style="display:block">${esc(limpiarError(err))}</div>`; return; }
    S.cfg.prm = prm.data; S.cfg.conceptos = con.data || []; S.cfg.areas = are.data || [];
    const ids = S.cfg.conceptos.map(c => c.id);
    const ta = ids.length ? await sb.from('inc_tarifas_area').select('*').in('concepto_id', ids) : { data: [] };
    S.cfg.tarifas = ta.data || [];
    pintarConfig();
  }
  function pintarConfig() {
    const p = S.cfg.prm || { base_calculo: 'mixto', jornada_horas: 8, umbral_triples_semana: 9, factor_triple: 3, aviso_horas_dia: 3, aviso_dias_semana: 3, prima_dominical_pct: 25 };
    const resp = (uid) => !uid ? 'Sin designar' : (uid === S.usuarioId ? 'Tú' : 'Otro usuario');
    const ed = S.cfg.editando || {};
    $('inc-c-cuerpo').innerHTML = `
      <h3 style="margin:18px 0 4px">Parámetros de cálculo</h3>
      <div class="inc-fila">
        <div><label for="inc-c-base">Base de cálculo</label><select id="inc-c-base">${opciones([['mixto', 'Mixto (todos los esquemas)'], ['bruto', 'Solo bruto'], ['neto', 'Solo neto']], p.base_calculo)}</select></div>
        <div><label for="inc-c-jor">Horas de la jornada</label><input id="inc-c-jor" type="number" step="0.5" min="1" value="${esc(p.jornada_horas)}"></div>
        <div><label for="inc-c-umb">Horas dobles por semana antes de triples</label><input id="inc-c-umb" type="number" step="0.5" min="0" value="${esc(p.umbral_triples_semana)}"></div>
        <div><label for="inc-c-ftr">Factor de horas triples</label><input id="inc-c-ftr" type="number" step="0.1" min="0" value="${esc(p.factor_triple)}"></div>
        <div><label for="inc-c-avh">Aviso: horas extra por día</label><input id="inc-c-avh" type="number" step="0.5" min="0" value="${esc(p.aviso_horas_dia)}"></div>
        <div><label for="inc-c-avd">Aviso: días con horas extra por semana</label><input id="inc-c-avd" type="number" step="1" min="0" value="${esc(p.aviso_dias_semana)}"></div>
        <div><label for="inc-c-pdm">Prima dominical (%)</label><input id="inc-c-pdm" type="number" step="0.5" min="0" value="${esc(p.prima_dominical_pct)}"></div>
      </div>
      <div class="inc-acciones"><button type="button" class="primary" id="inc-c-guardar-prm">Guardar parámetros</button>
        <span class="inc-nota">Historial de asignaciones desde: ${p.inicio_historial ? esc(fechaLarga(p.inicio_historial)) : 'se fija al crear el primer periodo'}</span></div>
      <div class="inc-msg" id="inc-c-msg-prm"></div>

      <h3 style="margin:18px 0 4px">Responsables que firman</h3>
      <p class="hint">Nómina: <b>${resp(p.responsable_nomina_user)}</b> · RH: <b>${resp(p.responsable_rh_user)}</b></p>
      <div class="inc-acciones"><button type="button" class="inc-sec" data-inc-resp="responsable_nomina_user">Designarme responsable de Nómina</button>
        <button type="button" class="inc-sec" data-inc-resp="responsable_rh_user">Designarme responsable de RH</button></div>
      <p class="inc-nota">Para designar a otra persona, BeeHuman necesita una función que liste los usuarios de Nómina y Administrador; hoy la base no permite listarlos. Queda como pendiente con su propia autorización.</p>
      <div class="inc-msg" id="inc-c-msg-resp"></div>

      <h3 style="margin:18px 0 4px">Conceptos (columnas de la hoja)</h3>
      <div class="inc-acciones"><span class="inc-nota">Agregar rápido:</span>
        ${Object.entries(PLANTILLAS).map(([k, t]) => `<button type="button" class="inc-sec" data-inc-plantilla="${k}">${esc(t.nombre)}</button>`).join('')}</div>
      ${S.cfg.conceptos.length ? `<div class="inc-tabla-wrap" style="max-height:none"><table class="inc-lista"><thead><tr><th>Columna</th><th>Concepto</th><th>Unidad</th><th>Cálculo</th><th>Tarifa / factor</th><th>Estado</th><th></th></tr></thead><tbody>
        ${S.cfg.conceptos.map(c => `<tr><td><b>${esc(c.abreviatura)}</b></td><td>${esc(c.nombre)}</td><td>${esc((UNIDADES.find(u => u[0] === c.unidad) || [, c.unidad])[1])}</td>
          <td>${esc((MODOS.find(m => m[0] === c.modo) || [, c.modo])[1])}</td>
          <td>${c.tipo === 'descuento' ? 'Importe capturado' : c.tarifa != null ? esc(dinero(c.tarifa)) + (S.cfg.tarifas.some(t => t.concepto_id === c.id) ? ' + por área' : '') : c.factor != null ? '× ' + esc(c.factor) : c.tipo === 'domingo' ? 'Prima dominical' : '—'}</td>
          <td>${c.activo ? '<span class="inc-estado enviada">Activo</span>' : '<span class="inc-estado borrador">Inactivo</span>'}</td>
          <td><button type="button" class="inc-sec" data-inc-editar="${esc(c.id)}">Editar</button></td></tr>`).join('')}</tbody></table></div>`
        : '<p class="hint">Sin conceptos todavía. Usa «Agregar rápido» o el formulario.</p>'}
      <h3 style="margin:18px 0 4px" id="inc-c-form-titulo">${ed.id ? 'Editar concepto' : 'Nuevo concepto'}</h3>
      <div class="inc-fila">
        <div><label for="inc-k-nom">Nombre</label><input id="inc-k-nom" maxlength="60" value="${esc(ed.nombre || '')}"></div>
        <div><label for="inc-k-abr">Abreviatura (columna)</label><input id="inc-k-abr" maxlength="6" value="${esc(ed.abreviatura || '')}"></div>
        <div><label for="inc-k-tipo">Tipo</label><select id="inc-k-tipo">${opciones(TIPOS, ed.tipo || 'horas_extra')}</select></div>
        <div><label for="inc-k-uni">Unidad</label><select id="inc-k-uni">${opciones(UNIDADES, ed.unidad || 'horas')}</select></div>
        <div><label for="inc-k-modo">Cálculo</label><select id="inc-k-modo">${opciones(MODOS, ed.modo || 'beehuman')}</select></div>
        <div><label for="inc-k-tar">Tarifa por unidad (opcional)</label><input id="inc-k-tar" type="number" step="0.01" min="0" value="${esc(ed.tarifa ?? '')}"></div>
        <div><label for="inc-k-fac">Factor (× sueldo o × hora)</label><input id="inc-k-fac" type="number" step="0.01" min="0" value="${esc(ed.factor ?? '')}"></div>
        <div><label for="inc-k-ord">Orden</label><input id="inc-k-ord" type="number" step="1" value="${esc(ed.orden ?? S.cfg.conceptos.length + 1)}"></div>
      </div>
      <p class="inc-nota" id="inc-k-ayuda"></p>
      <div class="inc-acciones"><button type="button" class="primary" id="inc-k-guardar">${ed.id ? 'Guardar cambios' : 'Agregar concepto'}</button>
        ${ed.id ? `<button type="button" class="inc-sec" id="inc-k-activo">${ed.activo ? 'Desactivar' : 'Activar'}</button><button type="button" class="inc-sec" id="inc-k-cancelar">Cancelar</button>` : ''}</div>
      <div class="inc-msg" id="inc-c-msg-con"></div>
      ${ed.id && (ed.modo === 'tarifa' || ed.tipo === 'domingo') && ed.tipo !== 'descuento' ? `
        <h3 style="margin:18px 0 4px">Tarifa por área para ${esc(ed.nombre)}</h3>
        <p class="hint">Sustituye la tarifa general para las personas de esa área.</p>
        ${S.cfg.tarifas.filter(t => t.concepto_id === ed.id).map(t => `<div class="inc-acciones"><span>${esc((S.cfg.areas.find(a => a.id === t.area_id) || {}).nombre || 'Área')}: <b>${esc(dinero(t.tarifa))}</b></span><button type="button" class="inc-peligro" data-inc-quitar-tarifa="${esc(t.id)}">Quitar</button></div>`).join('')}
        <div class="inc-fila"><div><label for="inc-t-area">Área</label><select id="inc-t-area">${S.cfg.areas.map(a => `<option value="${esc(a.id)}">${esc(a.nombre)}</option>`).join('')}</select></div>
          <div><label for="inc-t-monto">Tarifa</label><input id="inc-t-monto" type="number" step="0.01" min="0"></div>
          <div><button type="button" class="inc-sec" id="inc-t-agregar">Agregar tarifa por área</button></div></div>
        <div class="inc-msg" id="inc-c-msg-tar"></div>` : ''}`;
    const ayuda = () => {
      const t = $('inc-k-tipo').value, m = $('inc-k-modo').value;
      const textos = {
        horas_extra: 'Calcula BeeHuman: sueldo diario ÷ horas de jornada × factor (2 = doble); lo que pase del umbral semanal se paga con el factor de triples.',
        domingo: 'Si tiene tarifa (general o por área) esa es el pago completo; si no, se calcula la prima dominical sobre el sueldo diario.',
        turno: m === 'tarifa' ? 'Tarifa fija por turno.' : 'Calcula BeeHuman: sueldo diario × factor (por ejemplo 0.25 = 25 % de prima).',
        descuento: 'Importe capturado por el coordinador con motivo y conformidad; Nómina decide si se aplica.',
        otro: m === 'tarifa' ? 'Cantidad × tarifa.' : m === 'sin_importe' ? 'Solo cantidades, sin importe.' : 'Calcula BeeHuman: cantidad × sueldo diario × factor.'
      };
      $('inc-k-ayuda').textContent = textos[t] || '';
      if (t === 'descuento') { $('inc-k-uni').value = 'importe'; $('inc-k-modo').value = 'tarifa'; $('inc-k-tar').value = 1; }
    };
    ['inc-k-tipo', 'inc-k-modo'].forEach(id => $(id).addEventListener('change', ayuda)); ayuda();
    $('inc-c-guardar-prm').addEventListener('click', guardarParametros);
    document.querySelectorAll('[data-inc-resp]').forEach(b => b.addEventListener('click', () => designar(b.dataset.incResp)));
    document.querySelectorAll('[data-inc-plantilla]').forEach(b => b.addEventListener('click', () => { S.cfg.editando = Object.assign({}, PLANTILLAS[b.dataset.incPlantilla]); pintarConfig(); $('inc-k-nom').focus(); }));
    document.querySelectorAll('[data-inc-editar]').forEach(b => b.addEventListener('click', () => { S.cfg.editando = Object.assign({}, S.cfg.conceptos.find(c => c.id === b.dataset.incEditar)); pintarConfig(); }));
    $('inc-k-guardar').addEventListener('click', guardarConcepto);
    if ($('inc-k-cancelar')) $('inc-k-cancelar').addEventListener('click', () => { S.cfg.editando = null; pintarConfig(); });
    if ($('inc-k-activo')) $('inc-k-activo').addEventListener('click', async () => {
      const { error } = await sb.from('inc_conceptos').update({ activo: !ed.activo }).eq('id', ed.id);
      if (error) return msg('inc-c-msg-con', 'err', limpiarError(error));
      S.cfg.editando = null; cargarConfig();
    });
    if ($('inc-t-agregar')) $('inc-t-agregar').addEventListener('click', async () => {
      const monto = $('inc-t-monto').value;
      if (monto === '') return msg('inc-c-msg-tar', 'err', 'Escribe la tarifa.');
      const { error } = await sb.from('inc_tarifas_area').insert({ tenant_id: S.tenantId, concepto_id: ed.id, area_id: $('inc-t-area').value, tarifa: num(monto) });
      if (error) return msg('inc-c-msg-tar', 'err', error.code === '23505' ? 'Esa área ya tiene tarifa para este concepto.' : limpiarError(error));
      cargarConfig();
    });
    document.querySelectorAll('[data-inc-quitar-tarifa]').forEach(b => b.addEventListener('click', async () => {
      const { error } = await sb.from('inc_tarifas_area').delete().eq('id', b.dataset.incQuitarTarifa);
      if (error) return msg('inc-c-msg-tar', 'err', limpiarError(error));
      cargarConfig();
    }));
  }
  async function guardarParametros() {
    const v = {
      base_calculo: $('inc-c-base').value, jornada_horas: num($('inc-c-jor').value), umbral_triples_semana: num($('inc-c-umb').value),
      factor_triple: num($('inc-c-ftr').value), aviso_horas_dia: num($('inc-c-avh').value), aviso_dias_semana: Math.round(num($('inc-c-avd').value)),
      prima_dominical_pct: num($('inc-c-pdm').value), actualizado_por: S.usuarioId, actualizado_en: new Date().toISOString()
    };
    if (v.jornada_horas <= 0) return msg('inc-c-msg-prm', 'err', 'Las horas de la jornada deben ser mayores a cero.');
    const r = S.cfg.prm ? await sb.from('inc_parametros').update(v).eq('empresa_id', S.cfg.empresaId)
      : await sb.from('inc_parametros').insert(Object.assign({ empresa_id: S.cfg.empresaId, tenant_id: S.tenantId }, v));
    if (r.error) return msg('inc-c-msg-prm', 'err', limpiarError(r.error));
    await cargarConfig(); msg('inc-c-msg-prm', 'ok', 'Parámetros guardados. Aplican a las hojas que se envíen desde ahora.');
  }
  async function designar(campo) {
    const r = S.cfg.prm ? await sb.from('inc_parametros').update({ [campo]: S.usuarioId }).eq('empresa_id', S.cfg.empresaId)
      : await sb.from('inc_parametros').insert({ empresa_id: S.cfg.empresaId, tenant_id: S.tenantId, [campo]: S.usuarioId });
    if (r.error) return msg('inc-c-msg-resp', 'err', limpiarError(r.error));
    await cargarConfig(); msg('inc-c-msg-resp', 'ok', 'Responsable designado.');
  }
  async function guardarConcepto() {
    const ed = S.cfg.editando || {};
    const v = {
      nombre: $('inc-k-nom').value.trim(), abreviatura: $('inc-k-abr').value.trim().toUpperCase(), tipo: $('inc-k-tipo').value,
      unidad: $('inc-k-uni').value, modo: $('inc-k-modo').value, orden: Math.round(num($('inc-k-ord').value)),
      tarifa: $('inc-k-tar').value === '' ? null : num($('inc-k-tar').value), factor: $('inc-k-fac').value === '' ? null : num($('inc-k-fac').value)
    };
    if (!v.nombre || !v.abreviatura) return msg('inc-c-msg-con', 'err', 'Nombre y abreviatura son obligatorios.');
    if (v.modo === 'tarifa' && v.tarifa == null) return msg('inc-c-msg-con', 'err', 'El cálculo «Tarifa propia» necesita una tarifa.');
    if (v.tipo === 'horas_extra' && v.modo === 'beehuman' && v.factor == null) v.factor = 2;
    const r = ed.id ? await sb.from('inc_conceptos').update(v).eq('id', ed.id)
      : await sb.from('inc_conceptos').insert(Object.assign({ tenant_id: S.tenantId, empresa_id: S.cfg.empresaId, activo: true }, v));
    if (r.error) return msg('inc-c-msg-con', 'err', r.error.code === '23505' ? 'Ya existe un concepto con esa abreviatura en la empresa.' : limpiarError(r.error));
    S.cfg.editando = null; await cargarConfig(); msg('inc-c-msg-con', 'ok', 'Concepto guardado.');
  }

  // =====================================================================
  // Coordinador: mis hojas
  // =====================================================================
  async function vistaMisHojas() {
    const cont = $('inc-vista');
    cont.innerHTML = `<div class="card"><h2>Mis hojas de incidencias</h2>
      <p class="hint">Captura lo que no fue un día normal de tu gente y envía la hoja al cerrar el periodo. Al enviarla queda cerrada para ti; si hay un error, Nómina te la devuelve o puedes mandar un complemento.</p>
      <div id="inc-h-lista"><p class="hint">Cargando…</p></div><div class="inc-msg" id="inc-h-msg"></div></div>`;
    if (!rolPersonalId) { $('inc-h-lista').innerHTML = '<p class="hint">Tu usuario no está ligado a una ficha de persona. Pide al administrador que lo vincule.</p>'; return; }
    const [per, hj] = await Promise.all([
      sb.from('inc_periodos').select('id, empresa_id, inicio, fin, procesado_en').order('inicio', { ascending: false }).limit(30),
      sb.from('inc_hojas').select('id, periodo_id, tipo, estado, version_actual, hoja_raiz_id, creado_en').order('creado_en')
    ]);
    if (per.error || hj.error) { $('inc-h-lista').innerHTML = `<div class="inc-msg err" style="display:block">${esc(limpiarError(per.error || hj.error))}</div>`; return; }
    if (!per.data.length) { $('inc-h-lista').innerHTML = '<p class="hint">Nómina todavía no abre ningún periodo.</p>'; return; }
    const hojas = hj.data || [];
    $('inc-h-lista').innerHTML = `<table class="inc-lista"><thead><tr><th>Periodo</th><th>Empresa</th><th>Mi hoja</th><th></th></tr></thead><tbody>${per.data.map(p => {
      const h = hojas.find(x => x.periodo_id === p.id && x.tipo === 'normal');
      const comps = hojas.filter(x => x.periodo_id === p.id && x.tipo === 'complemento');
      const estado = h ? `<span class="inc-estado ${h.estado}">${ESTADOS[h.estado]}</span>` : (p.procesado_en ? '<span class="inc-estado procesada">Procesado</span>' : '<span class="inc-estado borrador">Sin abrir</span>');
      const accion = h ? `<button type="button" class="inc-sec" data-inc-hoja="${esc(h.id)}">${h.estado === 'borrador' || h.estado === 'devuelta' ? 'Capturar' : 'Ver'}</button>`
        : (p.procesado_en ? '' : `<button type="button" class="primary" style="margin:0" data-inc-abrir="${esc(p.id)}">Abrir hoja</button>`);
      return `<tr><td>${esc(fechaLarga(p.inicio))} – ${esc(fechaLarga(p.fin))}</td><td>${esc(nombreEmpresa(p.empresa_id) || '—')}</td><td>${estado}${comps.length ? ` <span class="inc-nota">+ ${comps.length} complemento${comps.length > 1 ? 's' : ''}</span>` : ''}</td><td>${accion}
        ${comps.map((c, i) => `<button type="button" class="inc-sec" data-inc-hoja="${esc(c.id)}">Complemento ${i + 1}</button>`).join(' ')}</td></tr>`;
    }).join('')}</tbody></table>`;
    document.querySelectorAll('[data-inc-hoja]').forEach(b => b.addEventListener('click', () => { S.hoja = { id: b.dataset.incHoja }; vistaHoja(b.dataset.incHoja); }));
    document.querySelectorAll('[data-inc-abrir]').forEach(b => b.addEventListener('click', async () => {
      const { data, error } = await sb.rpc('inc_abrir_hoja', { p_periodo: b.dataset.incAbrir });
      if (error) return msg('inc-h-msg', 'err', limpiarError(error));
      S.hoja = { id: data }; vistaHoja(data);
    }));
  }

  // =====================================================================
  // Coordinador: la hoja
  // =====================================================================
  async function vistaHoja(hojaId) {
    const cont = $('inc-vista');
    cont.innerHTML = '<div class="card"><p class="hint">Cargando la hoja…</p></div>';
    const { data: h, error: e1 } = await sb.from('inc_hojas').select('*').eq('id', hojaId).maybeSingle();
    if (e1 || !h) { cont.innerHTML = `<div class="card"><div class="inc-msg err" style="display:block">${esc(limpiarError(e1 || 'No se encontró la hoja.'))}</div></div>`; return; }
    const [pe, gente, ce, ca, ob, co, ev, pr] = await Promise.all([
      sb.from('inc_periodos').select('*').eq('id', h.periodo_id).single(),
      sb.rpc('inc_personas_hoja', { p_hoja: hojaId }),
      sb.from('inc_celdas').select('*').eq('hoja_id', hojaId),
      sb.from('inc_cantidades').select('*').eq('hoja_id', hojaId),
      sb.from('inc_observaciones').select('*').eq('hoja_id', hojaId),
      sb.from('inc_conceptos').select('*').order('orden').order('nombre'),
      sb.from('inc_eventos').select('*').eq('hoja_id', hojaId).order('creado_en', { ascending: false }),
      sb.from('proyectos').select('id, nombre').order('nombre')
    ]);
    const err = pe.error || gente.error || ce.error || ca.error || ob.error || co.error;
    if (err) { cont.innerHTML = `<div class="card"><div class="inc-msg err" style="display:block">${esc(limpiarError(err))}</div></div>`; return; }
    const periodo = pe.data;
    const conceptos = (co.data || []).filter(c => c.empresa_id === periodo.empresa_id && (c.activo || (ca.data || []).some(q => q.concepto_id === c.id)));
    const ids = conceptos.map(c => c.id);
    const [ta, prm, raiz] = await Promise.all([
      ids.length ? sb.from('inc_tarifas_area').select('*').in('concepto_id', ids) : { data: [] },
      sb.from('inc_parametros').select('*').eq('empresa_id', periodo.empresa_id).maybeSingle(),
      h.tipo === 'complemento' ? sb.from('inc_cantidades').select('personal_id, fecha, concepto_id, cantidad').eq('hoja_id', h.hoja_raiz_id) : { data: [] }
    ]);
    // personas y días permitidos (según el historial de asignaciones)
    const personas = new Map();
    (gente.data || []).forEach(r => {
      if (!personas.has(r.personal_id)) personas.set(r.personal_id, { id: r.personal_id, nombre: r.nombre_completo, empleado: r.empleado_id, area: r.area_id, proyecto: r.proyecto_id, dias: new Set() });
      personas.get(r.personal_id).dias.add(r.fecha);
    });
    const mapa = (arr, k) => new Map((arr || []).map(x => [k(x), Object.assign({}, x)]));
    S.hoja = {
      id: hojaId, h, periodo, conceptos, personas: [...personas.values()], dias: rango(periodo.inicio, periodo.fin),
      tarifas: ta.data || [], prm: prm.data || { aviso_horas_dia: 3, aviso_dias_semana: 3 }, proyectos: pr.error ? [] : (pr.data || []),
      celdas: mapa(ce.data, x => x.personal_id + '|' + x.fecha), cant: mapa(ca.data, x => x.personal_id + '|' + x.fecha + '|' + x.concepto_id),
      obs: mapa(ob.data, x => x.personal_id), eventos: ev.data || [], raiz: raiz.data || [],
      vista: (S.hoja && S.hoja.id === hojaId && S.hoja.vista) || 'asistencia', sucio: false, confirmarEnvio: false
    };
    if (['borrador', 'devuelta'].includes(h.estado) && obsGralLeer(hojaId) != null) S.hoja.h.observacion_general = obsGralLeer(hojaId);
    S.hoja.orig = { celdas: new Map([...S.hoja.celdas].map(([k, v]) => [k, Object.assign({}, v)])), cant: new Map([...S.hoja.cant].map(([k, v]) => [k, Object.assign({}, v)])), obs: new Map([...S.hoja.obs].map(([k, v]) => [k, Object.assign({}, v)])) };
    pintarHoja();
  }

  const editable = () => S.hoja && ['borrador', 'devuelta'].includes(S.hoja.h.estado);
  function tarifaDe(c, persona) {
    const t = S.hoja.tarifas.find(x => x.concepto_id === c.id && x.area_id === persona.area);
    return t ? Number(t.tarifa) : (c.tarifa != null ? Number(c.tarifa) : null);
  }
  // El coordinador solo ve importes que no dependen del sueldo.
  function importeVisible(c, persona, cant) {
    if (c.tipo === 'descuento') return cant;
    if (c.modo === 'tarifa' || (c.tipo === 'domingo' && tarifaDe(c, persona) != null)) { const t = tarifaDe(c, persona); return t == null ? null : cant * t; }
    return null;
  }
  function avisos(p) {
    const he = S.hoja.conceptos.filter(c => c.tipo === 'horas_extra').map(c => c.id);
    if (!he.length) return [];
    const porDia = new Map();
    S.hoja.dias.forEach(f => { let s = 0; he.forEach(cid => { const q = S.hoja.cant.get(p.id + '|' + f + '|' + cid); if (q) s += num(q.cantidad); }); if (s > 0) porDia.set(f, s); });
    const out = [];
    const maxDia = num(S.hoja.prm.aviso_horas_dia), maxDias = num(S.hoja.prm.aviso_dias_semana);
    const dExc = [...porDia].filter(([, s]) => maxDia > 0 && s > maxDia).map(([f]) => dia(f));
    if (dExc.length) out.push(`Más de ${maxDia} h extra: ${dExc.join(', ')}`);
    const porSem = new Map(); [...porDia.keys()].forEach(f => porSem.set(semana(f), (porSem.get(semana(f)) || 0) + 1));
    if ([...porSem.values()].some(n => maxDias > 0 && n > maxDias)) out.push(`Horas extra en más de ${maxDias} días de la semana`);
    return out;
  }

  function pintarHoja() {
    const H = S.hoja, ed = editable(), dis = ed ? '' : 'disabled';
    const cont = $('inc-vista');
    const dev = H.h.estado === 'devuelta' ? H.eventos.find(e => e.tipo === 'devolucion') : null;
    const vistas = [['asistencia', 'Asistencia'], ...H.conceptos.map(c => [c.id, c.abreviatura + ' · ' + c.nombre]), ...(H.proyectos.length ? [['proyecto', 'Proyecto por día']] : [])];
    const cDesc = H.conceptos.find(c => c.id === H.vista && c.tipo === 'descuento');
    const conc = H.conceptos.find(c => c.id === H.vista);
    const enRaiz = (pid, f, cid) => H.raiz.find(q => q.personal_id === pid && q.fecha === f && q.concepto_id === cid);
    const celda = (p, f) => {
      if (!p.dias.has(f)) return '<td class="inc-fuera" title="Sin asignación contigo este día">—</td>';
      const k = p.id + '|' + f;
      if (H.vista === 'asistencia') {
        const c = H.celdas.get(k), v = c && c.codigo || '';
        return `<td class="${v ? 'inc-cod-' + v : ''}"><select data-k="${k}" data-campo="codigo" aria-label="${esc(p.nombre)} ${dia(f)}" ${dis}>${CODIGOS.map(([val, t]) => `<option value="${val}" ${val === v ? 'selected' : ''}>${t}</option>`).join('')}</select></td>`;
      }
      if (H.vista === 'proyecto') {
        const c = H.celdas.get(k), v = c && c.proyecto_id || '';
        return `<td><select class="inc-proy" data-k="${k}" data-campo="proyecto_id" aria-label="Proyecto ${esc(p.nombre)} ${dia(f)}" ${dis}><option value="">${esc(nombreProyecto(p.proyecto) || 'De la ficha')}</option>${H.proyectos.map(x => `<option value="${esc(x.id)}" ${x.id === v ? 'selected' : ''}>${esc(x.nombre)}</option>`).join('')}</select></td>`;
      }
      const q = H.cant.get(k + '|' + H.vista), r = enRaiz(p.id, f, H.vista);
      if (r) return `<td title="Ya enviado en la hoja original">${esc(Number(r.cantidad))}</td>`;
      return `<td><input type="number" min="0" step="${conc && conc.unidad === 'importe' ? '0.01' : '0.5'}" inputmode="decimal" data-k="${k}|${H.vista}" data-campo="cantidad" value="${q ? esc(Number(q.cantidad)) : ''}" aria-label="${esc(conc ? conc.abreviatura : '')} ${esc(p.nombre)} ${dia(f)}" ${dis}></td>`;
    };
    const totales = p => H.conceptos.map(c => `<td class="inc-total" data-tot="${esc(p.id)}|${esc(c.id)}">${totalHtml(p, c)}</td>`).join('');
    const extra = p => {
      if (H.vista === 'asistencia') { const o = H.obs.get(p.id); return `<td><input class="inc-texto" data-obs="${esc(p.id)}" value="${esc(o ? o.texto : '')}" placeholder="Observación" aria-label="Observación ${esc(p.nombre)}" ${dis}></td>`; }
      if (cDesc) {
        const q = H.dias.map(f => H.cant.get(p.id + '|' + f + '|' + cDesc.id)).find(Boolean) || {};
        return `<td><input class="inc-texto" data-desc-motivo="${esc(p.id)}" value="${esc(q.motivo || '')}" placeholder="Motivo (obligatorio)" ${dis}></td><td><label style="font-size:12px;white-space:nowrap"><input type="checkbox" data-desc-conf="${esc(p.id)}" ${q.conformidad_declarada ? 'checked' : ''} ${dis} style="width:auto"> El trabajador está de acuerdo</label></td>`;
      }
      return '';
    };
    const sumaCol = f => `<td data-sum="${f}">${conc ? sumaHtml(f, conc) : ''}</td>`;
    const titulo = H.h.tipo === 'complemento' ? `Complemento · ${H.h.posterior_procesamiento ? 'posterior al procesamiento' : 'antes del procesamiento'}` : 'Hoja de incidencias';
    cont.innerHTML = `<div class="card">
      <div class="inc-cab"><div><p class="inc-nota" style="margin:0"><a href="#" id="inc-volver">‹ Mis hojas</a></p><h2>${titulo}</h2>
        <p class="hint" style="margin:4px 0 0">${esc(conEmpresa(H.periodo.empresa_id))}${esc(fechaLarga(H.periodo.inicio))} – ${esc(fechaLarga(H.periodo.fin))}</p></div>
        <div><span class="inc-estado ${H.h.estado}">${ESTADOS[H.h.estado]}</span>${H.h.version_actual ? ` <span class="inc-nota">Versión ${H.h.version_actual}</span>` : ''}</div></div>
      ${dev ? `<div class="inc-msg err" style="display:block"><b>Devuelta por ${esc(dev.nombre || 'Nómina')}:</b> ${esc(dev.motivo)}</div>` : ''}
      ${H.h.tipo === 'complemento' ? '<div class="inc-msg info" style="display:block">Registra solo lo que faltó en la hoja original. Lo que ya se envió aparece como dato fijo y no se puede repetir.</div>' : ''}
      ${!H.personas.length ? '<div class="inc-msg info" style="display:block">No tienes personas asignadas en este periodo y esta empresa.</div>' : ''}
      ${!H.proyectos.length && ed ? '<p class="inc-nota" id="inc-nota-proyecto">Proyecto por día: pendiente. Tu usuario no tiene acceso al catálogo de proyectos; habilitarlo requiere una función nueva en la base. Mientras tanto, anótalo en la observación de la persona.</p>' : ''}
      <div class="inc-seg" role="tablist">${vistas.map(([k, n]) => `<button type="button" data-inc-v="${esc(k)}" class="${k === H.vista ? 'activo' : ''}">${esc(n)}</button>`).join('')}</div>
      <div class="inc-leyenda">${H.vista === 'asistencia' ? '<span><b>·</b> Asistió</span><span><b>F</b> Falta</span><span><b>I</b> Incapacidad</span><span><b>D</b> Descanso</span><span><b>V</b> Vacaciones</span><span><b>P</b> Permiso</span><span><b>—</b> Sin asignación contigo ese día</span>'
        : H.vista === 'proyecto' ? '<span>Cambia el proyecto solo los días que la persona trabajó en otro; la ficha no se modifica.</span>'
        : conc ? `<span>Captura ${esc(conc.unidad === 'importe' ? 'el importe' : 'la cantidad de ' + conc.unidad)} por día.${conc.modo === 'beehuman' && !(conc.tipo === 'domingo' && conc.tarifa != null) ? ' El importe lo calcula Nómina.' : ''}</span>` : ''}</div>
      <div class="inc-tabla-wrap"><table class="inc-tabla"><thead><tr><th class="inc-col-persona">Colaborador</th>${H.dias.map(f => `<th>${esc(dia(f))}</th>`).join('')}
        ${H.conceptos.map(c => `<th title="${esc(c.nombre)}">${esc(c.abreviatura)}</th>`).join('')}<th>Avisos</th>${H.vista === 'asistencia' ? '<th>Observación</th>' : cDesc ? '<th>Motivo</th><th>Conformidad</th>' : ''}</tr></thead>
        <tbody>${H.personas.map(p => { return `<tr data-pid="${esc(p.id)}"><td class="inc-col-persona"><b>${esc(p.nombre)}</b><small>${esc(p.empleado || '')}</small></td>${H.dias.map(f => celda(p, f)).join('')}${totales(p)}<td data-av="${esc(p.id)}">${avisosHtml(p)}</td>${extra(p)}</tr>`; }).join('')}
        ${conc ? `<tr class="inc-sum"><td class="inc-col-persona">Total del día</td>${H.dias.map(sumaCol).join('')}${H.conceptos.map(() => '<td></td>').join('')}<td></td>${cDesc ? '<td></td><td></td>' : ''}</tr>` : ''}</tbody></table></div>
      <div style="margin-top:14px"><label for="inc-obs-gral" class="inc-nota">Observación general de la hoja (por ejemplo, por qué subieron las horas extra)</label>
        <textarea id="inc-obs-gral" ${dis}>${esc(H.h.observacion_general || '')}</textarea></div>
      <div class="inc-acciones">
        ${ed ? `<button type="button" class="inc-sec" id="inc-guardar">Guardar borrador</button>
          <button type="button" class="primary" style="margin:0" id="inc-enviar">${H.confirmarEnvio ? 'Confirmar: enviar y cerrar' : 'Enviar y cerrar'}</button>
          ${H.confirmarEnvio ? '<span class="inc-nota">Al enviar ya no podrás editarla; solo Nómina puede devolvértela.</span>' : ''}` : ''}
        ${!ed && H.h.tipo === 'normal' ? '<button type="button" class="inc-sec" id="inc-complemento">Agregar complemento</button>' : ''}
        <span class="inc-nota" id="inc-sucio">${H.sucio ? 'Cambios sin guardar' : ''}</span>
      </div>
      <div class="inc-msg" id="inc-msg"></div>
    </div>`;
    $('inc-volver').addEventListener('click', ev => { ev.preventDefault(); salirHoja(); });
    cont.querySelectorAll('[data-inc-v]').forEach(b => b.addEventListener('click', () => { H.vista = b.dataset.incV; H.confirmarEnvio = false; pintarHoja(); }));
    cont.querySelectorAll('select[data-k], input[data-k]').forEach(el => el.addEventListener('change', () => cambiarCelda(el)));
    cont.querySelectorAll('[data-obs]').forEach(el => el.addEventListener('change', () => {
      const o = H.obs.get(el.dataset.obs) || { personal_id: el.dataset.obs }; o.texto = el.value.trim(); H.obs.set(el.dataset.obs, o); marcar();
    }));
    cont.querySelectorAll('[data-desc-motivo]').forEach(el => el.addEventListener('change', () => aplicarDesc(el.dataset.descMotivo, { motivo: el.value.trim() })));
    cont.querySelectorAll('[data-desc-conf]').forEach(el => el.addEventListener('change', () => aplicarDesc(el.dataset.descConf, { conformidad_declarada: el.checked })));
    const og = $('inc-obs-gral'); if (og) og.addEventListener('change', () => { H.h.observacion_general = og.value; obsGralGuardar(H.id, og.value); marcar(); });
    if ($('inc-guardar')) $('inc-guardar').addEventListener('click', async () => { const ok = await guardar(); if (ok) { await vistaHoja(H.id); msg('inc-msg', 'ok', 'Borrador guardado.'); } });
    if ($('inc-enviar')) $('inc-enviar').addEventListener('click', enviar);
    if ($('inc-complemento')) $('inc-complemento').addEventListener('click', async () => {
      const { data, error } = await sb.rpc('inc_abrir_hoja', { p_periodo: H.periodo.id, p_complemento_de: H.id });
      if (error) return msg('inc-msg', 'err', limpiarError(error));
      S.hoja = { id: data }; vistaHoja(data);
    });
  }
  function totalHtml(p, c) {
    let s = 0; S.hoja.dias.forEach(f => { const q = S.hoja.cant.get(p.id + '|' + f + '|' + c.id); if (q) s += num(q.cantidad); });
    const imp = s ? importeVisible(c, p, s) : null;
    return `${s ? (c.unidad === 'importe' ? esc(dinero(s)) : esc(s)) : '—'}${imp != null && c.unidad !== 'importe' ? `<br><small>${esc(dinero(imp))}</small>` : ''}`;
  }
  function avisosHtml(p) { const av = avisos(p); return av.length ? `<span class="inc-aviso" title="${esc(av.join(' · '))}">⚠ ${av.length}</span>` : ''; }
  function sumaHtml(f, c) { let s = 0; S.hoja.personas.forEach(p => { const q = S.hoja.cant.get(p.id + '|' + f + '|' + c.id); if (q) s += num(q.cantidad); }); return s ? String(s) : ''; }
  // Actualiza solo totales, avisos y suma del día, sin redibujar la tabla (no se pierde lo que se está escribiendo).
  function refrescar(pid, fecha) {
    const H = S.hoja, p = H.personas.find(x => x.id === pid); if (!p) return;
    H.conceptos.forEach(c => { const td = document.querySelector(`td[data-tot="${pid}|${c.id}"]`); if (td) td.innerHTML = totalHtml(p, c); });
    const av = document.querySelector(`td[data-av="${pid}"]`); if (av) av.innerHTML = avisosHtml(p);
    const conc = H.conceptos.find(c => c.id === H.vista);
    const sm = document.querySelector(`td[data-sum="${fecha}"]`); if (sm && conc) sm.textContent = sumaHtml(fecha, conc);
  }
  function nombreProyecto(id) { const p = (S.hoja.proyectos || []).find(x => x.id === id); return p ? p.nombre : ''; }
  function marcar() { S.hoja.sucio = true; S.hoja.confirmarEnvio = false; const s = $('inc-sucio'); if (s) s.textContent = 'Cambios sin guardar'; }
  function cambiarCelda(el) {
    const H = S.hoja, campo = el.dataset.campo;
    if (campo === 'cantidad') {
      const k = el.dataset.k, v = el.value === '' ? '' : num(el.value);
      const [pid, f, cid] = k.split('|');
      if (v === '' || v === 0) { const q = H.cant.get(k); if (q) q.cantidad = 0; }
      else { const q = H.cant.get(k) || Object.assign({ personal_id: pid, fecha: f, concepto_id: cid }, (H.descPend || {})[pid] || {}); q.cantidad = v; H.cant.set(k, q); }
      marcar(); refrescar(pid, f); return;
    }
    const k = el.dataset.k, [pid, f] = k.split('|');
    const c = H.celdas.get(k) || { personal_id: pid, fecha: f };
    c[campo] = el.value || null; H.celdas.set(k, c);
    if (campo === 'codigo') el.parentElement.className = el.value ? 'inc-cod-' + el.value : '';
    marcar();
  }
  function aplicarDesc(pid, cambios) {
    const H = S.hoja, cid = H.vista;
    H.dias.forEach(f => { const q = H.cant.get(pid + '|' + f + '|' + cid); if (q) Object.assign(q, cambios); });
    H.descPend = H.descPend || {}; H.descPend[pid] = Object.assign(H.descPend[pid] || {}, cambios);
    marcar();
  }
  function salirHoja() {
    if (S.hoja && S.hoja.sucio && !window.confirm('Tienes cambios sin guardar. ¿Salir sin guardar?')) return;
    S.hoja = null; vistaMisHojas();
  }

  // Guarda solo las diferencias contra lo cargado. Las reglas (fechas,
  // asignación, duplicados, motivo del descuento) las valida la base.
  async function guardar() {
    const H = S.hoja; if (!editable()) return true;
    const ops = [];
    const descConc = new Set(H.conceptos.filter(c => c.tipo === 'descuento').map(c => c.id));
    for (const [k, c] of H.celdas) {
      const o = H.orig.celdas.get(k), vacio = !c.codigo && !c.proyecto_id && !c.centro_costo_id;
      if (c.id && vacio) ops.push(() => sb.from('inc_celdas').delete().eq('id', c.id));
      else if (c.id && (o.codigo !== c.codigo || o.proyecto_id !== c.proyecto_id)) ops.push(() => sb.from('inc_celdas').update({ codigo: c.codigo || null, proyecto_id: c.proyecto_id || null }).eq('id', c.id));
      else if (!c.id && !vacio) ops.push(() => sb.from('inc_celdas').insert({ hoja_id: H.id, personal_id: c.personal_id, fecha: c.fecha, codigo: c.codigo || null, proyecto_id: c.proyecto_id || null }));
    }
    for (const [k, q] of H.cant) {
      const o = H.orig.cant.get(k), cant = num(q.cantidad);
      const extraDesc = descConc.has(q.concepto_id) ? Object.assign({ motivo: q.motivo || null, conformidad_declarada: !!q.conformidad_declarada }, (H.descPend || {})[q.personal_id] || {}) : {};
      if (q.id && cant <= 0) ops.push(() => sb.from('inc_cantidades').delete().eq('id', q.id));
      else if (q.id && (num(o.cantidad) !== cant || (descConc.has(q.concepto_id) && (o.motivo !== extraDesc.motivo || !!o.conformidad_declarada !== extraDesc.conformidad_declarada))))
        ops.push(() => sb.from('inc_cantidades').update(Object.assign({ cantidad: cant }, extraDesc)).eq('id', q.id));
      else if (!q.id && cant > 0) ops.push(() => sb.from('inc_cantidades').insert(Object.assign({ hoja_id: H.id, personal_id: q.personal_id, fecha: q.fecha, concepto_id: q.concepto_id, cantidad: cant }, extraDesc)));
    }
    for (const [pid, o] of H.obs) {
      const ori = H.orig.obs.get(pid);
      if (o.id && !o.texto) ops.push(() => sb.from('inc_observaciones').delete().eq('id', o.id));
      else if (o.id && ori.texto !== o.texto) ops.push(() => sb.from('inc_observaciones').update({ texto: o.texto }).eq('id', o.id));
      else if (!o.id && o.texto) ops.push(() => sb.from('inc_observaciones').insert({ hoja_id: H.id, personal_id: pid, texto: o.texto }));
    }
    const errores = [];
    for (const op of ops) { const { error } = await op(); if (error) errores.push(error.code === '23505' ? 'Hay un registro repetido (misma persona, día y concepto).' : limpiarError(error)); }
    if (errores.length) { msg('inc-msg', 'err', 'No se guardó todo: ' + [...new Set(errores)].join(' · ')); return false; }
    H.sucio = false; return true;
  }
  async function enviar() {
    const H = S.hoja;
    if (!H.confirmarEnvio) { H.confirmarEnvio = true; pintarHoja(); return; }
    $('inc-enviar').disabled = true;
    const ok = await guardar(); if (!ok) { H.confirmarEnvio = false; return; }
    const { error } = await sb.rpc('inc_enviar_hoja', { p_hoja: H.id, p_observacion_general: (H.h.observacion_general || '').trim() || null });
    if (error) { H.confirmarEnvio = false; pintarHoja(); return msg('inc-msg', 'err', limpiarError(error)); }
    obsGralGuardar(H.id, null);
    await vistaHoja(H.id); msg('inc-msg', 'ok', 'Hoja enviada y cerrada. Nómina ya la puede revisar.');
  }

  // ---------- conexión con el menú ----------
  const btn = document.querySelector('nav.tabs button[data-tab="incidencias"]');
  if (btn) btn.addEventListener('click', () => { if (typeof pestanaPermitida !== 'function' || pestanaPermitida('incidencias')) abrir(); });
  window.beehumanIncidencias = { abrir };
})();
