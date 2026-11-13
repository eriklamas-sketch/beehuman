// =====================================================================
// BeeHuman · Ola 1 · Incidencias (hoja semanal del coordinador)
// Etapas 2 y 3: configuración (Administrador), periodos (Nómina y
// Administrador) y hoja del coordinador. B1 (fase 2): revisión de Nómina
// (tablero del periodo, hoja enviada, importes por esquema, devolución,
// firmas, sueldo manual y procesado). B1.1: valor por hora configurable
// (factor doble y umbral por empresa, horas sencillas, esquema preferido,
// esquema por asignar, motivo y bitácora de ajustes). Concentrado, comparativo y
// exportaciones son etapas posteriores (B3, B4').
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
#panel-incidencias .inc-chips{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}
#panel-incidencias .inc-chip{background:#F3F5FA;color:#45506A;border-radius:999px;padding:4px 11px;font-size:12px;font-weight:600}
#panel-incidencias .inc-chip.alerta{background:#FDECEA;color:#B42318}
#panel-incidencias .inc-chip.ok{background:#E8F4E5;color:#1F6B33}
#panel-incidencias .inc-estado.sin_abrir{background:#FFF4D6;color:#8A5A00}
#panel-incidencias .inc-mod{display:inline-block;border-radius:6px;padding:2px 7px;font-size:11px;font-weight:700;letter-spacing:.02em}
#panel-incidencias .inc-mod.bruto{background:#EAF0FC;color:#22489E}
#panel-incidencias .inc-mod.neto{background:#E8F4E5;color:#1F6B33}
#panel-incidencias .inc-mod.manual{background:#FFF4D6;color:#8A5A00}
#panel-incidencias .inc-mod.tarifa{background:#F1F2F4;color:#4B5565}
#panel-incidencias .inc-dec{display:inline-block;border-radius:999px;padding:2px 9px;font-size:11px;font-weight:600;white-space:nowrap}
#panel-incidencias .inc-dec.pendiente{background:#FFF4D6;color:#8A5A00}
#panel-incidencias .inc-dec.aceptado{background:#E8F4E5;color:#1F6B33}
#panel-incidencias .inc-dec.modificado{background:#EAF0FC;color:#22489E}
#panel-incidencias .inc-dec.sin_sueldo{background:#B42318;color:#fff}
#panel-incidencias .inc-dec.sin_importe,#panel-incidencias .inc-dec.descartado{background:#F1F2F4;color:#6B7385}
#panel-incidencias .inc-dec.por_asignar{background:#8A5A00;color:#fff}
#panel-incidencias .inc-imp tr.inc-por-asignar td{background:#FFFAEB}
#panel-incidencias .inc-imp select.inc-esq{margin:4px 0 0;padding:4px 6px;font-size:12px;max-width:220px}
#panel-incidencias .inc-imp input.inc-motivo-aj{width:110px;margin:4px 0 0;padding:4px 6px;font-size:12px;border:1px solid var(--v21-borde,#E5E9F1);border-radius:7px}
#panel-incidencias .inc-calc{font-size:12px;color:#45506A;min-width:120px}
#panel-incidencias .inc-imp td{text-align:left;padding:7px 8px;font-size:13px;border-top:1px solid #EDF0F6;vertical-align:middle}
#panel-incidencias .inc-imp td.n{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
#panel-incidencias .inc-imp th{text-align:left;font-size:12px;color:#45506A;background:#F3F5FA;padding:7px 8px;white-space:nowrap}
#panel-incidencias .inc-imp th.n{text-align:right}
#panel-incidencias .inc-imp tr.inc-persona td{background:#FAFBFD;font-weight:700;color:var(--v21-texto,#1C2840);border-top:2px solid #E5E9F1}
#panel-incidencias .inc-imp tr.inc-sin-sueldo td{background:#FFF6F5}
#panel-incidencias .inc-imp tr.inc-descartada td{color:#9AA1B0;text-decoration:line-through}
#panel-incidencias .inc-imp input.inc-final{width:110px;margin:0;padding:5px 6px;text-align:right;border:1px solid var(--v21-borde,#E5E9F1);border-radius:7px}
#panel-incidencias .inc-imp input.inc-manual{width:100px;margin:0 6px 0 0;padding:5px 6px;text-align:right;border:1px solid #F2C6C0;border-radius:7px}
#panel-incidencias .inc-imp button{margin:0 4px 0 0;padding:5px 10px;font-size:12px}
#panel-incidencias .inc-motivo{display:block;font-size:12px;color:#B42318;margin-top:3px}
#panel-incidencias .inc-subtot{font-size:12px;color:#45506A;font-weight:600}
#panel-incidencias .inc-subtot span{margin-right:12px;white-space:nowrap}
#panel-incidencias .inc-panel{border:1px solid var(--v21-borde,#E5E9F1);border-radius:12px;padding:12px 14px;margin:12px 0;background:#FBFCFE}
#panel-incidencias .inc-volver{background:none;border:0;color:var(--v21-navy,#16264A);font:600 13px Inter,sans-serif;cursor:pointer;padding:0;margin:0 0 8px}
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
  // Fechas completas siempre en DD/MM/AAAA (decisión de Erik, 9-nov): sin nombres de mes ambiguos.
  const fechaLarga = s => { const d = fechaUTC(s); return `${String(d.getUTCDate()).padStart(2, '0')}/${String(d.getUTCMonth() + 1).padStart(2, '0')}/${d.getUTCFullYear()}`; };
  const sumar = (s, n) => { const d = fechaUTC(s); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
  const rango = (a, b) => { const r = []; for (let f = a; f <= b; f = sumar(f, 1)) r.push(f); return r; };
  const semana = s => { const d = fechaUTC(s); const w = (d.getUTCDay() + 6) % 7; return sumar(s, -w); };
  const dinero = n => Number(n || 0).toLocaleString('es-MX', { style: 'currency', currency: 'MXN' });
  const num = v => { const n = Number(String(v).replace(',', '.')); return isFinite(n) ? n : 0; };
  const limpiarError = e => String((e && (e.message || e.details)) || e || 'Error desconocido').replace(/^BeeHuman:\s*/, '');
  const nombreEmpresa = id => { const e = (typeof empresas !== 'undefined' ? empresas : []).find(x => x.id === id); return e ? e.nombre : ''; };
  const conEmpresa = id => { const n = nombreEmpresa(id); return n ? n + ' · ' : ''; };
  function msg(id, tipo, texto) { const el = $(id); if (!el) return; el.className = 'inc-msg ' + tipo; el.textContent = texto; }

  const S = { vista: null, usuarioId: null, tenantId: null, cfg: { empresaId: null }, hoja: null, obsGral: {}, rev: {} };
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
    const vistas = rolActual === 'administrador' ? [['revision', 'Revisión'], ['periodos', 'Periodos'], ['config', 'Configuración']]
      : rolActual === 'nomina' ? [['revision', 'Revisión'], ['periodos', 'Periodos'], ['config', 'Configuración']]
      : rolActual === 'coordinador' ? [['hojas', 'Mis hojas']] : [];
    if (!vistas.length) { raiz.innerHTML = '<div class="card"><p class="hint">Esta sección no está disponible para tu rol.</p></div>'; return; }
    if (!S.vista || !vistas.some(v => v[0] === S.vista)) S.vista = vistas[0][0];
    raiz.innerHTML = (vistas.length > 1 ? `<div class="inc-sub">${vistas.map(([k, n]) => `<button type="button" data-inc-vista="${k}" class="${k === S.vista ? 'activo' : ''}">${n}</button>`).join('')}</div>` : '')
      + '<div id="inc-vista"></div>';
    raiz.querySelectorAll('[data-inc-vista]').forEach(b => b.addEventListener('click', () => { S.vista = b.dataset.incVista; S.hoja = null; S.rev = {}; abrir(); }));
    if (S.vista === 'revision') return vistaRevision();
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
      <p class="inc-nota">Para revisar las hojas enviadas, decidir importes, firmar y marcar el periodo como procesado, usa «Revisión».</p>
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
  const TIPOS = [['horas_extra', 'Horas extra (dobles y triples)'], ['horas', 'Horas sencillas'], ['domingo', 'Domingo trabajado'], ['turno', 'Turno'], ['descuento', 'Descuento operativo'], ['otro', 'Otro']];
  const UNIDADES = [['horas', 'Horas'], ['turnos', 'Turnos'], ['dias', 'Días'], ['importe', 'Importe']];
  const MODOS = [['beehuman', 'Calcula BeeHuman'], ['tarifa', 'Tarifa propia'], ['sin_importe', 'Sin importe']];
  const PLANTILLAS = {
    he: { nombre: 'Horas extra', abreviatura: 'HE', tipo: 'horas_extra', unidad: 'horas', modo: 'beehuman' },
    dom: { nombre: 'Domingo trabajado', abreviatura: 'DOM', tipo: 'domingo', unidad: 'dias', modo: 'beehuman' },
    tn: { nombre: 'Turno nocturno', abreviatura: 'T', tipo: 'turno', unidad: 'turnos', modo: 'tarifa', tarifa: 700 },
    desc: { nombre: 'Descuento operativo', abreviatura: 'DESC', tipo: 'descuento', unidad: 'importe', modo: 'tarifa', tarifa: 1 }
  };
  const opciones = (lista, v) => lista.map(([k, n]) => `<option value="${k}" ${k === v ? 'selected' : ''}>${n}</option>`).join('');

  const nombreClasif = id => { const c = (S.cfg.clasificaciones || []).find(x => x.id === id); return c ? c.nombre : 'Clasificación'; };
  function valorConcepto(c) {
    if (c.tipo === 'descuento') return 'Importe capturado';
    if (c.modo === 'sin_importe') return 'Sin importe';
    const area = S.cfg.tarifas.some(t => t.concepto_id === c.id) ? ' + por área' : '';
    if (c.tarifa != null && (c.modo === 'tarifa' || c.tipo === 'domingo')) return dinero(c.tarifa) + (c.unidad === 'horas' ? ' por hora' : '') + area + (c.tipo === 'horas_extra' ? ' × dobles / triples' : '');
    if (c.tipo === 'horas_extra') return 'Sueldo ÷ jornada × dobles / triples';
    if (c.tipo === 'horas' || c.unidad === 'horas') return 'Sueldo ÷ jornada' + (c.factor != null && Number(c.factor) !== 1 ? ' × ' + c.factor : '');
    if (c.tipo === 'domingo') return 'Prima dominical';
    return c.factor != null ? 'Sueldo diario × ' + c.factor : 'Sueldo diario';
  }

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
    const [prm, con, are, cls] = await Promise.all([
      sb.from('inc_parametros').select('*').eq('empresa_id', emp).maybeSingle(),
      sb.from('inc_conceptos').select('*').eq('empresa_id', emp).order('orden').order('nombre'),
      sb.from('areas').select('id, nombre').order('nombre'),
      sb.from('clasificaciones_personal').select('id, nombre').order('nombre')
    ]);
    const err = prm.error || con.error;
    if (err) { $('inc-c-cuerpo').innerHTML = `<div class="inc-msg err" style="display:block">${esc(limpiarError(err))}</div>`; return; }
    S.cfg.prm = prm.data; S.cfg.conceptos = con.data || []; S.cfg.areas = are.data || []; S.cfg.clasificaciones = cls.data || [];
    const ids = S.cfg.conceptos.map(c => c.id);
    const ta = ids.length ? await sb.from('inc_tarifas_area').select('*').in('concepto_id', ids) : { data: [] };
    S.cfg.tarifas = ta.data || [];
    pintarConfig();
  }
  function pintarConfig() {
    const p = S.cfg.prm || { base_calculo: 'mixto', jornada_horas: 8, umbral_triples_semana: 9, factor_doble: 2, factor_triple: 3, aviso_horas_dia: 3, aviso_dias_semana: 3, prima_dominical_pct: 25 };
    const resp = (uid) => !uid ? 'Sin designar' : (uid === S.usuarioId ? 'Tú' : 'Otro usuario');
    const ed = S.cfg.editando || {};
    const soloLectura = rolActual !== 'administrador';
    $('inc-c-cuerpo').innerHTML = `
      <h3 style="margin:18px 0 4px">Parámetros de cálculo</h3>
      <div class="inc-fila">
        <div><label for="inc-c-base">Base de cálculo</label><select id="inc-c-base">${opciones([['mixto', 'Mixto (todos los esquemas)'], ['bruto', 'Solo bruto'], ['neto', 'Solo neto']], p.base_calculo)}</select></div>
        <div><label for="inc-c-jor">Horas de la jornada</label><input id="inc-c-jor" type="number" step="0.5" min="1" value="${esc(p.jornada_horas)}"></div>
        <div><label for="inc-c-umb">Horas dobles por semana antes de triples</label><input id="inc-c-umb" type="number" step="0.5" min="0" placeholder="Vacío = sin triples" value="${esc(p.umbral_triples_semana ?? '')}"></div>
        <div><label for="inc-c-fdo">Factor de horas dobles</label><input id="inc-c-fdo" type="number" step="0.1" min="0" value="${esc(p.factor_doble ?? 2)}"></div>
        <div><label for="inc-c-ftr">Factor de horas triples</label><input id="inc-c-ftr" type="number" step="0.1" min="0" value="${esc(p.factor_triple)}"></div>
        <div><label for="inc-c-avh">Aviso: horas extra por día</label><input id="inc-c-avh" type="number" step="0.5" min="0" value="${esc(p.aviso_horas_dia)}"></div>
        <div><label for="inc-c-avd">Aviso: días con horas extra por semana</label><input id="inc-c-avd" type="number" step="1" min="0" value="${esc(p.aviso_dias_semana)}"></div>
        <div><label for="inc-c-pdm">Prima dominical (%)</label><input id="inc-c-pdm" type="number" step="0.5" min="0" value="${esc(p.prima_dominical_pct)}"></div>
      </div>
      <p class="inc-nota">Valor por hora = tarifa del concepto, o sueldo diario del esquema ÷ horas de la jornada. Horas extra: × factor de dobles hasta el umbral de la semana (lunes a domingo, sumando todos los días); después × factor de triples. Umbral vacío: todas dobles.</p>
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
      ${S.cfg.conceptos.length ? `<div class="inc-tabla-wrap" style="max-height:none"><table class="inc-lista"><thead><tr><th>Columna</th><th>Concepto</th><th>Unidad</th><th>Cálculo</th><th>Valor</th><th>Esquema preferido</th><th>Estado</th><th></th></tr></thead><tbody>
        ${S.cfg.conceptos.map(c => `<tr><td><b>${esc(c.abreviatura)}</b></td><td>${esc(c.nombre)}</td><td>${esc((UNIDADES.find(u => u[0] === c.unidad) || [, c.unidad])[1])}</td>
          <td>${esc((MODOS.find(m => m[0] === c.modo) || [, c.modo])[1])}</td>
          <td>${esc(valorConcepto(c))}</td>
          <td>${c.modo === 'tarifa' && c.tipo !== 'descuento' ? esc(c.clasificacion_pago_id ? nombreClasif(c.clasificacion_pago_id) : 'Sin preferido') : '—'}</td>
          <td>${c.activo ? '<span class="inc-estado enviada">Activo</span>' : '<span class="inc-estado borrador">Inactivo</span>'}</td>
          <td>${soloLectura ? '' : `<button type="button" class="inc-sec" data-inc-editar="${esc(c.id)}">Editar</button>`}</td></tr>`).join('')}</tbody></table></div>`
        : '<p class="hint">Sin conceptos todavía. Usa «Agregar rápido» o el formulario.</p>'}
      <div id="inc-c-form" ${soloLectura ? 'hidden' : ''}>
      <h3 style="margin:18px 0 4px" id="inc-c-form-titulo">${ed.id ? 'Editar concepto' : 'Nuevo concepto'}</h3>
      <div class="inc-fila">
        <div><label for="inc-k-nom">Nombre</label><input id="inc-k-nom" maxlength="60" value="${esc(ed.nombre || '')}"></div>
        <div><label for="inc-k-abr">Abreviatura (columna)</label><input id="inc-k-abr" maxlength="6" value="${esc(ed.abreviatura || '')}"></div>
        <div><label for="inc-k-tipo">Tipo</label><select id="inc-k-tipo">${opciones(TIPOS, ed.tipo || 'horas_extra')}</select></div>
        <div><label for="inc-k-uni">Unidad</label><select id="inc-k-uni">${opciones(UNIDADES, ed.unidad || 'horas')}</select></div>
        <div><label for="inc-k-modo">Cálculo</label><select id="inc-k-modo">${opciones(MODOS, ed.modo || 'beehuman')}</select></div>
        <div><label for="inc-k-tar">Tarifa por unidad (opcional)</label><input id="inc-k-tar" type="number" step="0.01" min="0" value="${esc(ed.tarifa ?? '')}"></div>
        <div><label for="inc-k-fac">Factor (turnos y otros)</label><input id="inc-k-fac" type="number" step="0.01" min="0" value="${esc(ed.factor ?? '')}"></div>
        <div id="inc-k-cls-caja"><label for="inc-k-cls">Esquema preferido (tarifa)</label><select id="inc-k-cls"><option value="">Sin preferido</option>${(S.cfg.clasificaciones || []).map(x => `<option value="${esc(x.id)}" ${x.id === ed.clasificacion_pago_id ? 'selected' : ''}>${esc(x.nombre)}</option>`).join('')}</select></div>
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
        <div class="inc-msg" id="inc-c-msg-tar"></div>` : ''}
      </div>`;
    if (soloLectura) {
      $('inc-c-cuerpo').querySelectorAll('input, select, textarea, button').forEach(el => { el.disabled = true; });
      $('inc-c-cuerpo').querySelectorAll('#inc-c-guardar-prm, [data-inc-resp], [data-inc-plantilla]').forEach(el => { el.hidden = true; });
      $('inc-c-cuerpo').insertAdjacentHTML('afterbegin', '<div class="inc-msg info" style="display:block" id="inc-c-solo-lectura">Solo lectura: la configuración de cálculo la cambia el Administrador.</div>');
      return;
    }
    const ayuda = () => {
      const t = $('inc-k-tipo').value, m = $('inc-k-modo').value;
      const textos = {
        horas_extra: m === 'tarifa' ? 'Tarifa por hora × factor de dobles hasta el umbral semanal de la empresa; después × factor de triples.' : m === 'sin_importe' ? 'Solo horas, sin importe.' : 'Valor por hora = sueldo diario del esquema ÷ horas de jornada; × factor de dobles hasta el umbral semanal, después × factor de triples.',
        horas: m === 'tarifa' ? 'Horas × tarifa (sin dobles ni triples).' : m === 'sin_importe' ? 'Solo horas, sin importe.' : 'Horas × sueldo diario del esquema ÷ horas de jornada (sin dobles ni triples).',
        domingo: 'Si tiene tarifa (general o por área) esa es el pago completo; si no, se calcula la prima dominical sobre el sueldo diario.',
        turno: m === 'tarifa' ? 'Tarifa fija por turno.' : 'Calcula BeeHuman: sueldo diario × factor (por ejemplo 0.25 = 25 % de prima).',
        descuento: 'Importe capturado por el coordinador con motivo y conformidad; Nómina decide si se aplica.',
        otro: m === 'tarifa' ? 'Cantidad × tarifa.' : m === 'sin_importe' ? 'Solo cantidades, sin importe.' : 'Calcula BeeHuman: cantidad × sueldo diario × factor.'
      };
      $('inc-k-ayuda').textContent = (textos[t] || '') + (m === 'tarifa' && t !== 'descuento' ? ' El importe se liga al esquema preferido si la persona tiene exactamente uno vigente; sin preferido, si tiene un solo esquema. Si no, Nómina lo asigna en la revisión.' : '');
      $('inc-k-cls-caja').hidden = !(m === 'tarifa' && t !== 'descuento');
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
      base_calculo: $('inc-c-base').value, jornada_horas: num($('inc-c-jor').value),
      umbral_triples_semana: $('inc-c-umb').value.trim() === '' ? null : num($('inc-c-umb').value),
      factor_doble: num($('inc-c-fdo').value), factor_triple: num($('inc-c-ftr').value), aviso_horas_dia: num($('inc-c-avh').value), aviso_dias_semana: Math.round(num($('inc-c-avd').value)),
      prima_dominical_pct: num($('inc-c-pdm').value), actualizado_por: S.usuarioId, actualizado_en: new Date().toISOString()
    };
    if (v.jornada_horas <= 0) return msg('inc-c-msg-prm', 'err', 'Las horas de la jornada deben ser mayores a cero.');
    if (!(v.factor_doble > 0) || !(v.factor_triple > 0)) return msg('inc-c-msg-prm', 'err', 'Los factores de dobles y triples deben ser mayores a cero.');
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
      tarifa: $('inc-k-tar').value === '' ? null : num($('inc-k-tar').value), factor: $('inc-k-fac').value === '' ? null : num($('inc-k-fac').value),
      clasificacion_pago_id: null
    };
    if (v.modo === 'tarifa' && v.tipo !== 'descuento') v.clasificacion_pago_id = $('inc-k-cls').value || null;
    if (!v.nombre || !v.abreviatura) return msg('inc-c-msg-con', 'err', 'Nombre y abreviatura son obligatorios.');
    if (v.modo === 'tarifa' && v.tarifa == null) return msg('inc-c-msg-con', 'err', 'El cálculo «Tarifa propia» necesita una tarifa.');
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
    if (c.tipo === 'horas_extra') return null;   // B1.1: dobles y triples se calculan en el servidor
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
        : conc ? `<span>Captura ${esc(conc.unidad === 'importe' ? 'el importe' : 'la cantidad de ' + conc.unidad)} por día.${(conc.modo === 'beehuman' && !(conc.tipo === 'domingo' && conc.tarifa != null)) || (conc.tipo === 'horas_extra' && conc.modo !== 'sin_importe') ? ' El importe lo calcula Nómina.' : ''}</span>` : ''}</div>
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

  // =====================================================================
  // B1 · Revisión de Nómina (Nómina y Administrador)
  // Toda decisión pasa por funciones del servidor; la pantalla no calcula
  // importes: solo suma, por separado, lo que el servidor ya calculó.
  // =====================================================================
  const ESTADO_TAB = { sin_abrir: 'Sin abrir', borrador: 'En captura', enviada: 'Enviada', devuelta: 'Devuelta', procesada: 'Procesada' };
  const MODALIDAD = { bruto: 'Bruto', neto: 'Neto', manual: 'Sueldo manual' };
  const DECISION = { pendiente: 'Por decidir', aceptado: 'Aceptado', modificado: 'Modificado', sin_sueldo: 'Sin sueldo', sin_importe: 'Sin importe', descartado: 'Descartado', por_asignar: 'Esquema por asignar' };
  const CATEGORIAS = [['bruto', 'Bruto'], ['neto', 'Neto'], ['manual', 'Sueldo manual'], ['tarifa', 'Sin esquema asignado'], ['descuento', 'Descuentos']];
  const errHtml = e => `<div class="inc-msg err" style="display:block">${esc(limpiarError(e))}</div>`;
  const fechaHora = ts => { try { return new Date(ts).toLocaleString('es-MX', { timeZone: 'America/Mexico_City', day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }); } catch (e) { return String(ts).slice(0, 16); } };
  const plural = (n, s, p) => `${n} ${n === 1 ? s : (p || s + 's')}`;

  async function vistaRevision() {
    if (S.rev.hojaId) return revHoja();
    if (S.rev.periodoId) return revPeriodo();
    return revPeriodos();
  }

  // ---------- 1. Periodos ----------
  async function revPeriodos() {
    const cont = $('inc-vista');
    cont.innerHTML = `<div class="card"><h2>Revisión de incidencias</h2>
      <p class="hint">Elige un periodo para ver quién ya envió su hoja, revisar la captura y decidir los importes.</p>
      <div id="inc-r-lista"><p class="hint">Cargando…</p></div></div>`;
    const [per, hj] = await Promise.all([
      sb.from('inc_periodos').select('id, empresa_id, inicio, fin, procesado_en').order('inicio', { ascending: false }).limit(60),
      sb.from('inc_hojas').select('periodo_id, estado, tipo')
    ]);
    const el = $('inc-r-lista'); if (!el) return;
    if (per.error || hj.error) { el.innerHTML = errHtml(per.error || hj.error); return; }
    if (!per.data.length) { el.innerHTML = '<p class="hint">Todavía no hay periodos. Créalos en «Periodos».</p>'; return; }
    const cuenta = new Map();
    (hj.data || []).filter(h => h.tipo === 'normal').forEach(h => {
      const a = cuenta.get(h.periodo_id) || { env: 0, dev: 0 };
      if (['enviada', 'procesada'].includes(h.estado)) a.env++;
      if (h.estado === 'devuelta') a.dev++;
      cuenta.set(h.periodo_id, a);
    });
    el.innerHTML = `<table class="inc-lista" id="inc-r-periodos"><thead><tr><th>Empresa</th><th>Periodo</th><th>Hojas</th><th>Estado</th><th></th></tr></thead><tbody>${per.data.map(p => {
      const a = cuenta.get(p.id) || { env: 0, dev: 0 };
      return `<tr><td>${esc(nombreEmpresa(p.empresa_id))}</td><td>${esc(fechaLarga(p.inicio))} – ${esc(fechaLarga(p.fin))}</td>
        <td>${plural(a.env, 'enviada')}${a.dev ? ` <span class="inc-chip alerta">${plural(a.dev, 'devuelta')}</span>` : ''}</td>
        <td>${p.procesado_en ? '<span class="inc-estado procesada">Procesado</span>' : '<span class="inc-estado borrador">Abierto</span>'}</td>
        <td><button type="button" class="inc-sec" data-rev-per="${esc(p.id)}">Revisar</button></td></tr>`;
    }).join('')}</tbody></table>`;
    el.querySelectorAll('[data-rev-per]').forEach(b => b.addEventListener('click', () => { S.rev = { periodoId: b.dataset.revPer }; vistaRevision(); }));
  }

  // ---------- 2. Tablero del periodo ----------
  async function revPeriodo() {
    const cont = $('inc-vista');
    cont.innerHTML = '<div class="card"><p class="hint">Cargando el periodo…</p></div>';
    // B5: primero se sincronizan los descuentos de créditos del periodo, para
    // que la lista de faltantes los incluya. Sin el módulo, se ignora.
    const cred = window.credPanelPeriodo ? await sb.rpc('cred_descuentos_periodo', { p_periodo: S.rev.periodoId }) : null;
    const [pe, tb, fl] = await Promise.all([
      sb.from('inc_periodos').select('*').eq('id', S.rev.periodoId).single(),
      sb.rpc('inc_tablero_periodo', { p_periodo: S.rev.periodoId }),
      sb.rpc('inc_faltantes_procesar', { p_periodo: S.rev.periodoId })
    ]);
    if (pe.error || tb.error) { cont.innerHTML = `<div class="card">${errHtml(pe.error || tb.error)}</div>`; return; }
    const p = pe.data, filas = tb.data || [];
    const faltan = p.procesado_en ? [] : (fl.error ? [{ tipo: 'error', detalle: limpiarError(fl.error) }] : (fl.data || []));
    const env = filas.filter(f => ['enviada', 'procesada'].includes(f.estado)).length;
    const sinEnviar = filas.filter(f => ['sin_abrir', 'borrador'].includes(f.estado));
    const dev = filas.filter(f => f.estado === 'devuelta');
    cont.innerHTML = `<div class="card">
      <button type="button" class="inc-volver" id="inc-r-volver">← Periodos</button>
      <div class="inc-cab"><div><h2>${esc(nombreEmpresa(p.empresa_id))} · ${esc(fechaLarga(p.inicio))} – ${esc(fechaLarga(p.fin))}</h2>
        <p class="hint">Una fila por coordinador con personal de esta empresa (relación laboral vigente) en el periodo.</p></div>
        <div>${p.procesado_en ? '<span class="inc-estado procesada">Procesado</span>' : '<span class="inc-estado borrador">Abierto</span>'}</div></div>
      <div class="inc-chips" id="inc-r-resumen">
        <span class="inc-chip ${filas.length && env === filas.length ? 'ok' : ''}">${env} de ${plural(filas.length, 'hoja')} enviadas</span>
        ${sinEnviar.length ? `<span class="inc-chip alerta" id="inc-r-faltan">Falta${sinEnviar.length === 1 ? '' : 'n'} por enviar: ${esc(sinEnviar.map(f => f.coordinador).join(', '))}</span>` : ''}
        ${dev.length ? `<span class="inc-chip alerta">${plural(dev.length, 'devuelta')} sin reenviar</span>` : ''}
      </div>
      ${filas.length ? `<div class="inc-tabla-wrap" style="max-height:none"><table class="inc-lista" id="inc-r-tablero"><thead><tr><th>Coordinador</th><th>Personas</th><th>Hoja</th><th>Firmas (versión vigente)</th><th>Complementos</th><th></th></tr></thead><tbody>${filas.map(f => `<tr data-coord="${esc(f.coordinador_id)}" data-estado="${esc(f.estado)}">
        <td><b>${esc(f.coordinador)}</b>${f.estado === 'devuelta' && f.ultimo_motivo ? `<span class="inc-motivo">Devuelta: ${esc(f.ultimo_motivo)}</span>` : ''}</td>
        <td>${f.personas}</td>
        <td><span class="inc-estado ${esc(f.estado)}">${esc(ESTADO_TAB[f.estado] || f.estado)}</span>${f.version_actual ? ` <span class="inc-nota">v${f.version_actual}${f.enviada_en ? ' · ' + esc(fechaHora(f.enviada_en)) : ''}</span>` : ''}</td>
        <td>${f.version_actual ? `${f.firma_nomina ? '✓' : '—'} Nómina · ${f.firma_rh ? '✓' : '—'} RH` : '—'}</td>
        <td>${f.complementos || '—'}</td>
        <td>${f.version_actual ? `<button type="button" class="inc-sec" data-rev-hoja="${esc(f.hoja_id)}">Revisar</button>` : ''}</td></tr>`).join('')}</tbody></table></div>`
        : '<p class="hint">Ningún coordinador tiene personal con relación laboral en esta empresa durante el periodo.</p>'}
      <div id="inc-r-cred">${cred && cred.error ? `<div class="inc-msg err" style="display:block">Descuentos de créditos: ${esc(limpiarError(cred.error))}</div>` : ''}</div>
      <div class="inc-msg" id="inc-r-msg"></div>
      ${p.procesado_en ? `<p class="inc-nota">Procesado el ${esc(fechaHora(p.procesado_en))}. Lo que llegue después entra como complemento.</p>`
        : `<div class="inc-panel" id="inc-r-proc-panel"><b>Marcar el periodo como procesado</b>
        <p class="hint">Solo se procesa una prenómina completa: todas las hojas enviadas, todos los importes y descuentos aceptados o modificados y las firmas requeridas.</p>
        ${faltan.length ? `<div class="inc-msg err" style="display:block" id="inc-r-faltantes"><b>Falta${faltan.length === 1 ? '' : 'n'} ${faltan.length} pendiente${faltan.length === 1 ? '' : 's'} para procesar:</b><ul style="margin:6px 0 0 18px;padding:0">${faltan.map(f => `<li data-tipo="${esc(f.tipo)}">${esc(f.detalle)}</li>`).join('')}</ul></div>`
          : '<div class="inc-msg ok" style="display:block" id="inc-r-faltantes">Todo está completo: hojas enviadas, importes decididos y firmas registradas.</div>'}
        <div class="inc-acciones"><button type="button" class="primary" id="inc-r-proc" ${faltan.length ? 'disabled' : ''}>Marcar como procesado</button></div></div>`}
    </div>`;
    $('inc-r-volver').addEventListener('click', () => { S.rev = {}; vistaRevision(); });
    if (cred && cred.data && window.credPanelPeriodo) window.credPanelPeriodo($('inc-r-cred'), Object.assign({ periodo_id: p.id }, cred.data), revPeriodo);
    cont.querySelectorAll('[data-rev-hoja]').forEach(b => b.addEventListener('click', () => { S.rev = { periodoId: p.id, hojaId: b.dataset.revHoja }; vistaRevision(); }));
    const bp = $('inc-r-proc');
    if (bp) bp.addEventListener('click', async () => {
      bp.disabled = true;
      const { data, error } = await sb.rpc('inc_marcar_procesado', { p_periodo: p.id });
      if (error) { await revPeriodo(); return msg('inc-r-msg', 'err', limpiarError(error)); }
      await revPeriodo(); msg('inc-r-msg', 'ok', data || 'Periodo marcado como procesado.');
    });
  }

  // ---------- 3. Hoja enviada: captura e importes ----------
  async function revHoja() {
    const cont = $('inc-vista');
    cont.innerHTML = '<div class="card"><p class="hint">Cargando la hoja…</p></div>';
    const hojaId = S.rev.hojaId;
    const { data: h, error: e1 } = await sb.from('inc_hojas').select('*').eq('id', hojaId).maybeSingle();
    if (e1 || !h) { cont.innerHTML = `<div class="card">${errHtml(e1 || 'No se encontró la hoja.')}</div>`; return; }
    const [pe, ver, ev, comps, coord] = await Promise.all([
      sb.from('inc_periodos').select('*').eq('id', h.periodo_id).single(),
      sb.from('inc_versiones').select('*').eq('hoja_id', hojaId).eq('numero', h.version_actual).maybeSingle(),
      sb.from('inc_eventos').select('*').eq('hoja_id', hojaId).order('creado_en', { ascending: false }),
      sb.from('inc_hojas').select('id, tipo, estado, version_actual, creado_en').eq('hoja_raiz_id', h.hoja_raiz_id).order('creado_en'),
      sb.from('personal').select('id, nombre_completo').eq('id', h.coordinador_id).maybeSingle()
    ]);
    const err = pe.error || ver.error || ev.error || comps.error;
    if (err || !ver.data) { cont.innerHTML = `<div class="card">${errHtml(err || 'Esta hoja todavía no tiene una versión enviada.')}</div>`; return; }
    const periodo = pe.data, version = ver.data, datos = version.datos || {};
    const [imp, prm, man] = await Promise.all([
      sb.from('inc_importes').select('*').eq('version_id', version.id),
      sb.from('inc_parametros').select('responsable_nomina_user, responsable_rh_user, base_calculo').eq('empresa_id', periodo.empresa_id).maybeSingle(),
      sb.from('inc_sueldos_manuales').select('personal_id, sueldo_diario').eq('periodo_id', periodo.id)
    ]);
    if (imp.error) { cont.innerHTML = `<div class="card">${errHtml(imp.error)}</div>`; return; }
    const lineas = imp.data || [];
    const uniq = a => [...new Set(a.filter(Boolean))];
    const lineaIds = lineas.map(l => l.id);
    const conOpciones = lineas.some(l => l.origen === 'por_asignar' || (l.esquema_asignado_por && ['pendiente', 'aceptado'].includes(l.origen)));
    const [aj, asg] = await Promise.all([
      lineaIds.length ? sb.from('inc_importes_ajustes').select('*').in('importe_id', lineaIds).order('creado_en') : { data: [] },
      conOpciones && h.estado === 'enviada' ? sb.rpc('inc_esquemas_asignables', { p_version: version.id }) : { data: [] }
    ]);
    const ajustes = aj.data || [];
    const rpIds = uniq([...lineas.map(l => l.registro_pago_id), ...ajustes.map(a => a.esquema_anterior), ...ajustes.map(a => a.esquema_nuevo)]);
    const relIds = uniq(lineas.map(l => l.relacion_laboral_id));
    const pIds = uniq([...(datos.cantidades || []).map(q => q.personal_id), ...(datos.celdas || []).map(c => c.personal_id), ...(datos.observaciones || []).map(o => o.personal_id), ...lineas.map(l => l.personal_id)]);
    const [rps, rels, pers] = await Promise.all([
      rpIds.length ? sb.from('personal_registros_pago').select('id, clasificacion_id').in('id', rpIds) : { data: [] },
      relIds.length ? sb.from('relaciones_laborales').select('id, registro_patronal_id').in('id', relIds) : { data: [] },
      pIds.length ? sb.from('personal').select('id, nombre_completo, empleado_id').in('id', pIds) : { data: [] }
    ]);
    const clIds = uniq((rps.data || []).map(r => r.clasificacion_id)), patIds = uniq((rels.data || []).map(r => r.registro_patronal_id));
    const [cls, pats] = await Promise.all([
      clIds.length ? sb.from('clasificaciones_personal').select('id, nombre').in('id', clIds) : { data: [] },
      patIds.length ? sb.from('empresas_registros_patronales').select('id, registro_patronal').in('id', patIds) : { data: [] }
    ]);
    const porId = arr => new Map((arr || []).map(x => [x.id, x]));
    S.rev.H = {
      h, periodo, version, datos, lineas, eventos: ev.data || [], comps: comps.data || [], coord: coord.data,
      ajustes, opciones: (asg.data || []).reduce((m, o) => { (m[o.linea_id] = m[o.linea_id] || []).push(o); return m; }, {}),
      prm: prm.data || {}, manuales: new Map((man.data || []).map(m => [m.personal_id, m.sueldo_diario])),
      rps: porId(rps.data), rels: porId(rels.data), personas: porId(pers.data), cls: porId(cls.data), pats: porId(pats.data),
      conceptos: porId(datos.conceptos), verDescartadas: S.rev.H && S.rev.H.h.id === h.id ? S.rev.H.verDescartadas : false, devolviendo: false
    };
    pintarRevHoja();
  }

  function categoria(l, H) {
    if (l.modalidad) return l.modalidad;
    const c = H.conceptos.get(l.concepto_id);
    if (c && c.tipo === 'descuento') return 'descuento';
    return l.usa_sueldo ? null : 'tarifa';
  }
  const importeDe = l => (['descartado', 'sin_importe', 'sin_sueldo'].includes(l.origen) && l.final == null) ? null : (l.final != null ? Number(l.final) : (l.sugerido != null ? Number(l.sugerido) : null));
  function sumarPorCategoria(lineas, H) {
    const t = {}; CATEGORIAS.forEach(([k]) => { t[k] = 0; });
    lineas.forEach(l => { const k = categoria(l, H), v = importeDe(l); if (k && v != null) t[k] += v; });
    return t;
  }
  const fmtN = n => String(Math.round(Number(n) * 100) / 100);
  function valorHoraHtml(l) {
    const d = l.detalle || {};
    if (d.valor_hora == null) return (d.horas_dobles != null || d.regla === 'horas_sueldo') && l.usa_sueldo && l.origen !== 'sin_sueldo' ? '<span class="inc-nota">Varía por fecha</span>' : '—';
    const o = d.origen_valor === 'tarifa' ? 'tarifa' : d.origen_valor === 'manual' ? 'sueldo manual' : 'sueldo' + (d.clasificacion ? ' de ' + d.clasificacion : '') + (d.jornada_horas ? ' ÷ ' + fmtN(d.jornada_horas) + ' h' : '');
    return `${esc(dinero(d.valor_hora))}<br><small class="inc-nota">${esc(o)}</small>`;
  }
  function calculoTxt(l) {
    const d = l.detalle || {}, vh = d.valor_hora != null ? dinero(d.valor_hora) : 'valor por hora';
    if (d.horas_dobles != null) {
      const p = [];
      if (Number(d.horas_dobles)) p.push(`${fmtN(d.horas_dobles)} h × ${vh} × ${fmtN(d.factor_doble)}`);
      if (Number(d.horas_triples)) p.push(`${fmtN(d.horas_triples)} h × ${vh} × ${fmtN(d.factor_triple)}`);
      return p.join(' + ') || '—';
    }
    if (d.regla === 'horas_sueldo') return `${fmtN(l.cantidad)} h × ${vh}` + (d.factor != null && Number(d.factor) !== 1 ? ' × ' + fmtN(d.factor) : '');
    if (d.tarifa != null) return `${fmtN(l.cantidad)} × ${dinero(d.tarifa)}`;
    if (d.regla === 'prima_dominical') return `${fmtN(l.cantidad)} × ${d.sueldo_diario != null ? dinero(d.sueldo_diario) : 'sueldo diario'} × ${fmtN(d.pct)} %`;
    if (d.regla === 'porcentaje_sueldo') return `${fmtN(l.cantidad)} × ${d.sueldo_diario != null ? dinero(d.sueldo_diario) : 'sueldo diario'}` + (d.factor != null && Number(d.factor) !== 1 ? ' × ' + fmtN(d.factor) : '');
    if (d.regla === 'descuento_operativo') return 'Importe capturado';
    return '—';
  }
  const etiquetaOpcion = o => `${o.clasificacion || 'Esquema'} · ${MODALIDAD[o.modalidad] || o.modalidad}${o.registro_patronal ? ' · RP ' + o.registro_patronal : ''}`;
  function nombreEsquema(id, H) {
    if (!id) return 'por asignar';
    const rp = H.rps.get(id), cl = rp ? H.cls.get(rp.clasificacion_id) : null;
    return cl ? cl.nombre : 'esquema';
  }
  function etiquetaEsquema(l, H) {
    const rel = H.rels.get(l.relacion_laboral_id);
    const pat = rel && rel.registro_patronal_id ? H.pats.get(rel.registro_patronal_id) : null;
    const relTxt = rel ? (pat ? 'RP ' + pat.registro_patronal : 'sin registro patronal') : '';
    const opciones = H.h.estado === 'enviada' ? (H.opciones[l.id] || []) : [];
    const selector = opciones.length ? `<br><select class="inc-esq" data-esq="${esc(l.id)}" aria-label="Esquema de pago"><option value="">Elige el esquema…</option>${opciones.map(o => `<option value="${esc(o.registro_pago_id)}" ${o.registro_pago_id === l.registro_pago_id ? 'selected' : ''}>${esc(etiquetaOpcion(o))}</option>`).join('')}</select><button type="button" class="inc-sec" data-asignar="${esc(l.id)}">${l.registro_pago_id ? 'Cambiar' : 'Asignar'}</button>` : '';
    if (l.origen === 'por_asignar') {
      return `<b>Esquema por asignar</b><span class="inc-motivo">${esc((l.detalle && l.detalle.motivo) || 'Nómina elige el esquema de pago.')}</span>${selector || (H.h.estado === 'enviada' ? '<span class="inc-motivo">Registra un esquema de pago vigente en la ficha de la persona.</span>' : '')}`;
    }
    if (l.registro_pago_id) {
      const rp = H.rps.get(l.registro_pago_id), cl = rp ? H.cls.get(rp.clasificacion_id) : null;
      const asig = l.detalle && l.detalle.asignacion === 'manual' ? 'asignado por Nómina' : l.detalle && l.detalle.asignacion === 'preferido' ? 'esquema preferido' : l.detalle && l.detalle.asignacion === 'unico' ? 'único esquema vigente' : '';
      return `<b>${esc(cl ? cl.nombre : 'Esquema')}</b>${relTxt || asig ? `<br><small class="inc-nota">${esc([relTxt, asig].filter(Boolean).join(' · '))}</small>` : ''}${selector}`;
    }
    if (l.modalidad === 'manual') return `Sueldo manual${relTxt ? `<br><small class="inc-nota">${esc(relTxt)}</small>` : ''}`;
    if (l.origen === 'sin_sueldo') return `<b>Sin esquema enlazado</b>${relTxt ? `<br><small class="inc-nota">${esc(relTxt)}</small>` : ''}`;
    return `No depende del sueldo${relTxt ? `<br><small class="inc-nota">${esc(relTxt)}</small>` : ''}`;
  }
  function badgeModalidad(l, H) {
    const k = categoria(l, H);
    if (k === 'bruto' || k === 'neto' || k === 'manual') return `<span class="inc-mod ${k}">${esc(MODALIDAD[k])}</span>`;
    if (k === 'tarifa') return '<span class="inc-mod tarifa">Tarifa</span>';
    if (k === 'descuento') return '<span class="inc-mod tarifa">Descuento</span>';
    return '—';
  }
  const resumenTotales = (t, id) => `<div class="inc-subtot" ${id ? `id="${id}"` : ''}>${CATEGORIAS.filter(([k]) => t[k]).map(([k, n]) => `<span data-cat="${k}">${esc(n)}: ${esc(dinero(t[k]))}</span>`).join('') || '<span>Sin importes</span>'}</div>`;

  function pintarRevHoja() {
    const H = S.rev.H, h = H.h, cont = $('inc-vista');
    const editable = h.estado === 'enviada';
    const yo = S.usuarioId;
    const firmas = H.eventos.filter(e => e.version_id === H.version.id && (e.tipo === 'firma_nomina' || e.tipo === 'firma_rh'));
    const firma = t => firmas.find(e => e.tipo === t);
    const envio = H.eventos.find(e => e.version_id === H.version.id && (e.tipo === 'envio' || e.tipo === 'complemento'));
    const devs = H.eventos.filter(e => e.tipo === 'devolucion');
    const puedeFirmar = (area, campo) => ['enviada', 'procesada'].includes(h.estado) && !firma('firma_' + area) && H.prm[campo] === yo;
    const bloqueFirma = (area, campo, nombre) => {
      const f = firma('firma_' + area);
      if (f) return `<span class="inc-chip ok">✓ ${nombre}: ${esc(f.nombre || '')} · ${esc(fechaHora(f.creado_en))}</span>`;
      if (puedeFirmar(area, campo)) return `<button type="button" class="inc-sec" data-firmar="${area}">Firmar como ${nombre}</button>`;
      return `<span class="inc-chip">${nombre}: sin firma${H.prm[campo] ? '' : ' (sin responsable designado)'}</span>`;
    };
    // --- captura (de la versión enviada; solo lectura) ---
    const dias = rango(H.periodo.inicio, H.periodo.fin);
    const conceptos = [...H.conceptos.values()].filter(c => (H.datos.cantidades || []).some(q => q.concepto_id === c.id));
    const celdas = new Map((H.datos.celdas || []).map(c => [c.personal_id + '|' + c.fecha, c]));
    const totCant = new Map(); (H.datos.cantidades || []).forEach(q => { const k = q.personal_id + '|' + q.concepto_id; totCant.set(k, (totCant.get(k) || 0) + num(q.cantidad)); });
    const obs = new Map((H.datos.observaciones || []).map(o => [o.personal_id, o.texto]));
    const idsCaptura = [...new Set([...(H.datos.celdas || []).map(c => c.personal_id), ...(H.datos.cantidades || []).map(q => q.personal_id), ...obs.keys()])];
    const nombreP = id => { const p = H.personas.get(id); return p ? p.nombre_completo : id; };
    idsCaptura.sort((a, b) => nombreP(a).localeCompare(nombreP(b), 'es'));
    const captura = idsCaptura.length ? `<div class="inc-tabla-wrap"><table class="inc-tabla" id="inc-r-captura"><thead><tr><th class="inc-col-persona">Persona</th>${dias.map(f => `<th>${esc(dia(f))}</th>`).join('')}${conceptos.map(c => `<th title="${esc(c.nombre)}">${esc(c.abreviatura)}</th>`).join('')}<th>Observación</th></tr></thead><tbody>${idsCaptura.map(pid => `<tr>
        <td class="inc-col-persona"><b>${esc(nombreP(pid))}</b></td>
        ${dias.map(f => { const c = celdas.get(pid + '|' + f), v = c && c.codigo; return `<td class="${v ? 'inc-cod-' + esc(v) : ''}" title="${esc(v ? NOMBRE_CODIGO[v] || v : 'Asistió')}">${esc(v || '·')}</td>`; }).join('')}
        ${conceptos.map(c => { const t = totCant.get(pid + '|' + c.id); return `<td class="inc-total">${t ? esc(String(Math.round(t * 100) / 100)) : ''}</td>`; }).join('')}
        <td style="text-align:left">${esc(obs.get(pid) || '')}</td></tr>`).join('')}</tbody></table></div>`
      : '<p class="hint">La hoja se envió sin incidencias: todos asistieron normalmente.</p>';
    // --- importes ---
    const visibles = H.lineas.filter(l => H.verDescartadas || l.origen !== 'descartado');
    const nDesc = H.lineas.filter(l => l.origen === 'descartado').length;
    const nPend = H.lineas.filter(l => l.origen === 'pendiente' && l.sugerido != null).length;
    const nSin = H.lineas.filter(l => l.origen === 'sin_sueldo').length;
    const nAsig = H.lineas.filter(l => l.origen === 'por_asignar').length;
    const totHoja = sumarPorCategoria(H.lineas.filter(l => l.origen !== 'descartado'), H);
    const porPersona = new Map(); visibles.forEach(l => { if (!porPersona.has(l.personal_id)) porPersona.set(l.personal_id, []); porPersona.get(l.personal_id).push(l); });
    const idsImp = [...porPersona.keys()].sort((a, b) => nombreP(a).localeCompare(nombreP(b), 'es'));
    const ordenCat = { bruto: 1, neto: 2, manual: 3, tarifa: 4, descuento: 5 };
    const filaLinea = l => {
      const c = H.conceptos.get(l.concepto_id) || {};
      const decide = editable && !['descartado', 'sin_importe', 'por_asignar'].includes(l.origen);
      const motivo = l.origen === 'sin_sueldo' ? `<span class="inc-motivo">${esc((l.detalle && l.detalle.motivo) || 'Sin sueldo para calcular este importe.')}</span>` : '';
      const nAj = H.ajustes.filter(a => a.importe_id === l.id && a.tipo === 'importe').length;
      return `<tr data-linea="${esc(l.id)}" data-origen="${esc(l.origen)}" data-cat="${esc(categoria(l, H) || '')}" class="${l.origen === 'sin_sueldo' ? 'inc-sin-sueldo' : ''} ${l.origen === 'descartado' ? 'inc-descartada' : ''} ${l.origen === 'por_asignar' ? 'inc-por-asignar' : ''}">
        <td><b>${esc(c.abreviatura || '')}</b><br><small class="inc-nota">${esc(c.nombre || '')}</small></td>
        <td class="n">${esc(String(Number(l.cantidad)))} <small class="inc-nota">${esc(c.unidad || '')}</small></td>
        <td class="n" data-valor-hora>${valorHoraHtml(l)}</td>
        <td class="inc-calc" data-calculo>${esc(calculoTxt(l))}</td>
        <td>${badgeModalidad(l, H)} ${etiquetaEsquema(l, H)}</td>
        <td class="n">${l.sugerido != null ? esc(dinero(l.sugerido)) : '—'}</td>
        <td class="n">${decide ? `<input type="number" min="0" step="0.01" class="inc-final" data-final="${esc(l.id)}" value="${l.final != null ? esc(Number(l.final)) : ''}" placeholder="${l.sugerido != null ? esc(Number(l.sugerido)) : 'Importe'}" aria-label="Importe final"><br><input type="text" maxlength="200" class="inc-motivo-aj" data-motivo="${esc(l.id)}" placeholder="Motivo si cambias el importe" aria-label="Motivo del ajuste">` : (l.final != null ? esc(dinero(l.final)) : '—')}</td>
        <td><span class="inc-dec ${esc(l.origen)}">${esc(DECISION[l.origen] || l.origen)}</span>${nAj ? `<span class="inc-nota" style="display:block">${plural(nAj, 'ajuste')}</span>` : ''}${motivo}</td>
        <td>${decide ? `${l.origen === 'pendiente' && l.sugerido != null ? `<button type="button" class="inc-sec" data-aceptar="${esc(l.id)}">Aceptar</button>` : ''}<button type="button" class="inc-sec" data-guardar="${esc(l.id)}">Guardar</button>` : ''}</td></tr>`;
    };
    const tablaImportes = idsImp.length ? `<div class="inc-tabla-wrap" style="max-height:none"><table class="inc-lista inc-imp" id="inc-r-importes"><thead><tr><th>Concepto</th><th class="n">Cantidad</th><th class="n">Valor por hora</th><th>Cálculo</th><th>Esquema de pago</th><th class="n">Sugerido</th><th class="n">Final</th><th>Estado</th><th></th></tr></thead><tbody>${idsImp.map(pid => {
      const ls = porPersona.get(pid).slice().sort((a, b) => (String((H.conceptos.get(a.concepto_id) || {}).orden || 0) + (ordenCat[categoria(a, H)] || 9)).localeCompare(String((H.conceptos.get(b.concepto_id) || {}).orden || 0) + (ordenCat[categoria(b, H)] || 9)));
      const sinS = ls.some(l => l.origen === 'sin_sueldo');
      const man = H.manuales.get(pid);
      return `<tr class="inc-persona" data-persona="${esc(pid)}"><td colspan="9">${esc(nombreP(pid))} ${resumenTotales(sumarPorCategoria(ls.filter(l => l.origen !== 'descartado'), H))}
          ${editable && (sinS || man != null) ? `<div style="margin-top:6px;font-weight:400">${sinS ? '<span class="inc-motivo" style="display:inline">Sin sueldo en esta empresa: </span>' : ''}<input type="number" min="0.01" step="0.01" class="inc-manual" data-manual="${esc(pid)}" value="${man != null ? esc(Number(man)) : ''}" placeholder="Sueldo diario" aria-label="Sueldo diario manual de ${esc(nombreP(pid))}"><button type="button" class="inc-sec" data-manual-btn="${esc(pid)}">${man != null ? 'Actualizar sueldo manual' : 'Usar sueldo diario manual'}</button></div>` : (man != null ? `<div class="inc-nota" style="font-weight:400">Sueldo diario manual del periodo: ${esc(dinero(man))}</div>` : '')}
        </td></tr>${ls.map(filaLinea).join('')}`;
    }).join('')}</tbody></table></div>` : '<p class="hint">Esta versión no generó importes.</p>';

    const otrasHojas = H.comps.length > 1 ? `<div class="inc-chips">${H.comps.map((x, i) => `<button type="button" class="inc-sec" data-rev-hoja="${esc(x.id)}" ${x.id === h.id ? 'disabled' : ''}>${x.tipo === 'normal' ? 'Hoja' : 'Complemento ' + i} · ${esc(ESTADO_TAB[x.estado] || x.estado)}</button>`).join('')}</div>` : '';
    cont.innerHTML = `<div class="card">
      <button type="button" class="inc-volver" id="inc-r-volver">← Periodo ${esc(fechaLarga(H.periodo.inicio))} – ${esc(fechaLarga(H.periodo.fin))}</button>
      <div class="inc-cab"><div><h2>${esc(H.coord ? H.coord.nombre_completo : 'Coordinador')}${h.tipo === 'complemento' ? ' · complemento' : ''}</h2>
        <p class="hint">${esc(nombreEmpresa(H.periodo.empresa_id))} · versión ${H.version.numero}${envio ? ' enviada el ' + esc(fechaHora(envio.creado_en)) + (envio.nombre ? ' por ' + esc(envio.nombre) : '') : ''}</p></div>
        <div><span class="inc-estado ${esc(h.estado)}" id="inc-r-estado">${esc(ESTADO_TAB[h.estado] || h.estado)}</span></div></div>
      ${otrasHojas}
      ${H.datos.observacion_general ? `<div class="inc-panel"><b>Observación del coordinador</b><p style="margin:4px 0 0">${esc(H.datos.observacion_general)}</p></div>` : ''}
      ${h.estado === 'devuelta' && devs[0] ? `<div class="inc-msg err" style="display:block">Devuelta por ${esc(devs[0].nombre || '')}: ${esc(devs[0].motivo || '')}. El coordinador la corrige y la reenvía.</div>` : ''}
      ${h.estado === 'procesada' ? '<div class="inc-msg info" style="display:block">El periodo ya se procesó: esta hoja es de solo lectura. Las correcciones llegan como complemento.</div>' : ''}
      <div class="inc-msg" id="inc-r-msg"></div>
      <div class="inc-chips" id="inc-r-firmas">${bloqueFirma('nomina', 'responsable_nomina_user', 'Nómina')}${bloqueFirma('rh', 'responsable_rh_user', 'RH')}</div>

      <h3 style="margin:18px 0 6px">Captura enviada</h3>
      <p class="inc-nota">Solo lectura: es la versión ${H.version.numero} tal como la envió el coordinador.</p>
      ${captura}

      <h3 style="margin:18px 0 6px">Importes</h3>
      <p class="inc-nota">Una línea por esquema de pago. Bruto y neto se muestran por separado y nunca se suman entre sí. Base de la empresa al enviar: ${esc(((H.datos.parametros || {}).base_calculo) || '—')}.</p>
      <div class="inc-chips" id="inc-r-totales">${CATEGORIAS.filter(([k]) => k === 'bruto' || k === 'neto' || totHoja[k]).map(([k, n]) =>`<span class="inc-chip" data-total="${k}">${esc(n)}: ${esc(dinero(totHoja[k]))}</span>`).join('')}
        ${nSin ? `<span class="inc-chip alerta" id="inc-r-sinsueldo">${plural(nSin, 'línea')} sin sueldo</span>` : ''}
        ${nAsig ? `<span class="inc-chip alerta" id="inc-r-porasignar">${plural(nAsig, 'línea')} con esquema por asignar</span>` : ''}
        ${nPend ? `<span class="inc-chip">${plural(nPend, 'importe')} por decidir</span>` : ''}</div>
      <div class="inc-acciones">
        ${editable && nPend ? `<button type="button" class="primary" id="inc-r-aceptar-todos">Aceptar los ${nPend} sugeridos pendientes</button>` : ''}
        ${nDesc ? `<button type="button" class="inc-sec" id="inc-r-descartadas">${H.verDescartadas ? 'Ocultar' : 'Mostrar'} ${plural(nDesc, 'línea descartada', 'líneas descartadas')}</button>` : ''}
      </div>
      ${tablaImportes}
      ${H.ajustes.length ? `<h3 style="margin:18px 0 6px">Bitácora de ajustes</h3>
      <p class="inc-nota">Cada cambio de importe o de esquema queda registrado y no se puede editar ni borrar. El sugerido original se conserva.</p>
      <div class="inc-tabla-wrap" style="max-height:none"><table class="inc-lista inc-imp" id="inc-r-ajustes"><thead><tr><th>Fecha</th><th>Persona</th><th>Concepto</th><th>Cambio</th><th>Motivo</th><th>Quién</th></tr></thead><tbody>${H.ajustes.slice().reverse().map(a => {
        const l = H.lineas.find(x => x.id === a.importe_id) || {}, c = H.conceptos.get(l.concepto_id) || {};
        const cambio = a.tipo === 'importe' ? `${dinero(a.anterior)} → ${dinero(a.nuevo)}` : `Esquema: ${nombreEsquema(a.esquema_anterior, H)} → ${nombreEsquema(a.esquema_nuevo, H)}`;
        return `<tr data-ajuste="${esc(a.tipo)}"><td>${esc(fechaHora(a.creado_en))}</td><td>${esc(nombreP(l.personal_id))}</td><td>${esc(c.abreviatura || '')}</td><td>${esc(cambio)}</td><td>${esc(a.motivo || '—')}</td><td>${esc(a.nombre || '')}</td></tr>`;
      }).join('')}</tbody></table></div>` : ''}

      ${editable ? `<div class="inc-panel" id="inc-r-devolver-panel">
        ${H.devolviendo ? `<b>Devolver al coordinador</b>
          <div class="inc-fila"><div><label for="inc-r-area">Quién devuelve</label><select id="inc-r-area"><option value="nomina">Nómina</option><option value="rh">RH</option></select></div></div>
          <label for="inc-r-motivo" class="inc-nota">Motivo (lo verá el coordinador)</label><textarea id="inc-r-motivo" placeholder="Qué debe corregir"></textarea>
          <div class="inc-acciones"><button type="button" class="inc-peligro" id="inc-r-devolver-ok">Devolver hoja</button><button type="button" class="inc-sec" id="inc-r-devolver-no">Cancelar</button></div>`
          : '<button type="button" class="inc-peligro" id="inc-r-devolver">Devolver al coordinador</button> <span class="inc-nota">La versión enviada se conserva; el coordinador corrige y al reenviar nace una versión nueva.</span>'}
      </div>` : ''}
    </div>`;

    $('inc-r-volver').addEventListener('click', () => { S.rev = { periodoId: H.periodo.id }; vistaRevision(); });
    cont.querySelectorAll('[data-rev-hoja]').forEach(b => b.addEventListener('click', () => { S.rev = { periodoId: H.periodo.id, hojaId: b.dataset.revHoja }; vistaRevision(); }));
    const accion = async (fn, okTxt) => {
      const { data, error } = await fn();
      if (error) { msg('inc-r-msg', 'err', limpiarError(error)); return false; }
      await revHoja(); msg('inc-r-msg', 'ok', typeof okTxt === 'function' ? okTxt(data) : okTxt); return true;
    };
    cont.querySelectorAll('[data-aceptar]').forEach(b => b.addEventListener('click', () => { b.disabled = true; accion(() => sb.rpc('inc_decidir_importe', { p_importe: b.dataset.aceptar, p_final: null }), 'Importe aceptado.'); }));
    cont.querySelectorAll('[data-guardar]').forEach(b => b.addEventListener('click', () => {
      const inp = cont.querySelector(`[data-final="${b.dataset.guardar}"]`);
      const v = inp && inp.value.trim();
      if (!v) return msg('inc-r-msg', 'err', 'Escribe el importe final o usa «Aceptar».');
      const l = H.lineas.find(x => x.id === b.dataset.guardar) || {};
      const mot = (cont.querySelector(`[data-motivo="${b.dataset.guardar}"]`) || {}).value || '';
      const cambia = l.sugerido == null || num(v) !== Number(l.sugerido) || l.origen === 'modificado';
      if (cambia && !mot.trim() && !(l.final != null && num(v) === Number(l.final))) return msg('inc-r-msg', 'err', 'Escribe el motivo del ajuste: queda en la bitácora.');
      b.disabled = true; accion(() => sb.rpc('inc_decidir_importe', { p_importe: b.dataset.guardar, p_final: num(v), p_motivo: mot.trim() || null }), 'Importe guardado.');
    }));
    cont.querySelectorAll('[data-manual-btn]').forEach(b => b.addEventListener('click', () => {
      const inp = cont.querySelector(`[data-manual="${b.dataset.manualBtn}"]`), v = num(inp && inp.value);
      if (!(v > 0)) return msg('inc-r-msg', 'err', 'Escribe un sueldo diario mayor a cero.');
      b.disabled = true; accion(() => sb.rpc('inc_capturar_sueldo_manual', { p_periodo: H.periodo.id, p_personal: b.dataset.manualBtn, p_sueldo: v }), 'Sueldo diario guardado y importes recalculados. Lo que ya modificaste no cambió.');
    }));
    cont.querySelectorAll('[data-asignar]').forEach(b => b.addEventListener('click', () => {
      const sel = cont.querySelector(`[data-esq="${b.dataset.asignar}"]`);
      if (!sel || !sel.value) return msg('inc-r-msg', 'err', 'Elige el esquema de pago de la línea.');
      b.disabled = true; accion(() => sb.rpc('inc_asignar_esquema', { p_importe: b.dataset.asignar, p_registro_pago: sel.value }), 'Esquema asignado. Ahora acepta o modifica el importe.');
    }));
    if ($('inc-r-aceptar-todos')) $('inc-r-aceptar-todos').addEventListener('click', () => { $('inc-r-aceptar-todos').disabled = true; accion(() => sb.rpc('inc_aceptar_sugeridos', { p_version: H.version.id }), n => `${plural(n || 0, 'importe aceptado', 'importes aceptados')}.`); });
    if ($('inc-r-descartadas')) $('inc-r-descartadas').addEventListener('click', () => { H.verDescartadas = !H.verDescartadas; pintarRevHoja(); });
    cont.querySelectorAll('[data-firmar]').forEach(b => b.addEventListener('click', () => { b.disabled = true; accion(() => sb.rpc('inc_firmar_hoja', { p_hoja: h.id, p_area: b.dataset.firmar }), 'Firma registrada sobre la versión ' + H.version.numero + '.'); }));
    if ($('inc-r-devolver')) $('inc-r-devolver').addEventListener('click', () => { H.devolviendo = true; pintarRevHoja(); });
    if ($('inc-r-devolver-no')) $('inc-r-devolver-no').addEventListener('click', () => { H.devolviendo = false; pintarRevHoja(); });
    if ($('inc-r-devolver-ok')) $('inc-r-devolver-ok').addEventListener('click', () => {
      const motivo = $('inc-r-motivo').value.trim();
      if (!motivo) return msg('inc-r-msg', 'err', 'Escribe el motivo de la devolución.');
      $('inc-r-devolver-ok').disabled = true;
      accion(() => sb.rpc('inc_devolver_hoja', { p_hoja: h.id, p_motivo: motivo, p_area: $('inc-r-area').value }), 'Hoja devuelta al coordinador.');
    });
  }

  // ---------- conexión con el menú ----------
  const btn = document.querySelector('nav.tabs button[data-tab="incidencias"]');
  if (btn) btn.addEventListener('click', () => { if (typeof pestanaPermitida !== 'function' || pestanaPermitida('incidencias')) abrir(); });
  window.beehumanIncidencias = { abrir };
})();
