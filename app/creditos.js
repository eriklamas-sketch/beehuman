// BeeHuman · B5: créditos y descuentos (13-nov-2026).
// - Ficha → «Prestaciones y créditos»: registro de créditos por relación
//   laboral, cambios con motivo, estado, historia y movimientos de saldo.
// - Incidencias → Revisión → periodo: panel «Descuentos del periodo».
// Solo Administrador y Nómina. La protección real está en la base de datos
// (RLS y funciones); aquí solo se presenta. Registrar un crédito no es
// descontarlo: INFONAVIT y pensiones porcentuales son informativos (datos
// para NOI) y no generan importes.
(function () {
  const $ = id => document.getElementById(id);
  const esc = v => String(v == null ? '' : v).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const dinero = n => n == null || n === '' ? '—' : '$' + Number(n).toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const num = v => Number(String(v).replace(/[$,\s]/g, ''));
  const limpiar = e => String((e && (e.message || e.details)) || e || 'Error').replace(/^BeeHuman:\s*/, '');
  const fecha = f => { if (!f) return '—'; const [a, m, d] = String(f).slice(0, 10).split('-'); return `${d}/${m}/${a}`; };
  const fechaHora = f => f ? new Date(f).toLocaleString('es-MX', { dateStyle: 'short', timeStyle: 'short' }) : '—';
  const hoy = () => { const d = new Date(); return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10); };
  const puede = () => typeof rolActual !== 'undefined' && ['administrador', 'nomina'].includes(rolActual);
  const nombreEmpresa = id => { try { const e = (typeof empresas !== 'undefined' ? empresas : []).find(x => String(x.id) === String(id)); return e ? e.nombre : 'Empresa'; } catch (_) { return 'Empresa'; } };
  const TIPOS = { infonavit: 'INFONAVIT', fonacot: 'FONACOT', prestamo: 'Préstamo', anticipo: 'Anticipo', pension: 'Pensión alimenticia', otro: 'Otro descuento recurrente' };
  const ESTADOS = { incompleto: 'Incompleto', activo: 'Activo', suspendido: 'Suspendido', terminado: 'Terminado' };
  const INF_TIPOS = { cuota_fija: 'Cuota fija mensual', porcentaje: 'Porcentaje del SBC', factor_vsm_uma: 'Factor (VSM / UMA)' };
  const EVENTOS = { alta: 'Alta', cambio: 'Cambio', suspension: 'Suspensión', reactivacion: 'Reactivación', terminacion: 'Terminación', activacion: 'Activación', conversion: 'Conversión del expediente', terminacion_saldo: 'Terminado por saldo liquidado' };
  const etiqueta = c => (c.tipo === 'otro' ? (c.concepto || 'Descuento') : TIPOS[c.tipo]) + (c.referencia ? ' · ' + c.referencia : '');

  if (!document.getElementById('cred-css')) {
    const st = document.createElement('style'); st.id = 'cred-css';
    st.textContent = `
.cred{container-type:inline-size}
.cred .cred-g-chips .cred-est,.cred .cred-g-cnt{white-space:nowrap}
.cred-h3{display:flex;justify-content:space-between;align-items:center;gap:8px 16px;flex-wrap:wrap}
#cred-saldo-total{display:inline-flex;align-items:baseline;gap:8px;flex-wrap:wrap;font:500 12.5px Inter,sans-serif;text-transform:none;letter-spacing:0;color:#45506A;background:#F4F6FA;border:1px solid #E2E7F0;border-radius:12px;padding:6px 12px}
#cred-saldo-total b{font:700 16px Montserrat,sans-serif;color:#1D2A44}
#cred-saldo-total .cred-st-n{font-size:11.5px;color:#6B7385}
.cred .cred-intro{margin:0 0 12px;color:#45506A;font-size:13px;line-height:1.5}
.cred table{width:100%;border-collapse:collapse;font-size:13px}
.cred th{font:600 11px Montserrat,sans-serif;text-transform:uppercase;letter-spacing:.04em;color:#6B7385;text-align:left;padding:8px 10px;border-bottom:1px solid #E5E9F1;background:#F8FAFC}
.cred td{padding:9px 10px;border-bottom:1px solid #EEF1F6;vertical-align:top}
.cred td.n,.cred th.n{text-align:right;white-space:nowrap}
.cred .cred-wrap{overflow-x:auto;border:1px solid #E5E9F1;border-radius:12px;background:#fff}
.cred .cred-est{display:inline-block;padding:2px 9px;border-radius:999px;font-size:11.5px;font-weight:600;background:#EAF4EE;color:#1F6B40}
.cred .cred-est.incompleto{background:#FFF4D6;color:#7A5300}.cred .cred-est.suspendido{background:#F1F2F4;color:#45506A}.cred .cred-est.terminado{background:#F1F2F4;color:#6B7385}
.cred .cred-est.pendiente{background:#FFF4D6;color:#7A5300}.cred .cred-est.modificado{background:#E8EEFB;color:#2443A3}.cred .cred-est.descartado{background:#F1F2F4;color:#6B7385}
.cred .cred-info{font-size:11.5px;color:#6B7385}
.cred .cred-sec{background:#fff;border:1px solid #D7DCE6;color:#26324A;border-radius:9px;padding:5px 11px;font-size:12.5px;cursor:pointer;margin:2px 4px 2px 0}
.cred .cred-sec:hover{border-color:#2E6945}
.cred .cred-form{border:1px solid #E5E9F1;border-radius:14px;padding:16px;margin:14px 0;background:#F8FAF7}
.cred .cred-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:10px 14px}
.cred .cred-grid label{display:block;font-size:12px;color:#68717A;margin-bottom:4px}
.cred .cred-grid input,.cred .cred-grid select{width:100%;box-sizing:border-box}
.cred .cred-msg{display:none;margin:10px 0;padding:9px 12px;border-radius:10px;font-size:13px}
.cred .cred-msg.err{display:block;background:#FDECEC;color:#8A1F1F}.cred .cred-msg.ok{display:block;background:#EAF4EE;color:#1F6B40}
.cred .cred-mini{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:6px}
.cred .cred-mini input,.cred .cred-mini select{padding:5px 7px;font-size:12.5px;border:1px solid #D7DCE6;border-radius:8px}
.cred .cred-hist{background:#FAFBFC;font-size:12.5px}
.cred input.cred-final{width:100px;text-align:right}
.cred input.cred-motivo{width:140px}
.cred h3.cred-h{font:700 13px Montserrat,sans-serif;letter-spacing:.045em;text-transform:uppercase;color:#2E6945;margin:22px 0 8px}
.cred .cred-lista{display:flex;flex-direction:column;gap:12px}
.cred .cred-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,380px),1fr));gap:12px}
.cred .cred-card{background:#fff;border:1px solid #E5E9F1;border-left:4px solid #2E6945;border-radius:14px;padding:12px 16px;display:flex;flex-direction:column;gap:9px;min-width:0}
.cred .cred-card.abierta{grid-column:1/-1}
.cred .cred-card.pendiente{border-left-color:#E0A526;background:#FFFCF3}
.cred .cred-card.informativo{border-left-color:#6B7FA6;background:#F7F9FC}
.cred .cred-card.suspendido{border-left-color:#9AA3B2}
.cred .cred-card.terminado{border-left-color:#C9CED8;background:#FAFAFB;opacity:.85}
.cred .cred-card-h{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;flex-wrap:wrap}
.cred .cred-nombre{font:700 14.5px Montserrat,sans-serif;color:#26324A}
.cred .cred-est.activo{background:#EAF4EE;color:#1F6B40}.cred .cred-est.informativo{background:#E8EEF8;color:#34466F}
.cred .cred-metricas{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px 14px;border-top:1px solid #EEF1F6;padding-top:10px}
.cred .cred-m{display:flex;flex-direction:column;gap:2px;min-width:0}
.cred .cred-m-t{font:600 10.5px Montserrat,sans-serif;text-transform:uppercase;letter-spacing:.04em;color:#6B7385}
.cred .cred-m b{font-size:15px;color:#26324A}
.cred .cred-m-n{font-size:11.5px;color:#6B7385}
.cred .cred-aviso{background:#FFF4D6;color:#6A4A00;border-radius:10px;padding:8px 11px;font-size:12.5px}
.cred .cred-aviso.listo{background:#FFF0C7}
.cred .cred-acciones{display:flex;flex-wrap:wrap;gap:4px}
.cred .cred-sec.cred-activar{background:#F2B51D;border-color:#F2B51D;color:#2B2100;font-weight:700}
.cred .cred-hist{background:#FAFBFC;border-radius:10px;padding:8px 10px;font-size:12.5px}
.cred details.cred-term>summary{cursor:pointer;font:600 12.5px Inter,sans-serif;color:#45506A;padding:6px 2px}
.cred details.cred-term>.cred-cards{margin-top:8px}
.cred .cred-top{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:12px}
.cred .cred-resumen{display:flex;flex-wrap:wrap;gap:6px}
.cred .cred-chip{display:inline-flex;align-items:center;gap:5px;border:1px solid #DCE2EC;background:#fff;color:#45506A;border-radius:999px;padding:5px 11px;font:500 12.5px Inter,sans-serif;cursor:pointer}
.cred .cred-chip b{font-weight:700;color:#1D2A44}
.cred .cred-chip.on{background:#1D2A44;border-color:#1D2A44;color:#fff}.cred .cred-chip.on b{color:#F2B51D}
.cred .cred-chip.pendiente:not(.on){border-color:#F0D27A;background:#FFF8E2}
.cred .cred-nuevo{margin:0;white-space:nowrap}
.cred .cred-buscar{width:100%;box-sizing:border-box;margin:0 0 12px;padding:9px 12px;border:1px solid #DCE2EC;border-radius:10px;font-size:13px}
.cred .cred-lista{gap:10px}
.cred details.cred-grupo{border:1px solid #E5E9F1;border-radius:14px;background:#fff;overflow:hidden}
.cred details.cred-grupo[open]{background:#FBFCFD}
.cred details.cred-grupo.term{background:#F6F7F9}
.cred details.cred-grupo>summary{list-style:none;display:grid;grid-template-columns:auto auto auto 1fr auto auto;align-items:center;gap:10px;padding:12px 16px;cursor:pointer}
.cred details.cred-grupo>summary::-webkit-details-marker{display:none}
.cred .cred-g-ic{color:#1D2A44;display:flex}
.cred .cred-g-n{font:700 14.5px Montserrat,sans-serif;color:#1D2A44;white-space:nowrap}
.cred .cred-g-cnt{font-size:11.5px;font-weight:600;color:#45506A;background:#EEF1F6;border-radius:999px;padding:2px 9px;white-space:nowrap}
.cred .cred-g-chips{display:flex;gap:5px;flex-wrap:wrap}
.cred .cred-g-res{display:flex;gap:18px;justify-content:flex-end;flex-wrap:wrap}
.cred .cred-g-m{display:flex;flex-direction:column;align-items:flex-end;min-width:0}
.cred .cred-g-m b{font-size:14.5px;color:#1D2A44}
.cred .cred-g-flecha{width:9px;height:9px;border-right:2px solid #45506A;border-bottom:2px solid #45506A;transform:rotate(45deg);margin:0 4px 4px}
.cred details.cred-grupo[open] .cred-g-flecha{transform:rotate(-135deg);margin-top:6px}
.cred .cred-g-cuerpo{padding:0 12px 12px;display:flex;flex-direction:column;gap:8px}
.cred .cred-g-cuerpo .cred-cards{grid-template-columns:1fr;gap:8px}
.cred .cred-mas{align-self:flex-start}
.cred .cred-nota{margin-top:14px;font-size:12px}
/* Modal angosto (≈690 px): los importes del encabezado bajan a un renglón propio, uno junto al otro. */
@container (max-width:820px){
  .cred details.cred-grupo>summary{display:flex;flex-wrap:wrap;align-items:center;gap:8px 10px}
  .cred .cred-g-flecha{margin-left:auto;order:1}
  .cred .cred-g-res{order:2;flex-basis:100%;flex-wrap:nowrap;justify-content:flex-start;gap:32px;padding-left:30px}
  .cred .cred-g-m{align-items:flex-start}
}
@media (max-width:640px){
  .cred details.cred-grupo>summary{display:flex;flex-wrap:wrap;align-items:center;gap:6px 8px;padding:11px 12px}
  .cred .cred-g-n{white-space:normal;font-size:14px}
  .cred .cred-g-flecha{margin-left:auto;order:1}
  .cred .cred-g-chips,.cred .cred-g-res{order:2;flex-basis:100%}
  .cred .cred-g-chips:empty{display:none}
  .cred .cred-g-res{justify-content:flex-start;gap:14px;flex-wrap:wrap;padding-left:0}
  .cred .cred-g-m{align-items:flex-start}
  .cred .cred-m-n.sec{display:none}
  .cred .cred-card-h{flex-wrap:nowrap}.cred .cred-card-h .cred-est{white-space:normal;text-align:right;max-width:46%}
  .cred .cred-acciones{gap:3px}.cred .cred-acciones .cred-sec{font-size:12px;margin:0}
  .cred .cred-card{padding:11px 12px}
  .cred .cred-acciones .cred-sec{padding:5px 9px}
  .cred .cred-nuevo{width:100%}
  .cred .cred-metricas{grid-template-columns:1fr 1fr}
  .cred .cred-g-cuerpo{padding:0 8px 10px}
}
@media (max-width:640px){.cred .cred-grid{grid-template-columns:1fr}}`;
    document.head.appendChild(st);
  }

  // =====================================================================
  // 1. Ficha de la persona
  // =====================================================================
  const F = { personal: null, creditos: [], rels: [], pers: [], editando: null, abierto: {} };

  window.credFicha = async function (personalId) {
    const box = $('cred-ficha');
    if (!box) return;
    if (!puede()) { pintarSaldoPrestamos(box, false); box.innerHTML = ''; return; }
    F.personal = personalId; F.editando = null; F.abierto = {}; F.grupos = {}; F.verTodo = {}; F.filtro = ''; F.buscar = '';
    pintarSaldoPrestamos(box, false);   // no mostrar el total de la persona anterior mientras carga
    box.innerHTML = '<p class="hint">Cargando créditos…</p>';
    await cargarFicha(); pintarFicha();
  };

  async function cargarFicha() {
    const [c, r, p, d] = await Promise.all([
      sb.rpc('cred_creditos_persona', { p_personal: F.personal }),
      sb.from('relaciones_laborales').select('id, empresa_id, registro_patronal_id, estado, fecha_ingreso, fecha_baja').eq('personal_id', F.personal),
      sb.from('periodicidades').select('id, nombre').order('nombre'),
      // Solo lectura: descuentos ya registrados por periodo (propuesto y procesado). No calcula nada.
      sb.from('cred_descuentos').select('credito_id, periodo_id, sugerido, final, origen, periodo:inc_periodos(inicio, fin, procesado_en)').eq('personal_id', F.personal)
    ]);
    F.error = c.error; F.creditos = c.data || [];
    F.lineasError = !!d.error; F.lineas = d.error ? [] : (d.data || []);
    F.rels = (r.data || []).filter(x => x.estado !== 'anulada'); F.pers = p.data || [];
  }

  const relTxt = r => `${nombreEmpresa(r.empresa_id)}${r.estado !== 'vigente' || r.fecha_baja ? ' (baja ' + fecha(r.fecha_baja) + ')' : ''}${r.fecha_ingreso ? ' · desde ' + fecha(r.fecha_ingreso) : ''}`;

  // true solo si la base respondió explícitamente que no falta nada (null); undefined u otro valor ≠ completo.
  const datosCompletos = x => x.credito.estado === 'incompleto' && Object.prototype.hasOwnProperty.call(x, 'falta_para_activar') && x.falta_para_activar === null;

  // Créditos informativos: datos para NOI; nunca descuentan en BeeHuman ni se «activan».
  const esInformativo = c => c.tipo === 'infonavit' || (c.tipo === 'pension' && c.pension_forma === 'porcentaje');
  const ORIGEN_LINEA = { pendiente: 'Por decidir', aceptado: 'Aceptado', modificado: 'Modificado' };
  const perTxt = p => p ? `${fecha(p.inicio)} – ${fecha(p.fin)}` : '';

  // Propuesto (periodo abierto más reciente) y procesado (último periodo procesado), tal como están
  // guardados en cred_descuentos. La ficha no calcula importes: si no hay línea, lo dice.
  function lineasDe(c) {
    const ls = (F.lineas || []).filter(l => l.credito_id === c.id && l.origen !== 'descartado' && l.periodo);
    const porInicio = (a, b) => String(b.periodo.inicio).localeCompare(String(a.periodo.inicio));
    const abiertas = ls.filter(l => !l.periodo.procesado_en).sort(porInicio);
    const procesadas = ls.filter(l => l.periodo.procesado_en && l.final != null).sort(porInicio);
    return { propuesta: abiertas[0] || null, otrasAbiertas: Math.max(abiertas.length - 1, 0), procesada: procesadas[0] || null };
  }

  function estadoTxt(x, listo) {
    const c = x.credito;
    if (esInformativo(c)) return 'Informativo NOI · Sin descuento en BeeHuman' + (c.estado !== 'activo' ? ' · ' + ESTADOS[c.estado] : '');
    if (c.estado === 'incompleto') return listo ? 'Completo · falta activar' : 'Incompleto · faltan datos';
    return { activo: 'Activo · propone descuento', suspendido: 'Suspendido · no propone descuento', terminado: 'Terminado' }[c.estado] || ESTADOS[c.estado];
  }

  function avisoTxt(x, listo) {
    const c = x.credito;
    if (c.estado !== 'incompleto' || esInformativo(c)) return '';
    // Solo un null EXPLÍCITO en falta_para_activar significa «datos completos» (misma validación que «Activar»).
    if (listo) return '<div class="cred-aviso listo" data-cred-listo>Datos completos: pulsa «Activar» para que empiece a proponer descuentos. Te pedirá fecha efectiva y motivo.</div>';
    if (typeof x.falta_para_activar === 'string' && x.falta_para_activar) return `<div class="cred-aviso" data-cred-falta>Faltan datos: ${esc(x.falta_para_activar)} Sin descuento hasta completarlo.</div>`;
    return '<div class="cred-aviso" data-cred-sin-dato>Incompleto: no se pudo comprobar si los datos están completos. Vuelve a abrir la ficha.</div>';
  }

  // sec = nota secundaria (explicación); en celular se oculta para compactar. Importes, estados, vigencia y acciones no.
  const metrica = (titulo, valor, nota, attr, sec) => `<div class="cred-m"${attr ? ' ' + attr : ''}><span class="cred-m-t">${titulo}</span><b>${valor}</b>${nota ? `<span class="cred-m-n${sec ? ' sec' : ''}">${nota}</span>` : ''}</div>`;

  function metricasHtml(x) {
    const c = x.credito;
    if (esInformativo(c)) {
      const datos = c.tipo === 'infonavit'
        ? metrica('Tipo de descuento (NOI)', esc(INF_TIPOS[c.infonavit_tipo] || '—'), '') + metrica('Valor', esc(c.infonavit_valor == null ? '—' : c.infonavit_tipo === 'cuota_fija' ? dinero(c.infonavit_valor) : c.infonavit_tipo === 'porcentaje' ? c.infonavit_valor + ' %' : c.infonavit_valor), '')
          + metrica('Aviso de retención', esc(fecha(c.infonavit_fecha_aviso)), '')
        : metrica('Porcentaje (NOI)', esc((c.pension_valor ?? '—') + ' %'), 'Se calcula con el neto');
      return datos + metrica('Descuento en BeeHuman', 'No genera', 'Informativo', '', true);
    }
    const { propuesta, otrasAbiertas, procesada } = lineasDe(c);
    const prop = F.lineasError ? metrica('Descuento propuesto', '—', 'No se pudo consultar', 'data-propuesto')
      : propuesta ? metrica('Descuento propuesto', esc(dinero(propuesta.final != null ? propuesta.final : propuesta.sugerido)),
          `${esc(ORIGEN_LINEA[propuesta.origen] || '')} · ${esc(perTxt(propuesta.periodo))}${otrasAbiertas ? ` · +${otrasAbiertas} periodo${otrasAbiertas === 1 ? '' : 's'} abierto${otrasAbiertas === 1 ? '' : 's'}` : ''}`, 'data-propuesto')
      : metrica('Descuento propuesto', 'Sin propuesta aún', c.estado === 'incompleto' ? 'Se propone al activarlo' : c.estado === 'activo' ? 'Aparece al abrir la revisión del periodo' : '', 'data-propuesto', true);
    const proc = F.lineasError ? metrica('Procesado', '—', 'No se pudo consultar', 'data-procesado')
      : procesada ? metrica('Procesado', esc(dinero(procesada.final)), 'Periodo ' + esc(perTxt(procesada.periodo)), 'data-procesado')
      : metrica('Procesado', '—', 'Sin descuentos procesados', 'data-procesado', true);
    const saldo = x.saldo != null ? metrica('Saldo pendiente', esc(dinero(x.saldo)), 'de ' + esc(dinero(c.monto_total)), 'data-saldo') : '';
    return metrica('Importe configurado', c.importe_periodo != null ? esc(dinero(c.importe_periodo)) : '—', esc(x.periodicidad || ''), 'data-configurado') + prop + proc + saldo;
  }

  function tarjetaHtml(x) {
    const c = x.credito, ab = F.abierto[c.id];
    const listo = datosCompletos(x) && !esInformativo(c);
    // «Activar» solo en créditos completos pendientes de activar; nunca en informativos.
    // Suspender, Reactivar y Terminar, igual que antes.
    const trans = { activo: [['suspendido', 'Suspender'], ['terminado', 'Terminar']], suspendido: [['activo', 'Reactivar'], ['terminado', 'Terminar']],
      incompleto: listo ? [['activo', 'Activar'], ['terminado', 'Terminar']] : [['terminado', 'Terminar']] }[c.estado] || [];
    const clase = esInformativo(c) ? 'informativo' : c.estado === 'incompleto' ? 'pendiente' : c.estado;
    const editando = !!(F.editando && F.editando.credito && F.editando.credito.id === c.id);
    return `<article class="cred-card ${clase}${ab || editando ? ' abierta' : ''}" data-cred="${esc(c.id)}" data-tipo="${esc(c.tipo)}" data-estado="${esc(c.estado)}">
      <header class="cred-card-h">
        <div><b class="cred-nombre">${esc(etiqueta(c))}</b>
          <div class="cred-info">${x.empresa ? esc(x.empresa) + (x.registro_patronal ? ' · RP ' + esc(x.registro_patronal) : '') : 'Sin relación laboral'} · Vigencia ${esc(fecha(c.fecha_inicio))} – ${c.fecha_fin ? esc(fecha(c.fecha_fin)) : 'indefinida'}</div>
          ${c.origen === 'conversion_no_fonacot' ? '<div class="cred-info">Convertido del campo «No. FONACOT»</div>' : ''}
          ${c.tipo === 'pension' && c.pension_beneficiario ? `<div class="cred-info">Beneficiario: ${esc(c.pension_beneficiario)}</div>` : ''}</div>
        <span class="cred-est ${esc(clase)}">${esc(estadoTxt(x, listo))}</span>
      </header>
      <div class="cred-metricas">${metricasHtml(x)}</div>
      ${avisoTxt(x, listo)}
      <div class="cred-acciones">
        ${trans.filter(([e]) => e === 'activo' && c.estado === 'incompleto').map(([e, t]) => `<button type="button" class="cred-sec cred-activar" data-cred-estado="${esc(c.id)}" data-a="${e}">${t}</button>`).join('')}
        ${c.estado !== 'terminado' ? `<button type="button" class="cred-sec" data-cred-editar="${esc(c.id)}">Editar</button>` : ''}
        ${trans.filter(([e]) => !(e === 'activo' && c.estado === 'incompleto')).map(([e, t]) => `<button type="button" class="cred-sec" data-cred-estado="${esc(c.id)}" data-a="${e}">${t}</button>`).join('')}
        <button type="button" class="cred-sec" data-cred-hist="${esc(c.id)}">${ab === 'hist' ? 'Ocultar historia' : 'Historia'}</button>
      </div>
      ${ab && ab.startsWith('estado:') ? `<div class="cred-mini cred-hist" data-mini="${esc(c.id)}">
        <b>${esc(trans.find(t => t[0] === ab.slice(7))?.[1] || '')}</b>
        <label>Fecha efectiva <input type="date" data-est-fecha value="${hoy()}"></label>
        <input type="text" data-est-motivo placeholder="Motivo (obligatorio)" maxlength="300" style="min-width:220px">
        <button type="button" class="cred-sec" data-est-ok="${esc(c.id)}" data-a="${esc(ab.slice(7))}">Confirmar</button>
        <button type="button" class="cred-sec" data-est-no>Cancelar</button></div>` : ''}
      ${ab === 'hist' ? `<div class="cred-hist">
        <b>Historia</b><ul style="margin:6px 0 8px 18px;padding:0">${(x.historia || []).map(h => `<li>${esc(fechaHora(h.creado_en))} · <b>${esc(EVENTOS[h.evento] || h.evento)}</b>${h.fecha_efectiva ? ' (efectiva ' + esc(fecha(h.fecha_efectiva)) + ')' : ''}${h.motivo ? ' — ' + esc(h.motivo) : ''} · ${esc(h.nombre || '')}</li>`).join('')}</ul>
        ${(x.movimientos || []).length ? `<b>Movimientos de saldo</b><ul style="margin:6px 0 0 18px;padding:0">${x.movimientos.map(m => `<li>Periodo ${esc(m.periodo)} · descuento ${esc(dinero(m.importe))}: ${esc(dinero(m.saldo_anterior))} → ${esc(dinero(m.saldo_nuevo))}</li>`).join('')}</ul>` : ''}</div>` : ''}
      ${editando ? formHtml() : ''}
    </article>`;
  }

  // ---- Agrupación contraíble (prototipo) ----
  const GRUPOS = [
    { k: 'prestamos', n: 'Préstamos y anticipos', tipos: ['prestamo', 'anticipo'], ic: '<path d="M3 12h4l3 3h4a2 2 0 0 0 0-4h-3M3 19h11l6-5-2-2-4 3"/><circle cx="16" cy="6" r="3"/>' },
    { k: 'fonacot', n: 'FONACOT', tipos: ['fonacot'], ic: '<rect x="3" y="6" width="18" height="12" rx="2"/><path d="M3 10h18"/>' },
    { k: 'infonavit', n: 'INFONAVIT y pensiones', tipos: ['infonavit', 'pension'], ic: '<path d="M4 11l8-6 8 6v8H4z"/><path d="M10 19v-5h4v5"/>' },
    { k: 'otros', n: 'Otros descuentos', tipos: ['otro'], ic: '<path d="M4 4h7l9 9-7 7-9-9z"/><circle cx="8.5" cy="8.5" r="1.5"/>' },
  ];
  const icono = d => `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
  const IC_TERM = '<path d="M5 21V4h11l-2 4 2 4H5"/>';
  const POR_GRUPO = 6;   // tarjetas visibles por grupo antes de «Mostrar N más»
  const UMBRAL_BUSCAR = 10;

  // Clasificación para el resumen y los filtros (cada crédito en una sola clase).
  function clase(x) {
    const c = x.credito;
    if (c.estado === 'terminado') return 'terminado';
    if (esInformativo(c)) return 'informativo';
    if (c.estado === 'incompleto') return 'pendiente';
    return c.estado === 'suspendido' ? 'suspendido' : 'activo';
  }
  // «Por completar o activar»: SOLO créditos en estado incompleto (les faltan datos o están completos y falta
  // activarlos). No incluye descuentos «por decidir»: esos se deciden en Incidencias → Revisión.
  const CLASES = [['activo', 'activo', 'activos'], ['pendiente', 'por completar o activar', 'por completar o activar'], ['suspendido', 'suspendido', 'suspendidos'], ['informativo', 'informativo NOI', 'informativos NOI'], ['terminado', 'terminado', 'terminados']];

  // Resumen económico de un grupo: solo cantidades comparables.
  // Saldo: suma de saldos (no tiene periodicidad). Propuesto / procesado: solo si todas las
  // líneas son del MISMO periodo; si hay varios periodos, se dice cuántos, sin sumar.
  function resumenGrupo(lista) {
    const partes = [];
    const conSaldo = lista.filter(x => x.saldo != null);
    if (conSaldo.length) partes.push(['Saldo pendiente', dinero(conSaldo.reduce((s, x) => s + Number(x.saldo), 0)), conSaldo.length < lista.length ? `${conSaldo.length} de ${lista.length} con saldo` : '']);
    const desc = lista.filter(x => !esInformativo(x.credito));
    if (!desc.length) return lista.length ? [['', 'Informativo NOI · Sin descuento en BeeHuman', '']] : [];
    // Se suma solo si TODAS las líneas son del mismo periodo y los créditos tienen la misma periodicidad.
    const comp = (titulo, sel, monto) => {
      const ls = desc.map(x => ({ x, l: sel(lineasDe(x.credito)) })).filter(o => o.l);
      if (!ls.length) return;
      const pers = new Set(ls.map(o => o.l.periodo_id || (o.l.periodo.inicio + '|' + o.l.periodo.fin)));
      const perio = new Set(ls.map(o => o.x.credito.periodicidad_id || ''));
      if (pers.size === 1 && perio.size === 1) partes.unshift([titulo + ' · ' + perTxt(ls[0].l.periodo), dinero(ls.reduce((s, o) => s + Number(monto(o.l)), 0)), ls.length > 1 ? `${ls.length} créditos` : '']);
      else partes.unshift([titulo, pers.size > 1 ? `${pers.size} periodos` : 'Periodicidades distintas', 'Sin sumar: ver cada crédito']);
    };
    comp('Procesado', r => r.procesada, l => l.final);
    comp('Propuesto', r => r.propuesta, l => (l.final != null ? l.final : l.sugerido));
    return partes;
  }

  function chipsGrupo(lista) {
    const n = {}; lista.forEach(x => { const c = x.credito, k = esInformativo(c) && c.estado !== 'terminado' ? 'info' : c.estado === 'incompleto' ? (datosCompletos(x) && !esInformativo(c) ? 'listo' : 'falta') : c.estado; n[k] = (n[k] || 0) + 1; });
    return [['listo', 'por activar', 'por activar', 'pendiente'], ['falta', 'incompleto', 'incompletos', 'pendiente'], ['suspendido', 'suspendido', 'suspendidos', 'suspendido'], ['info', 'informativo NOI', 'informativos NOI', 'informativo']]
      .filter(([k]) => n[k]).map(([k, t1, tn, cl]) => `<span class="cred-est ${cl}">${n[k]} ${n[k] === 1 ? t1 : tn}</span>`).join('');
  }

  function grupoHtml(g, lista, abierto, esTerm) {
    const vis = F.verTodo[g.k] ? lista : lista.slice(0, POR_GRUPO);
    const res = esTerm ? [] : resumenGrupo(lista);
    return `<details class="cred-grupo${esTerm ? ' term' : ''}" data-grupo="${g.k}"${abierto ? ' open' : ''}>
      <summary>
        <span class="cred-g-ic">${icono(g.ic)}</span>
        <span class="cred-g-n">${esc(g.n)}</span>
        <span class="cred-g-cnt">${lista.length} registro${lista.length === 1 ? '' : 's'}</span>
        <span class="cred-g-chips">${esTerm ? '' : chipsGrupo(lista)}</span>
        <span class="cred-g-res">${res.map(([t, v, n]) => `<span class="cred-g-m">${t ? `<span class="cred-m-t">${esc(t)}</span>` : ''}<b>${esc(v)}</b>${n ? `<span class="cred-m-n">${esc(n)}</span>` : ''}</span>`).join('')}</span>
        <span class="cred-g-flecha" aria-hidden="true"></span>
      </summary>
      <div class="cred-g-cuerpo">
        <div class="cred-cards">${vis.map(tarjetaHtml).join('')}</div>
        ${lista.length > vis.length ? `<button type="button" class="cred-sec cred-mas" data-ver-todo="${g.k}">Mostrar ${lista.length - vis.length} más</button>` : ''}
      </div>
    </details>`;
  }

  function contenedorScroll(el) {
    for (let e = el.parentElement; e; e = e.parentElement) {
      const o = getComputedStyle(e).overflowY;
      if ((o === 'auto' || o === 'scroll') && e.scrollHeight > e.clientHeight) return e;
    }
    return document.scrollingElement || document.documentElement;
  }

  // Saldo total de préstamos (encabezado de la sección, a la derecha del título).
  // Solo LEE el saldo que entrega la base (cred_saldo_actual) de préstamos y anticipos no terminados,
  // incluidos los suspendidos. No usa importes configurados ni propuestos. Sin préstamos: $0.00.
  function saldoPrestamos(creditos) {
    const vivos = (creditos || []).filter(x => ['prestamo', 'anticipo'].includes(x.credito.tipo) && x.credito.estado !== 'terminado');
    const n = e => vivos.filter(x => x.credito.estado === e).length;
    return { total: vivos.reduce((s, x) => s + (x.saldo != null ? Number(x.saldo) : 0), 0), activos: n('activo'), suspendidos: n('suspendido'), incompletos: n('incompleto'), vivos: vivos.length };
  }
  function pintarSaldoPrestamos(box, mostrar) {
    const sec = box.closest('section'); const h = sec && sec.querySelector(':scope > h3');
    if (!h) return;
    let el = h.querySelector('#cred-saldo-total');
    if (!mostrar) { if (el) el.remove(); h.classList.remove('cred-h3'); return; }
    h.classList.add('cred-h3');
    if (!el) { el = document.createElement('span'); el.id = 'cred-saldo-total'; h.appendChild(el); }
    const r = saldoPrestamos(F.creditos);
    const det = r.vivos ? [[r.activos, 'préstamo activo', 'préstamos activos'], [r.suspendidos, 'suspendido', 'suspendidos'], [r.incompletos, 'incompleto', 'incompletos']]
      .filter(([k]) => k).map(([k, a, b]) => `${k} ${k === 1 ? a : b}`).join(' · ') : 'Sin préstamos vigentes';
    el.dataset.total = r.total.toFixed(2);
    el.innerHTML = `<span class="cred-st-t">Saldo total de préstamos</span><b>${esc(dinero(r.total))}</b><span class="cred-st-n">${esc(det)}</span>`;
  }

  function pintarFicha() {
    const box = $('cred-ficha'); if (!box) return;
    if (F.error) { pintarSaldoPrestamos(box, false); box.innerHTML = `<div class="cred"><div class="cred-msg err">${esc(limpiar(F.error))}</div></div>`; return; }
    pintarSaldoPrestamos(box, true);
    // Conserva la posición del usuario al repintar.
    // Conserva la posición: guarda un elemento visible de referencia (tarjeta o grupo) y, tras repintar,
    // lo devuelve al mismo lugar de la pantalla.
    const sc = contenedorScroll(box); const y = sc.scrollTop;
    sc.style.overflowAnchor = 'none';   // durante el repintado, la posición la repone esta función
    const ancla = (() => {
      const lim = sc === document.scrollingElement || sc === document.documentElement ? 0 : sc.getBoundingClientRect().top;
      const el = [...box.querySelectorAll('#cred-lista [data-cred], #cred-lista details.cred-grupo')].find(e => e.getClientRects().length && e.getBoundingClientRect().bottom > lim + 1);
      return el ? { sel: el.dataset.cred ? `[data-cred="${el.dataset.cred}"]` : `details[data-grupo="${el.dataset.grupo}"]`, top: el.getBoundingClientRect().top } : null;
    })();
    const todos = F.creditos, cuenta = {};
    todos.forEach(x => { const k = clase(x); cuenta[k] = (cuenta[k] || 0) + 1; });
    const q = (F.buscar || '').trim().toLowerCase();
    const pasa = x => (!F.filtro || clase(x) === F.filtro) && (!q || (etiqueta(x.credito) + ' ' + (x.empresa || '')).toLowerCase().includes(q));
    const visibles = todos.filter(pasa);
    const vivos = visibles.filter(x => x.credito.estado !== 'terminado'), term = visibles.filter(x => x.credito.estado === 'terminado');
    const pocos = todos.filter(x => x.credito.estado !== 'terminado').length <= 3;
    const grupos = GRUPOS.map(g => ({ g, lista: vivos.filter(x => g.tipos.includes(x.credito.tipo)) })).filter(o => o.lista.length);
    // Apertura inicial: con 3 o menos créditos vivos, todo abierto; si no, solo grupos con algo por atender.
    // Con filtro o búsqueda activos, se abre todo lo que coincide.
    const editandoId = F.editando && F.editando.credito && F.editando.credito.id;
    const abrir = o => o.lista.some(x => x.credito.id === editandoId) || (F.grupos[o.g.k] != null ? F.grupos[o.g.k] : (pocos || !!F.filtro || !!q || o.lista.some(x => x.credito.estado === 'incompleto') || o.lista.some(x => F.abierto[x.credito.id])));
    const termAbierto = F.grupos.terminados != null ? F.grupos.terminados : (F.filtro === 'terminado' || term.some(x => F.abierto[x.credito.id]));
    box.innerHTML = `<div class="cred">
      <div class="cred-top">
        <div class="cred-resumen" role="group" aria-label="Filtrar créditos">
          <button type="button" class="cred-chip${!F.filtro ? ' on' : ''}" data-filtro=""><b>${todos.length}</b> registros</button>
          ${CLASES.filter(([k]) => cuenta[k]).map(([k, t1, tn]) => `<button type="button" class="cred-chip ${k}${F.filtro === k ? ' on' : ''}" data-filtro="${k}"><b>${cuenta[k]}</b> ${cuenta[k] === 1 ? t1 : tn}</button>`).join('')}
        </div>
        ${F.editando ? '' : '<button type="button" class="primary cred-nuevo" id="cred-nuevo">+ Registrar crédito o descuento</button>'}
      </div>
      ${todos.length >= UMBRAL_BUSCAR ? `<input type="search" id="cred-buscar" class="cred-buscar" placeholder="Buscar por tipo, referencia o empresa" value="${esc(F.buscar || '')}">` : ''}
      <div class="cred-msg" id="cred-msg"></div>
      ${F.editando && !(F.editando.credito && F.editando.credito.id) ? formHtml() : ''}
      ${todos.length ? `<div id="cred-lista" class="cred-lista">
          ${grupos.map(o => grupoHtml(o.g, o.lista, abrir(o), false)).join('')}
          ${term.length ? grupoHtml({ k: 'terminados', n: 'Terminados', ic: IC_TERM }, term, termAbierto, true) : ''}
          ${!visibles.length ? '<p class="hint">Ningún crédito coincide con el filtro.</p>' : ''}
        </div>
        <p class="cred-intro cred-nota">Registrar un crédito no es descontarlo. INFONAVIT y las pensiones porcentuales son informativos para NOI. Los demás proponen un descuento por periodo que Nómina decide en Incidencias → Revisión; el saldo baja solo al procesar el periodo.</p>`
        : '<p class="hint" id="cred-lista-vacia">Sin créditos ni descuentos registrados. Registrar un crédito no es descontarlo.</p>'}
    </div>`;
    box.querySelectorAll('details.cred-grupo').forEach(d => d.addEventListener('toggle', () => { F.grupos[d.dataset.grupo] = d.open; }));
    box.querySelectorAll('[data-filtro]').forEach(b => b.addEventListener('click', () => { F.filtro = b.dataset.filtro || ''; F.grupos = {}; pintarFicha(); }));
    box.querySelectorAll('[data-ver-todo]').forEach(b => b.addEventListener('click', () => { F.verTodo[b.dataset.verTodo] = true; pintarFicha(); }));
    const bq = $('cred-buscar'); if (bq) bq.addEventListener('input', () => { F.buscar = bq.value; F.grupos = {}; const pos = bq.selectionStart; pintarFicha(); const n = $('cred-buscar'); if (n) { n.focus(); n.setSelectionRange(pos, pos); } });
    const reponer = () => {
      sc.scrollTop = y;
      const el = ancla && box.querySelector('#cred-lista ' + ancla.sel);
      if (el && el.getClientRects().length) sc.scrollTop += el.getBoundingClientRect().top - ancla.top;
    };
    reponer(); requestAnimationFrame(() => { reponer(); sc.style.overflowAnchor = ''; });
    bindFicha();
  }

  function formHtml() {
    const ed = F.editando, c = ed.credito || {};
    const t = ed.tipo || c.tipo || 'fonacot', esNuevo = !c.id;
    const v = k => c[k] == null ? '' : c[k];
    const opt = (lst, sel) => lst.map(([k, n]) => `<option value="${esc(k)}" ${String(k) === String(sel) ? 'selected' : ''}>${esc(n)}</option>`).join('');
    const pf = ed.pension_forma || c.pension_forma || 'fijo';
    const mostrar = {
      concepto: t === 'otro', ref: true,
      per: !(t === 'infonavit' || (t === 'pension' && pf === 'porcentaje')),
      imp: !(t === 'infonavit' || (t === 'pension' && pf === 'porcentaje')),
      monto: ['prestamo', 'anticipo', 'fonacot'].includes(t),
      inf: t === 'infonavit', pen: t === 'pension'
    };
    const refLbl = { infonavit: 'Número de crédito INFONAVIT', fonacot: 'Número de crédito FONACOT', pension: 'Oficio o expediente', prestamo: 'Folio (opcional)', anticipo: 'Folio (opcional)', otro: 'Referencia (opcional)' }[t];
    const impLbl = { fonacot: 'Retención por periodo (cédula)', prestamo: 'Descuento por periodo', anticipo: 'Descuento por periodo', pension: 'Importe por periodo', otro: 'Descuento por periodo' }[t];
    return `<div class="cred-form" id="cred-form">
      <b>${esNuevo ? 'Registrar crédito o descuento' : 'Editar ' + esc(etiqueta(c))}</b>
      ${t === 'fonacot' ? '<p class="cred-info">Captura la retención <b>por periodo</b> tal como viene en la cédula; BeeHuman no la prorratea.</p>' : ''}
      ${t === 'infonavit' ? '<p class="cred-info">Se registra para NOI. BeeHuman no calcula el descuento INFONAVIT todavía.</p>' : ''}
      <div class="cred-grid" style="margin-top:10px">
        <div><label for="cred-tipo">Tipo</label><select id="cred-tipo" ${esNuevo ? '' : 'disabled'}>${opt(Object.entries(TIPOS), t)}</select></div>
        <div><label for="cred-rel">Relación laboral (empresa)</label><select id="cred-rel"><option value="">Elige…</option>${F.rels.map(r => `<option value="${esc(r.id)}" ${r.id === c.relacion_laboral_id ? 'selected' : ''}>${esc(relTxt(r))}</option>`).join('')}</select></div>
        ${mostrar.concepto ? `<div><label for="cred-concepto">Concepto</label><input id="cred-concepto" maxlength="120" value="${esc(v('concepto'))}" placeholder="p. ej. Caja de ahorro"></div>` : ''}
        <div><label for="cred-ref">${esc(refLbl)}</label><input id="cred-ref" maxlength="60" value="${esc(v('referencia'))}"></div>
        <div><label for="cred-ini">Inicio</label><input id="cred-ini" type="date" value="${esc(v('fecha_inicio'))}"></div>
        <div><label for="cred-fin">Fin (opcional)</label><input id="cred-fin" type="date" value="${esc(v('fecha_fin'))}"></div>
        ${mostrar.pen ? `<div><label for="cred-pen-forma">Forma</label><select id="cred-pen-forma">${opt([['fijo', 'Monto fijo por periodo'], ['porcentaje', 'Porcentaje (informativo)']], pf)}</select></div>
          ${pf === 'porcentaje' ? `<div><label for="cred-pen-valor">Porcentaje</label><input id="cred-pen-valor" inputmode="decimal" value="${esc(v('pension_valor'))}"></div>` : ''}
          <div><label for="cred-pen-benef">Beneficiario</label><input id="cred-pen-benef" maxlength="120" value="${esc(v('pension_beneficiario'))}"></div>` : ''}
        ${mostrar.inf ? `<div><label for="cred-inf-tipo">Tipo de descuento</label><select id="cred-inf-tipo"><option value="">Elige…</option>${opt(Object.entries(INF_TIPOS), c.infonavit_tipo)}</select></div>
          <div><label for="cred-inf-valor">Valor</label><input id="cred-inf-valor" inputmode="decimal" value="${esc(v('infonavit_valor'))}"></div>
          <div><label for="cred-inf-aviso">Fecha del aviso de retención</label><input id="cred-inf-aviso" type="date" value="${esc(v('infonavit_fecha_aviso'))}"></div>` : ''}
        ${mostrar.per ? `<div><label for="cred-per">Periodicidad</label><select id="cred-per"><option value="">Elige…</option>${opt(F.pers.map(p => [p.id, p.nombre]), c.periodicidad_id)}</select></div>` : ''}
        ${mostrar.imp ? `<div><label for="cred-imp">${esc(impLbl)}</label><input id="cred-imp" inputmode="decimal" value="${esc(v('importe_periodo'))}"></div>` : ''}
        ${mostrar.monto ? `<div><label for="cred-monto">${t === 'fonacot' ? 'Importe total del crédito (opcional)' : 'Monto total'}</label><input id="cred-monto" inputmode="decimal" value="${esc(v('monto_total'))}" ${c.id && (ed.movs || 0) > 0 ? 'disabled' : ''}></div>` : ''}
        <div><label for="cred-notas">Notas (opcional)</label><input id="cred-notas" maxlength="300" value="${esc(v('notas'))}"></div>
        ${esNuevo ? '' : `<div><label for="cred-motivo">Motivo del cambio</label><input id="cred-motivo" maxlength="300" placeholder="Obligatorio; queda en la historia"></div>`}
      </div>
      <div style="margin-top:12px"><button type="button" class="primary" id="cred-guardar">Guardar</button>
        <button type="button" class="primary" id="cred-cancelar" style="background:var(--surface-2,#EEF1F6);color:var(--text,#26324A)">Cancelar</button></div>
    </div>`;
  }

  function leerForm() {
    const g = id => { const el = $(id); return el ? el.value.trim() : undefined; };
    const n = id => { const x = g(id); return x === undefined ? undefined : (x === '' ? null : num(x)); };
    const d = { relacion_laboral_id: g('cred-rel') || null, referencia: g('cred-ref') || null, fecha_inicio: g('cred-ini') || null, fecha_fin: g('cred-fin') || null, notas: g('cred-notas') || null };
    const set = (k, val) => { if (val !== undefined) d[k] = val; };
    set('concepto', g('cred-concepto'));
    set('periodicidad_id', $('cred-per') ? (g('cred-per') || null) : null);
    set('importe_periodo', $('cred-imp') ? n('cred-imp') : null);
    if ($('cred-monto') && !$('cred-monto').disabled) d.monto_total = n('cred-monto');
    if ($('cred-inf-tipo')) { d.infonavit_tipo = g('cred-inf-tipo') || null; d.infonavit_valor = n('cred-inf-valor'); d.infonavit_fecha_aviso = g('cred-inf-aviso') || null; }
    if ($('cred-pen-forma')) { d.pension_forma = g('cred-pen-forma'); d.pension_valor = $('cred-pen-valor') ? n('cred-pen-valor') : null; d.pension_beneficiario = g('cred-pen-benef') || null; }
    for (const k of ['importe_periodo', 'monto_total', 'infonavit_valor', 'pension_valor']) if (d[k] !== undefined && d[k] !== null && !(d[k] > 0)) return { error: 'Los importes y valores deben ser números mayores a cero.' };
    return { d };
  }

  function msgF(tipo, texto) { const m = $('cred-msg'); if (m) { m.className = 'cred-msg ' + tipo; m.textContent = texto; } }

  function bindFicha() {
    const box = $('cred-ficha');
    const bn = $('cred-nuevo'); if (bn) bn.addEventListener('click', () => { F.editando = { tipo: 'fonacot' }; pintarFicha(); });
    const tipoSel = $('cred-tipo');
    if (tipoSel && !tipoSel.disabled) tipoSel.addEventListener('change', () => { F.editando = { tipo: tipoSel.value }; pintarFicha(); });
    const pfSel = $('cred-pen-forma');
    if (pfSel) pfSel.addEventListener('change', () => { F.editando.pension_forma = pfSel.value; const keep = leerForm().d || {}; F.editando.credito = Object.assign({}, F.editando.credito || {}, keep, { pension_forma: pfSel.value }); pintarFicha(); });
    const bc = $('cred-cancelar'); if (bc) bc.addEventListener('click', () => { F.editando = null; pintarFicha(); });
    const bg = $('cred-guardar');
    if (bg) bg.addEventListener('click', async () => {
      const { d, error } = leerForm(); if (error) return msgF('err', error);
      const ed = F.editando, c = ed.credito || {};
      const motivo = $('cred-motivo') ? $('cred-motivo').value.trim() : null;
      if (c.id && !motivo) return msgF('err', 'Escribe el motivo del cambio: queda en la historia.');
      if (!c.id) { d.personal_id = F.personal; d.tipo = ed.tipo || 'fonacot'; }
      bg.disabled = true;
      const r = await sb.rpc('cred_guardar', { p_id: c.id || null, p_datos: d, p_motivo: motivo });
      bg.disabled = false;
      if (r.error) return msgF('err', limpiar(r.error));
      F.editando = null; await cargarFicha(); pintarFicha();
      const tras = c.id ? F.creditos.find(y => y.credito.id === c.id) : null;
      msgF('ok', !c.id ? 'Crédito registrado.'
        : tras && tras.credito.estado === 'incompleto'
          ? (datosCompletos(tras) ? 'Cambio guardado en la historia. Los datos ya están completos: pulsa «Activar» para que empiece a proponer descuentos.'
             : typeof tras.falta_para_activar === 'string' && tras.falta_para_activar ? `Cambio guardado en la historia. Aún faltan datos: ${tras.falta_para_activar}`
             : 'Cambio guardado en la historia.')
          : 'Cambio guardado en la historia.');
    });
    box.querySelectorAll('[data-cred-editar]').forEach(b => b.addEventListener('click', () => {
      const x = F.creditos.find(y => y.credito.id === b.dataset.credEditar);
      F.editando = { credito: x.credito, tipo: x.credito.tipo, pension_forma: x.credito.pension_forma, movs: (x.movimientos || []).length };
      // El formulario se abre dentro de la tarjeta; solo se desplaza si quedó fuera de la pantalla.
      pintarFicha(); const f = $('cred-form'); if (f && f.getBoundingClientRect().top > window.innerHeight - 80) f.scrollIntoView({ block: 'nearest' });
    }));
    box.querySelectorAll('[data-cred-hist]').forEach(b => b.addEventListener('click', () => { const id = b.dataset.credHist; F.abierto = { [id]: F.abierto[id] === 'hist' ? null : 'hist' }; pintarFicha(); }));
    box.querySelectorAll('[data-cred-estado]').forEach(b => b.addEventListener('click', () => { F.abierto = { [b.dataset.credEstado]: 'estado:' + b.dataset.a }; pintarFicha(); }));
    box.querySelectorAll('[data-est-no]').forEach(b => b.addEventListener('click', () => { F.abierto = {}; pintarFicha(); }));
    box.querySelectorAll('[data-est-ok]').forEach(b => b.addEventListener('click', async () => {
      const mini = box.querySelector(`[data-mini="${b.dataset.estOk}"]`);
      const motivo = mini.querySelector('[data-est-motivo]').value.trim(), f = mini.querySelector('[data-est-fecha]').value;
      if (!motivo) return msgF('err', 'Escribe el motivo: queda en la historia.');
      b.disabled = true;
      const r = await sb.rpc('cred_cambiar_estado', { p_id: b.dataset.estOk, p_estado: b.dataset.a, p_fecha: f || null, p_motivo: motivo });
      if (r.error) { b.disabled = false; return msgF('err', limpiar(r.error)); }
      F.abierto = {}; await cargarFicha(); pintarFicha(); msgF('ok', 'Estado actualizado.');
    }));
  }

  // =====================================================================
  // 2. Revisión de Nómina → periodo: «Descuentos del periodo»
  // =====================================================================
  // data: resultado de cred_descuentos_periodo (ya sincronizado).
  window.credPanelPeriodo = function (el, data, recargar) {
    if (!el) return;
    if (!puede() || !data) { el.innerHTML = ''; return; }
    const proc = !!data.procesado;
    const vivas = (data.lineas || []).filter(l => l.origen !== 'descartado');
    const desc = (data.lineas || []).filter(l => l.origen === 'descartado');
    const pend = vivas.filter(l => l.origen === 'pendiente');
    const fila = l => `<tr data-desc="${esc(l.id)}" data-origen="${esc(l.origen)}">
      <td><b>${esc(l.persona)}</b><div class="cred-info">${esc(l.empleado_id || '')}</div></td>
      <td>${esc(etiqueta(l))}${l.detalle && l.detalle.tope_saldo ? '<div class="cred-info">Ajustado al saldo disponible</div>' : ''}</td>
      <td class="n" data-saldo-linea>${l.saldo != null ? esc(dinero(l.saldo)) + (!proc && l.disponible != null && Number(l.disponible) < Number(l.saldo) ? `<div class="cred-info" data-disponible>Disponible ${esc(dinero(Math.max(Number(l.disponible), 0)))}: ${esc(dinero(Number(l.saldo) - Number(l.disponible)))} comprometido en otros periodos abiertos</div>` : '') : '—'}</td>
      <td class="n" data-sugerido>${esc(dinero(l.sugerido))}</td>
      <td class="n">${!proc && l.origen !== 'descartado' ? `<input class="cred-final" data-final="${esc(l.id)}" inputmode="decimal" value="${l.final != null ? esc(l.final) : ''}" placeholder="${esc(l.sugerido ?? '')}" aria-label="Descuento final"><br><input class="cred-motivo" data-motivo="${esc(l.id)}" maxlength="200" placeholder="Motivo si cambias" aria-label="Motivo del ajuste">` : esc(dinero(l.final))}</td>
      <td><span class="cred-est ${esc(l.origen)}">${esc({ pendiente: 'Por decidir', aceptado: 'Aceptado', modificado: 'Modificado', descartado: 'Ya no aplica' }[l.origen])}</span>${(l.ajustes || []).length ? `<div class="cred-info">${l.ajustes.length} ajuste${l.ajustes.length === 1 ? '' : 's'}: ${esc(l.ajustes.map(a => dinero(a.anterior) + ' → ' + dinero(a.nuevo) + ' (' + a.motivo + ')').join('; '))}</div>` : ''}</td>
      <td>${!proc && l.origen !== 'descartado' ? `${l.origen === 'pendiente' ? `<button type="button" class="cred-sec" data-aceptar="${esc(l.id)}">Aceptar</button>` : ''}<button type="button" class="cred-sec" data-guardar="${esc(l.id)}">Guardar</button>` : ''}</td></tr>`;
    el.innerHTML = `<div class="cred" id="cred-panel">
      <h3 class="cred-h">Descuentos del periodo</h3>
      <p class="cred-intro">Créditos con descuento por periodo de las personas de esta empresa. Nacen «por decidir»: acepta o modifica con motivo. El saldo de préstamos y anticipos baja solo al procesar el periodo.</p>
      <div class="cred-msg" id="cred-p-msg"></div>
      ${data.sin_periodicidad ? '<div class="cred-msg err" style="display:block">El periodo no tiene periodicidad: no se proponen descuentos.</div>' : ''}
      ${vivas.length ? `<div class="cred-wrap"><table id="cred-p-lineas"><thead><tr><th>Persona</th><th>Crédito</th><th class="n">Saldo</th><th class="n">Sugerido</th><th class="n">Final</th><th>Estado</th><th></th></tr></thead><tbody>${vivas.map(fila).join('')}</tbody></table></div>`
        : '<p class="hint" id="cred-p-vacio">Sin descuentos de créditos en este periodo.</p>'}
      ${!proc && pend.length ? `<button type="button" class="cred-sec" id="cred-p-aceptar-todos" style="margin-top:8px">Aceptar los ${pend.length} descuento${pend.length === 1 ? '' : 's'} por decidir</button>` : ''}
      ${desc.length ? `<p class="cred-info" style="margin-top:6px">${desc.length} descuento${desc.length === 1 ? '' : 's'} que ya no aplica${desc.length === 1 ? '' : 'n'} (crédito suspendido, terminado o fuera de vigencia); se conservan sin borrar.</p>` : ''}
      ${(data.informativos || []).length ? `<h3 class="cred-h">Créditos informativos (no generan descuento)</h3>
        <div class="cred-wrap"><table id="cred-p-info"><thead><tr><th>Persona</th><th>Crédito</th><th>Datos para NOI</th></tr></thead><tbody>${data.informativos.map(i => `<tr data-info="${esc(i.tipo)}"><td><b>${esc(i.persona)}</b><div class="cred-info">${esc(i.empleado_id || '')}</div></td><td>${esc(etiqueta(i))}${i.estado === 'incompleto' ? ' <span class="cred-est incompleto">Incompleto</span>' : ''}</td>
          <td>${i.tipo === 'infonavit' ? esc((INF_TIPOS[i.infonavit_tipo] || '') + ' ' + (i.infonavit_valor ?? '') + (i.infonavit_fecha_aviso ? ' · aviso ' + fecha(i.infonavit_fecha_aviso) : '')) : i.tipo === 'pension' ? esc(i.pension_valor + ' % del neto') : 'Completa su retención en la ficha para que proponga descuento'}</td></tr>`).join('')}</tbody></table></div>` : ''}
      ${(data.avisos || []).length ? `<div class="cred-msg err" style="display:block" id="cred-p-avisos"><b>Avisos:</b><ul style="margin:4px 0 0 18px;padding:0">${data.avisos.map(a => `<li>${esc(a.persona)} · ${esc(etiqueta(a))}: ${esc(a.aviso)}</li>`).join('')}</ul></div>` : ''}
    </div>`;
    const m = (t, x) => { const e = $('cred-p-msg'); if (e) { e.className = 'cred-msg ' + t; e.textContent = x; } };
    const accion = async (fn, ok) => { const r = await fn(); if (r.error) return m('err', limpiar(r.error)); await recargar(); const e = $('cred-p-msg'); if (e) { e.className = 'cred-msg ok'; e.textContent = ok; } };
    el.querySelectorAll('[data-aceptar]').forEach(b => b.addEventListener('click', () => { b.disabled = true; accion(() => sb.rpc('cred_decidir_descuento', { p_id: b.dataset.aceptar, p_final: null }), 'Descuento aceptado.'); }));
    el.querySelectorAll('[data-guardar]').forEach(b => b.addEventListener('click', () => {
      const l = vivas.find(x => x.id === b.dataset.guardar);
      const v = (el.querySelector(`[data-final="${l.id}"]`) || {}).value || '';
      const mot = ((el.querySelector(`[data-motivo="${l.id}"]`) || {}).value || '').trim();
      if (!v.trim()) return m('err', 'Escribe el descuento final o usa «Aceptar».');
      const n = num(v);
      if (!(n >= 0)) return m('err', 'El descuento debe ser un número.');
      if ((n !== Number(l.sugerido) || l.origen === 'modificado') && !(l.final != null && n === Number(l.final)) && !mot) return m('err', 'Escribe el motivo del ajuste: queda en la bitácora.');
      b.disabled = true; accion(() => sb.rpc('cred_decidir_descuento', { p_id: l.id, p_final: n, p_motivo: mot || null }), 'Descuento guardado.');
    }));
    const bt = $('cred-p-aceptar-todos');
    if (bt) bt.addEventListener('click', () => { bt.disabled = true; accion(() => sb.rpc('cred_aceptar_descuentos', { p_periodo: data.periodo_id }), 'Descuentos aceptados.'); });
  };
})();
