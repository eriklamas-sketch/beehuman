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
  const fechaHoraMx = (t) => { if (!t) return '—'; try { return new Intl.DateTimeFormat('es-MX', { timeZone: 'America/Mexico_City', day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(t)).replace(',', ''); } catch (e) { return fechaMx(t); } };
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
  const IDSE_ESTADO = { pendiente: 'IDSE: pendiente', en_archivo: 'IDSE: archivo generado', presentado: 'IDSE: presentado',
    confirmado: 'IDSE: resultado recibido · aceptado', rechazado: 'IDSE: resultado recibido · rechazado', cancelado: 'IDSE: cancelado' };
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
.hl-filtros{display:flex;gap:8px;flex-wrap:wrap}.hl-filtros select{height:34px;border-radius:9px}
.hl-bitacora{display:flex;flex-direction:column;gap:10px}
.hl-ev{border:1px solid var(--v21-borde,#E5E9F1);border-left:4px solid #C9D2E3;border-radius:12px;padding:12px 14px;background:var(--v21-superficie,#fff)}
.hl-ev.imss{border-left-color:var(--v21-navy,#16264A)}.hl-ev.anulado{opacity:.6}.hl-ev.anulado .hl-ev-tit b{text-decoration:line-through}
.hl-ev-cab{display:flex;gap:14px;align-items:flex-start;flex-wrap:wrap;margin:0 0 8px}
.hl-ev-fecha{font-weight:700;font-size:15px;color:var(--v21-navy,#16264A);min-width:96px}.hl-ev-fecha span{display:block;font-size:11px;font-weight:500;color:var(--v21-texto-2,#5B6680)}
.hl-ev-tit{flex:1;min-width:180px}.hl-ev-donde{font-size:12.5px;color:var(--v21-texto-2,#5B6680);margin-top:2px}
.hl-ev-chips{display:flex;gap:6px;flex-wrap:wrap}
.hl-tabla{width:100%;border-collapse:collapse;font-size:13px;margin:4px 0 8px}
.hl-tabla th,.hl-tabla td{text-align:left;padding:5px 8px;border-bottom:1px solid var(--v21-borde-2,#EEF1F6)}
.hl-tabla thead th{font-size:11.5px;color:var(--v21-texto-2,#5B6680);font-weight:600;background:var(--v21-fondo,#F6F8FB)}
.hl-tabla tbody th{font-weight:600;color:var(--v21-texto,#16264A);width:32%}
.hl-nr{color:#8A94A8;font-style:italic}
.hl-link{font-weight:600}
.rl-internos{margin:18px 0 8px;font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--v21-texto-2,#5B6680)}
.sbc-card{margin-top:14px;background:var(--surface-2,#F6F8FB)}
.sbc-rel{border-top:1px solid var(--v21-borde,#E5E9F1);padding:10px 0}
.sbc-fila{display:flex;gap:8px 18px;flex-wrap:wrap;align-items:center}
.sbc-resumen{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin:8px 0}
.sbc-resumen>div{border:1px solid var(--v21-borde,#E5E9F1);border-radius:10px;padding:8px 10px;background:#fff}
.sbc-resumen span{display:block;font-size:11.5px;color:var(--v21-texto-2,#5B6680)}.sbc-resumen b{font-size:15px}
.sbc-resumen small{display:block;font-size:11.5px;color:#8A6400;margin-top:3px}
.sbc-av{margin:6px 0;padding:8px 10px;border-radius:9px;background:#FFF8E6;color:#6B4E00;font-size:13px}
.sbc-av.err{background:#FDECEA;color:#B42318}.sbc-av.ok{background:#EAF6EE;color:#1E6B3A}
.sbc-pend-arch{display:inline-block;margin:2px 0;padding:1px 8px;border-radius:999px;background:#FFF3D6;color:#8A6400;font-weight:600}.sbc-av .hl-btn2{margin-left:8px}
.hl-aviso-sueldo{margin:6px 0;padding:8px 10px;border-radius:9px;background:#EAF0FB;color:#24427A;font-size:13px}
@media (max-width:640px){.hl-card{padding:12px}.hl-grid{grid-template-columns:1fr}.hl-ev-cab{gap:6px}}
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
    estado = { personaId: p.id, persona: p, relaciones: [], eventos: [], pendientes: [], esquemas: [], formAbierto: null };
    bloquearFicha(false);
    raiz.innerHTML = '<p class="hint">Cargando historia laboral…</p>';
    asegurarContenedores();
    ['rl-raiz', 'sbc-raiz'].forEach((k) => { const c = document.getElementById(k); if (c) c.innerHTML = '<p class="hint">Cargando relación laboral…</p>'; });
    if (!causas.length || !rps.length) await cargarCatalogos();
    const id = p.id;
    const [rel, hist, pend] = await Promise.all([
      sb.from('relaciones_laborales').select('*').eq('personal_id', id),
      sb.rpc('laboral_historial', { p_personal_id: id }),
      sb.from('personal_registros_pago').select('id,sueldo,modalidad_sueldo,empresa_id,registro_patronal_id,clasificacion_id,fecha_inicio,relacion_laboral_id')
        .eq('personal_id', id).eq('activo', true),
    ]);
    if (estado.personaId !== id) return; // se abrió otra ficha mientras cargaba
    if (rel.error || hist.error) {
      raiz.innerHTML = `<div class="hl-msg err">No se pudo cargar la historia laboral: ${esc(msgError(rel.error || hist.error))}</div>`;
      return;
    }
    estado.relaciones = (rel.data || []).filter((r) => r.estado !== 'anulada');
    estado.eventos = hist.data || [];
    estado.esquemas = pend.error ? [] : (pend.data || []);
    estado.pendientes = estado.esquemas.filter((e) => !e.relacion_laboral_id);
    bloquearFicha(estado.relaciones.length > 0);
    pintar();
    msgPendiente = null; // un aviso solo se muestra en la ficha que lo generó, una vez
  }

  // Con historial, estos datos solo cambian desde aquí (la base lo exige).
  function bloquearFicha(si) {
    fichaBloqueadaPara = si ? estado.personaId : null;
    ['d-empresa', 'd-registro-patronal', 'd-numero-interno', 'd-fechabaja', 'd-comentariobaja'].forEach((idc) => {
      const el = document.getElementById(idc); if (!el) return;
      el.disabled = si; el.title = si ? 'Se registra en Relación laboral' : '';
    });
    const est = document.getElementById('d-estatus');
    if (est) {
      const enBaja = est.value === 'Baja';
      est.disabled = si && enBaja;
      [...est.options].forEach((o) => { if (o.value === 'Baja' || o.text === 'Baja') o.disabled = si && !enBaja; });
      est.title = si ? 'Las bajas se registran en Relación laboral' : '';
    }
    let aviso = document.getElementById('hl-aviso-ficha');
    const ancla = document.getElementById('d-empresa');
    if (si && ancla && !aviso) {
      aviso = document.createElement('p'); aviso.id = 'hl-aviso-ficha'; aviso.className = 'hl-bloqueado';
      aviso.innerHTML = 'Empresa, registro patronal, número interno y bajas se registran en <a href="#" onclick="cambiarSeccionDetalle(\'laboral\');return false;">Relación laboral</a>.';
      ancla.closest('.grid3, .grid2, div').parentNode.appendChild(aviso);
    }
    if (aviso) aviso.style.display = si ? 'block' : 'none';
  }

  // ---------- contenedores en la ficha ----------
  // Historia laboral (08) = bitácora de solo lectura.
  // Relación laboral (03) = gestión: ingreso, baja, corrección.
  // Compensación (04) = salario ante el IMSS (SBC) y su modificación (07).
  function asegurarContenedores() {
    const secL = document.querySelector('[data-detail-section="laboral"]');
    if (secL && !document.getElementById('rl-raiz')) {
      const d = document.createElement('div'); d.id = 'rl-raiz';
      const h3 = secL.querySelector('h3'); h3.insertAdjacentElement('afterend', d);
      const t = document.createElement('h4'); t.className = 'rl-internos'; t.textContent = 'Datos internos de la ficha';
      d.insertAdjacentElement('afterend', t);
      const lj = document.getElementById('d-jornada');
      const lab = lj && lj.closest('div') ? lj.closest('div').querySelector('label') : null;
      if (lab) lab.textContent = 'Jornada (descripción interna)';
    }
    const comp = document.getElementById('rp-componente');
    if (comp && !document.getElementById('sbc-raiz')) {
      const d = document.createElement('div'); d.id = 'sbc-raiz'; comp.insertAdjacentElement('afterend', d);
    }
  }
  const rpDe = (relId) => textoRP((estado.relaciones.find((r) => r.id === relId) || {}).registro_patronal_id);
  const enlaceBandeja = (rpId, texto) => rpId
    ? ` <a href="#" class="hl-link" onclick="BH_laboral.irABandeja('${esc(rpId)}');return false;">${esc(texto || 'Ver en la bandeja IDSE de ' + (textoRP(rpId) || 'este registro patronal'))}</a>` : '';

  function pintar() {
    asegurarContenedores();
    pintarBitacora();
    pintarRelaciones();
    pintarSbc();
    if (msgPendiente && msgPendiente.personaId === estado.personaId) mensaje(msgPendiente.texto, true, msgPendiente.html, msgPendiente.destino);
    msgPendiente = null;
  }

  // ---------- 08 Historia laboral: bitácora ----------
  const FILTROS = { todo: 'Todos los acontecimientos', imss: 'Movimientos ante el IMSS', comp: 'Compensación y salario',
    org: 'Organización', corr: 'Correcciones' };
  const enFiltro = (tipo, f) => f === 'todo' || (f === 'imss' && TIPOS_IMSS.includes(tipo))
    || (f === 'comp' && ['cambio_esquema_pago', 'modificacion_salario'].includes(tipo))
    || (f === 'org' && ['cambio_puesto', 'cambio_jefe', 'cambio_organizacion', 'cambio_empresa', 'cambio_registro_patronal'].includes(tipo))
    || (f === 'corr' && tipo === 'correccion_datos');
  let vista = { filtro: 'todo', recientes: true };

  function pintarBitacora() {
    const raiz = document.getElementById('hl-raiz');
    if (!raiz) return;
    // Sin fecha efectiva (datos migrados) van siempre al final, con cualquier orden.
    const evs = estado.eventos.filter((e) => enFiltro(e.tipo, vista.filtro)).sort((a, b) =>
      (!a.fecha_efectiva) - (!b.fecha_efectiva)
      || (vista.recientes ? -1 : 1) * (String(a.fecha_efectiva).localeCompare(String(b.fecha_efectiva)) || String(a.registrado_en).localeCompare(String(b.registrado_en))));
    const varias = new Set(estado.eventos.map((e) => e.relacion_id)).size > 1;
    let h = `<div class="hl-wrap"><div class="hl-cab"><h3>Historia laboral</h3>
      <div class="hl-filtros"><select id="hl-filtro" aria-label="Filtrar acontecimientos">${Object.entries(FILTROS).map(([k, t]) => `<option value="${k}" ${k === vista.filtro ? 'selected' : ''}>${t}</option>`).join('')}</select>
      <button type="button" class="hl-btn2" id="hl-orden">${vista.recientes ? 'Más recientes primero ⇅' : 'Más antiguos primero ⇅'}</button></div></div>
      <p class="hint" style="margin:0 0 10px">Solo consulta. Ingresos, reingresos, bajas, correcciones y la anulación del último movimiento se registran en <a href="#" onclick="cambiarSeccionDetalle('laboral');return false;">Relación laboral</a>; los esquemas de pago y la modificación de salario (SBC), en <a href="#" onclick="cambiarSeccionDetalle('compensacion');return false;">Compensación</a>.${varias ? ' Esta persona tiene más de una relación laboral: cada acontecimiento indica su empresa y registro patronal.' : ''}</p>
      <div class="hl-msg" id="hl-msg"></div>`;
    if (!estado.eventos.length) h += '<p class="hint">Todavía no hay acontecimientos registrados.</p>';
    else if (!evs.length) h += '<p class="hint">No hay acontecimientos de este tipo.</p>';
    h += '<div class="hl-bitacora">';
    evs.forEach((e) => {
      const claves = [...new Set([...Object.keys(e.valores_anteriores || {}), ...Object.keys(e.valores_nuevos || {})])].filter((k) => !OCULTAR.includes(k));
      const filas = claves.map((k) => {
        const a = (e.valores_anteriores || {})[k], n = (e.valores_nuevos || {})[k];
        const vacio = (v) => v === undefined || v === null || v === '';
        return `<tr><th scope="row">${esc(ETIQUETAS[k] || k)}</th><td>${vacio(a) ? '<span class="hl-nr">No registrado</span>' : esc(valorLegible(k, a))}</td><td>${vacio(n) ? '<span class="hl-nr">Sin dato</span>' : esc(valorLegible(k, n))}</td></tr>`;
      }).join('');
      const rel = estado.relaciones.find((r) => r.id === e.relacion_id) || {};
      const quien = e.origen === 'migracion' ? 'Migración inicial' : (e.registrado_por === 'sistema' ? 'Sistema' : e.registrado_por || '—');
      h += `<article class="hl-ev ${TIPOS_IMSS.includes(e.tipo) ? 'imss' : ''} ${e.estado}" data-evento="${esc(e.evento_id)}">
        <div class="hl-ev-cab"><div class="hl-ev-fecha">${e.fecha_efectiva ? fechaMx(e.fecha_efectiva) : 'Sin fecha'}<span>${e.fecha_efectiva ? 'fecha efectiva' : 'dato migrado'}</span></div>
          <div class="hl-ev-tit"><b>${esc(TIPOS[e.tipo] || e.tipo)}</b>
            <div class="hl-ev-donde">${esc(e.empresa || '—')} · ${e.registro_patronal ? 'RP ' + esc(e.registro_patronal) : 'sin registro patronal'}</div></div>
          <div class="hl-ev-chips">${e.idse_estado ? `<span class="hl-chip idse ${e.idse_estado}">${esc(IDSE_ESTADO[e.idse_estado] || e.idse_estado)}</span>` : ''}
            ${e.estado === 'anulado' ? '<span class="hl-chip">Anulado</span>' : ''}${e.origen === 'migracion' ? '<span class="hl-chip">Migración inicial</span>' : ''}</div></div>
        ${filas ? `<table class="hl-tabla"><thead><tr><th>Dato</th><th>Anterior</th><th>Nuevo</th></tr></thead><tbody>${filas}</tbody></table>` : ''}
        ${e.causa_descripcion ? `<div class="hl-meta">Causa: ${esc(e.causa_descripcion)}</div>` : ''}
        ${e.motivo ? `<div class="hl-meta">Motivo: ${esc(e.motivo)}</div>` : ''}
        <div class="hl-meta">Registrado por ${esc(quien)} el ${fechaHoraMx(e.registrado_en)}${e.idse_estado && rel.registro_patronal_id && puedeOperar() ? ' ·' + enlaceBandeja(rel.registro_patronal_id, 'Ver en la bandeja IDSE') : ''}</div>
      </article>`;
    });
    h += '</div></div>';
    raiz.innerHTML = h;
    document.getElementById('hl-filtro').onchange = (ev) => { vista.filtro = ev.target.value; pintarBitacora(); };
    document.getElementById('hl-orden').onclick = () => { vista.recientes = !vista.recientes; pintarBitacora(); };
  }

  function ultimoAnulable(relId) {
    const evs = estado.eventos.filter((e) => e.relacion_id === relId && e.estado === 'vigente' && TIPOS_IMSS.includes(e.tipo))
      .sort((a, b) => String(b.registrado_en).localeCompare(String(a.registrado_en)));
    const u = evs[0];
    if (!u || u.origen === 'migracion') return null;
    if (u.idse_estado && !['pendiente', 'rechazado', 'cancelado'].includes(u.idse_estado)) return null;
    return u.evento_id;
  }

  // ---------- 03 Relación laboral: gestión ----------
  function pintarRelaciones() {
    const raiz = document.getElementById('rl-raiz');
    if (!raiz) return;
    const rels = [...estado.relaciones].sort((a, b) => (a.estado === 'vigente' ? 0 : 1) - (b.estado === 'vigente' ? 0 : 1)
      || String(b.fecha_ingreso || '').localeCompare(String(a.fecha_ingreso || '')));
    let h = `<div class="hl-wrap"><div class="hl-cab"><h4 style="margin:0">Relaciones laborales</h4>
      ${puedeOperar() ? '<button type="button" class="primary" style="margin:0" id="hl-btn-ingreso">Registrar ingreso o reingreso</button>' : ''}</div>
      <div class="hl-msg" id="rl-msg"></div><div id="hl-form-ingreso"></div>`;
    if (estado.pendientes.length && puedeOperar()) {
      const vig = rels.filter((r) => r.estado === 'vigente');
      h += `<div class="hl-pend"><b>Esquemas de pago sin relación laboral</b>
        <p class="hint" style="margin:4px 0 8px">La base no los asignó porque hay más de una relación posible. Elige a cuál pertenece cada uno.</p>`;
      estado.pendientes.forEach((e) => {
        const comp = vig.filter((r) => !e.empresa_id || r.empresa_id === e.empresa_id);
        h += `<div class="hl-grid" style="margin:6px 0"><div><label>Esquema</label><div>${dinero(e.sueldo)} ${esc(e.modalidad_sueldo || '')} · ${esc(e.empresa_id ? nombreEmpresa(e.empresa_id) : 'sin empresa')} · desde ${fechaMx(e.fecha_inicio)}</div></div>
          <div><label>Relación laboral (empresa · registro patronal · ingreso)</label><select id="hl-pend-${e.id}"><option value="">Elige…</option>${comp.map((r) =>
            `<option value="${r.id}">${esc(nombreEmpresa(r.empresa_id))} · ${esc(textoRP(r.registro_patronal_id) ? 'RP ' + textoRP(r.registro_patronal_id) : 'Sin registro patronal')} · ingreso ${fechaMx(r.fecha_ingreso)}</option>`).join('')}</select></div>
          <div><button type="button" class="hl-btn2" data-asignar="${e.id}">Asignar</button></div></div>`;
      });
      h += '</div>';
    }
    if (!rels.length) h += `<p class="hint">Esta persona todavía no tiene relaciones laborales registradas.${puedeOperar() ? ' Usa «Registrar ingreso o reingreso».' : ''}</p>`;
    rels.forEach((r) => {
      const rpTxt = textoRP(r.registro_patronal_id);
      h += `<div class="hl-card ${r.estado}" data-relacion="${r.id}"><h4>${esc(nombreEmpresa(r.empresa_id))} · ${esc(rpTxt ? 'RP ' + rpTxt : 'Sin registro patronal (sin IDSE)')}
        <span class="hl-chip ${r.estado}">${r.estado === 'vigente' ? 'Vigente' : 'Baja'}</span>
        ${(r.pendientes_migracion || []).map((p) => `<span class="hl-chip aviso">${esc(PENDIENTE[p] || p)}</span>`).join('')}</h4>
        <div class="hl-datos"><span>Ingreso <b>${fechaMx(r.fecha_ingreso)}</b></span>
          <span>Antigüedad reconocida <b>${fechaMx(r.fecha_reconocimiento_antiguedad)}</b></span>
          ${r.estado === 'baja' ? `<span>Baja <b>${fechaMx(r.fecha_baja)}</b>${r.causa_baja ? ' · ' + esc(valorLegible('causa_baja', r.causa_baja)) : ''}</span>` : ''}
          ${rpTxt ? `<span>SBC <b>${r.sbc == null ? 'No registrado' : dinero(r.sbc)}</b></span><span>Tipo <b>${esc(valorLegible('tipo_trabajador', r.tipo_trabajador))}</b></span>
          <span>Salario <b>${esc(valorLegible('tipo_salario', r.tipo_salario))}</b></span><span>Jornada IMSS <b>${esc(valorLegible('jornada', r.jornada))}</b></span>
          <span>UMF <b>${esc(r.umf || '—')}</b></span>` : ''}<span>Número interno <b>${esc(r.numero_interno || '—')}</b></span></div>`;
      if (puedeOperar()) {
        // Anulación: solo el último movimiento IMSS de esta relación que todavía no
        // se presentó (la regla vive en la base: laboral_anular_evento).
        const anu = estado.eventos.find((e) => e.evento_id === ultimoAnulable(r.id));
        h += '<div class="hl-acc">';
        if (r.estado === 'vigente') h += `<button type="button" class="hl-btn2" data-accion="baja" data-rel="${r.id}">Dar de baja</button>`;
        h += `<button type="button" class="hl-btn2" data-accion="corregir" data-rel="${r.id}">Corregir datos</button>`;
        if (anu) h += `<button type="button" class="hl-btn2 peligro" data-anular="${anu.evento_id}" data-rel="${r.id}">Anular último movimiento: ${esc(TIPOS[anu.tipo] || anu.tipo)} del ${fechaMx(anu.fecha_efectiva)}</button>`;
        h += `</div><div id="hl-form-${r.id}"></div>`;
      }
      h += '</div>';
    });
    raiz.innerHTML = h + '</div>';
    const bi = document.getElementById('hl-btn-ingreso');
    if (bi) bi.onclick = () => formIngreso();
    raiz.querySelectorAll('[data-accion]').forEach((b) => { b.onclick = () => ({ baja: formBaja, corregir: formCorregir })[b.dataset.accion](b.dataset.rel); });
    raiz.querySelectorAll('[data-anular]').forEach((b) => { b.onclick = () => formAnular(b.dataset.anular, b.dataset.rel); });
    raiz.querySelectorAll('[data-asignar]').forEach((b) => {
      b.onclick = async () => {
        const sel = document.getElementById('hl-pend-' + b.dataset.asignar);
        if (!sel.value) { mensaje('Elige la relación del esquema.', false, null, 'rl-msg'); return; }
        const r = estado.relaciones.find((x) => x.id === sel.value) || {};
        const destino = `${nombreEmpresa(r.empresa_id)} · ${textoRP(r.registro_patronal_id) ? 'RP ' + textoRP(r.registro_patronal_id) : 'sin registro patronal'}`;
        // Confirmación explícita: con varias relaciones posibles no se adivina.
        if (!confirm(`¿Asignar este esquema de pago a la relación ${destino}?\n\nSus cambios de sueldo y la modificación de salario (07) que ofrezca BeeHuman se referirán a esa relación.`)) return;
        const { error } = await sb.from('personal_registros_pago').update({ relacion_laboral_id: sel.value }).eq('id', b.dataset.asignar);
        if (error) { mensaje(msgError(error), false, null, 'rl-msg'); return; }
        await alAbrirDetalle(detalleActual); mensaje(`Esquema asignado a la relación ${destino}.`, true, null, 'rl-msg');
      };
    });
  }

  // ---------- 04 Compensación: salario ante el IMSS (SBC) ----------
  // El SBC NO se calcula ni se actualiza desde el sueldo: la modificación (07)
  // es una operación explícita e independiente (decisión de Erik, 7-nov).
  function sbcDesde(relId) {
    const e = estado.eventos.filter((x) => x.relacion_id === relId && x.estado === 'vigente' && ['ingreso', 'reingreso', 'modificacion_salario'].includes(x.tipo)
      && x.valores_nuevos && x.valores_nuevos.sbc !== undefined).sort((a, b) => String(b.fecha_efectiva).localeCompare(String(a.fecha_efectiva)))[0];
    return e ? e.fecha_efectiva : null;
  }
  function pintarSbc() {
    const raiz = document.getElementById('sbc-raiz');
    if (!raiz) return;
    if (!puedeOperar()) { raiz.innerHTML = ''; return; }
    const vig = estado.relaciones.filter((r) => r.estado === 'vigente');
    let h = `<div class="card sbc-card"><div class="hl-cab"><h4 style="margin:0">Salario ante el IMSS (SBC)</h4></div>
      <p class="hint" style="margin:0 0 8px"><b>SBC</b> = salario base de cotización diario ante el IMSS. No es el sueldo de los esquemas de pago:
      cambiar el sueldo no cambia el SBC. Si el SBC cambia, se registra aquí y genera la modificación de salario (07) pendiente en la bandeja IDSE.</p>
      <div class="hl-msg" id="sbc-msg"></div>`;
    if (!vig.length) h += '<p class="hint">Sin relación laboral vigente.</p>';
    if (estado.pendientes.length) {
      h += `<div class="sbc-av">${estado.pendientes.length === 1 ? 'Un esquema de pago no tiene' : estado.pendientes.length + ' esquemas de pago no tienen'} relación laboral asignada.
        Asígnalo en <a href="#" onclick="cambiarSeccionDetalle('laboral');return false;">Relación laboral</a> antes de registrar una modificación de salario por su cambio de sueldo.</div>`;
    }
    const varias = vig.filter((r) => r.registro_patronal_id).length > 1;
    vig.forEach((r) => {
      const rpTxt = textoRP(r.registro_patronal_id);
      const desde = sbcDesde(r.id);
      h += `<div class="sbc-rel" data-sbc-rel="${r.id}"><div class="sbc-fila"><div><b>${esc(nombreEmpresa(r.empresa_id))}</b> · ${rpTxt ? 'RP ' + esc(rpTxt) : 'sin registro patronal'}</div>`;
      if (!rpTxt) {
        h += '<div class="hint">Sin registro patronal: no presenta movimientos ante el IMSS.</div></div></div>';
        return;
      }
      h += `<div>SBC vigente registrado: <b>${r.sbc == null ? 'No registrado' : dinero(r.sbc) + ' diario'}</b>${r.sbc != null && desde ? ` <span class="hl-meta">(desde ${fechaMx(desde)})</span>` : ''}</div>
        <div>Tope de cotización hoy: <b class="sbc-tope-hoy" data-rel="${r.id}">…</b></div>
        <button type="button" class="hl-btn2" data-sbc="${r.id}">Registrar modificación de salario (07)</button></div>
        <div class="hl-meta">Esquemas de pago de esta relación: ${(() => { const es = estado.esquemas.filter((e) => e.relacion_laboral_id === r.id);
          return es.length ? es.map((e) => `${esc(dinero(e.sueldo))} ${esc(e.modalidad_sueldo || '')}`).join(' · ') : 'ninguno'; })()}</div>
        <div id="sbc-form-${r.id}"></div></div>`;
    });
    raiz.innerHTML = h + '</div>';
    raiz.querySelectorAll('[data-sbc]').forEach((b) => { b.onclick = () => formSalario(b.dataset.sbc); });
    raiz.querySelectorAll('.sbc-tope-hoy').forEach(async (el) => {
      const t = await topeEn(hoyMexico(), el.dataset.rel);
      el.textContent = t.tope == null ? 'sin UMA registrada' : `${dinero(t.tope)} diario (25 UMA × ${dinero(t.uma)})`;
    });
  }
  // Tope (25 UMA) y salario mínimo de la zona del RP a una fecha.
  const cacheParam = {};
  async function parametro(clave, fecha) {
    const k = clave + '|' + fecha;
    if (!(k in cacheParam)) {
      const { data, error } = await sb.rpc('parametro_vigente', { p_clave: clave, p_fecha: fecha });
      cacheParam[k] = error || data == null ? null : Number(data);
    }
    return cacheParam[k];
  }
  async function topeEn(fecha, relId) {
    const r = estado.relaciones.find((x) => x.id === relId) || {};
    const rp = rps.find((x) => x.id === r.registro_patronal_id) || {};
    const zlfn = rp.zona_salario_minimo === 'zlfn';
    const [uma, sm] = await Promise.all([parametro('UMA_DIARIA', fecha), parametro(zlfn ? 'SALARIO_MINIMO_ZLFN' : 'SALARIO_MINIMO_GENERAL', fecha)]);
    return { uma, sm, zlfn, tope: uma == null ? null : Math.round(uma * 25 * 100) / 100 };
  }
  // Importes: se escriben con separador de miles y se guardan como número.
  const leerImporte = (t) => { const v = String(t || '').replace(/[$,\s]/g, ''); return v === '' ? null : (/^\d+(\.\d{1,2})?$/.test(v) ? Number(v) : NaN); };
  const formatoImporte = (n) => Number(n).toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  // Separador de miles mientras se escribe (máx. 2 decimales). El valor real se
  // obtiene con leerImporte(): siempre un número, nunca el texto con comas.
  function formatearAlEscribir(el) {
    const antes = el.value, pos = el.selectionStart == null ? antes.length : el.selectionStart;
    const digitosAntes = antes.slice(0, pos).replace(/[^\d.]/g, '').length;
    let limpio = antes.replace(/[^\d.]/g, '');
    const punto = limpio.indexOf('.');
    if (punto >= 0) limpio = limpio.slice(0, punto + 1) + limpio.slice(punto + 1).replace(/\./g, '').slice(0, 2);
    let [ent, dec] = limpio.split('.');
    ent = ent.replace(/^0+(?=\d)/, '');
    const conComas = ent.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    const nuevo = dec !== undefined ? `${conComas}.${dec}` : conComas;
    if (nuevo === antes) return;
    el.value = nuevo;
    let n = 0, i = 0;                       // conserva el cursor después del mismo dígito
    while (i < nuevo.length && n < digitosAntes) { if (/[\d.]/.test(nuevo[i])) n++; i++; }
    try { el.setSelectionRange(i, i); } catch (e) { /* ignore */ }
  }
  // destino: hl-msg (bitácora), rl-msg (relación laboral) o sbc-msg (Compensación)
  function mensaje(texto, ok, html, destino) {
    const m = document.getElementById(destino || 'hl-msg'); if (!m) return;
    if (html) m.innerHTML = html; else m.textContent = texto;
    m.className = 'hl-msg ' + (ok ? 'ok' : 'err');
    if (ok && destino) m.scrollIntoView({ block: 'nearest' });
  }

  // Ejecuta una función de la base y vuelve a abrir la ficha en la sección indicada.
  async function ejecutar(fn, args, ok, seccion, destino) {
    const { error } = await sb.rpc(fn, args);
    if (error) { mensaje(msgError(error), false, null, destino); return { error }; }
    const id = estado.personaId;
    msgPendiente = typeof ok === 'string' ? { texto: ok, destino, personaId: id } : { ...ok, destino, personaId: id };
    if (typeof cargarPersonal === 'function') await cargarPersonal();
    // Se vuelve a abrir la ficha para que sus campos reflejen lo que dejó la base.
    if (typeof abrirDetalle === 'function') await abrirDetalle(id, seccion || 'historia');
    return { ok: true };
  }

  // Los avisos de resultado no persisten: se borran al cambiar de sección o de ficha.
  function limpiarAvisos() {
    ['hl-msg', 'rl-msg', 'sbc-msg'].forEach((k) => { const m = document.getElementById(k); if (m) { m.innerHTML = ''; m.className = 'hl-msg'; } });
  }
  document.addEventListener('click', (ev) => { if (ev.target.closest && ev.target.closest('[data-detail-tab]')) limpiarAvisos(); }, true);

  function cerrarForms() {
    document.querySelectorAll('#rl-raiz [id^="hl-form-"], #sbc-raiz [id^="sbc-form-"]').forEach((d) => { d.innerHTML = ''; });
  }
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
      if (!val(f, 'empresa') || !val(f, 'fecha')) { mensaje('Indica empresa y fecha de ingreso.', false, null, 'rl-msg'); return; }
      await ejecutar('laboral_registrar_ingreso', {
        p_personal_id: estado.personaId, p_empresa_id: val(f, 'empresa'), p_registro_patronal_id: val(f, 'rp') || null,
        p_fecha_ingreso: val(f, 'fecha'), p_fecha_reconocimiento_antiguedad: val(f, 'antig') || null,
        p_sbc: num(f, 'sbc'), p_sdi: num(f, 'sdi'), p_tipo_trabajador: val(f, 'tt') || null, p_tipo_salario: val(f, 'ts') || null,
        p_jornada: val(f, 'jo') || null, p_umf: val(f, 'umf') || null, p_numero_interno: val(f, 'num') || null, p_motivo: val(f, 'motivo') || null,
      }, val(f, 'rp')
        ? { html: `<b>Ingreso registrado.</b> El alta (08) quedó <b>pendiente</b> en la bandeja IDSE del registro patronal <b>${esc(textoRP(val(f, 'rp')))}</b>.${enlaceBandeja(val(f, 'rp'))}` }
        : 'Ingreso registrado. Sin registro patronal: no genera movimiento IDSE.', 'laboral', 'rl-msg');
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
    const rpId = (estado.relaciones.find((r) => r.id === relId) || {}).registro_patronal_id;
    montar('hl-form-' + relId, `<b>Dar de baja esta relación</b>
      <p class="hint" style="margin:4px 0 8px">Se desactivan sus esquemas de pago. ${rpId ? `Queda la baja (02) pendiente en la bandeja IDSE del registro patronal ${esc(textoRP(rpId))}; el archivo se genera desde la bandeja cuando lo decidas.` : 'Sin registro patronal: no genera movimiento IDSE.'}</p>
      <div class="hl-grid"><div><label>Fecha de baja</label><input name="fecha" type="date" required></div>
        <div><label>Causa (IMSS)</label><select name="causa" required><option value="">Elige…</option>${causas.map((c) => `<option value="${esc(c.codigo)}">${esc(c.codigo)} · ${esc(c.descripcion)}</option>`).join('')}</select></div>
        <div><label>Comentario (opcional)</label><input name="motivo"></div></div>${botones('Registrar baja')}`, async (f) => {
      const html = rpId
        ? `<b>Baja registrada.</b> El movimiento de baja (02) quedó <b>pendiente</b> en la bandeja IDSE del registro patronal <b>${esc(textoRP(rpId))}</b>. El archivo se genera desde la bandeja cuando lo decidas.${enlaceBandeja(rpId)}`
        : '<b>Baja registrada.</b> Esta relación no tiene registro patronal: no genera movimiento IDSE.';
      await ejecutar('laboral_registrar_baja', { p_relacion_id: relId, p_fecha_baja: val(f, 'fecha') || null, p_causa: val(f, 'causa') || null, p_motivo: val(f, 'motivo') || null },
        { html }, 'laboral', 'rl-msg');
    });
  }

  // Modificación de salario (07) desde Compensación. Captura SBC (y SDI aparte);
  // el sueldo de los esquemas de pago no interviene.
  const FACTOR_MINIMO = 1.0493; // integración mínima de ley (15 días de aguinaldo, 12 de vacaciones, 25 % de prima)
  function formSalario(relId, avisoSueldo) {
    const r = estado.relaciones.find((x) => x.id === relId) || {};
    const rpId = r.registro_patronal_id;
    const vigente = r.sbc == null ? null : Number(r.sbc);
    const otras = estado.relaciones.filter((x) => x.estado === 'vigente' && x.registro_patronal_id && x.id !== relId).length;
    montar('sbc-form-' + relId, `<b>Modificación de salario (07) · ${esc(nombreEmpresa(r.empresa_id))} · RP ${esc(textoRP(rpId) || '')}</b>
      ${otras ? `<p class="hl-aviso-sueldo">Esta persona tiene ${otras + 1} relaciones vigentes con registro patronal. El movimiento se registrará <b>solo</b> para ${esc(nombreEmpresa(r.empresa_id))} · RP ${esc(textoRP(rpId))} (ingreso ${fechaMx(r.fecha_ingreso)}).</p>` : ''}
      ${avisoSueldo ? `<p class="hl-aviso-sueldo">${esc(avisoSueldo)}</p>` : ''}
      <div class="sbc-resumen">
        <div><span>SBC vigente registrado</span><b>${vigente == null ? 'No registrado' : dinero(vigente)}</b>${vigente == null ? '<small>Dato migrado sin SBC. El movimiento quedará como «No registrado → nuevo SBC»; no se inventa un valor anterior.</small>' : ''}</div>
        <div><span>Nuevo SBC diario</span><b class="sbc-nuevo">—</b></div>
        <div><span>Tope a la fecha efectiva</span><b class="sbc-tope">…</b><small class="sbc-tope-det"></small></div>
      </div>
      <div class="sbc-avisos"></div>
      <div class="hl-grid"><div><label>Fecha efectiva del cambio (no la fecha de captura)</label><input name="fecha" type="date" required value="${hoyMexico()}"></div>
        <div><label>Nuevo SBC diario</label><input name="sbc" inputmode="decimal" required placeholder="Ej. 1,250.00" autocomplete="off"></div>
        <div><label>SDI — salario diario integrado (opcional)</label><input name="sdi" inputmode="decimal" placeholder="Igual al SBC si lo dejas vacío" autocomplete="off"></div>
        <div><label>Tipo de salario</label><select name="ts">${opciones(TIPO_SAL, r.tipo_salario)}</select></div>
        <div><label class="sbc-motivo-lab">Motivo (opcional)</label><input name="motivo" maxlength="300"></div></div>
      <div id="hl-faltan-07-${relId}"></div>${botones('Registrar modificación')}`, async (f) => {
      const sbc = leerImporte(val(f, 'sbc')), sdi = leerImporte(val(f, 'sdi'));
      if (sbc == null || isNaN(sbc) || sbc <= 0) { mensaje('Captura el nuevo SBC diario: un importe con hasta 2 decimales.', false, null, 'sbc-msg'); return; }
      if (sdi != null && isNaN(sdi)) { mensaje('El SDI debe ser un importe con hasta 2 decimales.', false, null, 'sbc-msg'); return; }
      let est = await revisar();
      while (est.obsoleta) est = await revisar();
      if (est.bloquea) { mensaje(est.bloquea, false, null, 'sbc-msg'); return; }
      const faltan = faltantesIdse07(r, val(f, 'ts'));
      const html = `<b>Modificación de salario registrada.</b> El movimiento 07 quedó <b>pendiente</b> en la bandeja IDSE del registro patronal <b>${esc(textoRP(rpId))}</b>. `
        + (faltan.length ? `<span class="sbc-pend-arch">Archivo todavía no listo: falta ${faltan.map(esc).join(', ')}.</span> ` : 'Su archivo está listo para generarse desde la bandeja cuando lo decidas.')
        + enlaceBandeja(rpId);
      const res = await ejecutar('laboral_modificar_salario', { p_relacion_id: relId, p_fecha_efectiva: val(f, 'fecha') || null, p_sbc: sbc,
        p_sdi: sdi, p_tipo_salario: val(f, 'ts') || null, p_motivo: val(f, 'motivo') || null }, { html }, 'compensacion', 'sbc-msg');
      if (res.error && res.error.hint === 'sbc_tope') revisar();
    });
    const form = document.querySelector('#sbc-form-' + relId + ' form');
    if (!form) return;
    const caja = form.querySelector('.sbc-avisos');
    const enviar = form.querySelector('button[type=submit]');
    // Avisos en vivo. «bloquea» = la base lo rechazaría (tope, mínimo, motivo).
    let turno = 0; // solo la revisión más reciente pinta (las anteriores pueden terminar después)
    async function revisar() {
      const mio = ++turno;
      // Un error anterior deja de valer en cuanto se edita el formulario.
      const previo = document.getElementById('sbc-msg');
      if (previo && previo.classList.contains('err')) { previo.textContent = ''; previo.className = 'hl-msg'; }
      const fecha = val(form, 'fecha');
      const sbc = leerImporte(val(form, 'sbc'));
      const t = fecha ? await topeEn(fecha, relId) : {};
      if (mio !== turno) return { bloquea: null, obsoleta: true };
      form.querySelector('.sbc-tope').textContent = t.tope == null ? '—' : dinero(t.tope);
      form.querySelector('.sbc-tope-det').textContent = t.tope == null ? 'Sin UMA registrada para esa fecha.' : `25 UMA × ${dinero(t.uma)} (UMA vigente al ${fechaMx(fecha)})`;
      form.querySelector('.sbc-nuevo').textContent = sbc == null || isNaN(sbc) ? '—' : dinero(sbc);
      const avisos = []; let bloquea = null;
      const motivoLab = form.querySelector('.sbc-motivo-lab');
      motivoLab.textContent = 'Motivo (opcional)';
      if (sbc != null && !isNaN(sbc)) {
        if (t.tope != null && sbc > t.tope) {
          bloquea = `El SBC no puede rebasar el tope de ${dinero(t.tope)} a esa fecha (25 UMA).`;
          avisos.push(`<div class="sbc-av err">${esc(bloquea)} Si el salario diario integrado real es mayor, se registra como SDI y el SBC queda en el tope. <button type="button" class="hl-btn2" data-usar-tope>Usar el tope (${esc(dinero(t.tope))})</button></div>`);
        } else if (t.sm != null && sbc < t.sm) {
          bloquea = `El SBC no puede ser menor al salario mínimo ${t.zlfn ? 'de la zona libre de la frontera norte' : 'general'} (${dinero(t.sm)}) a esa fecha. Con jornada o semana reducida también se ajusta al mínimo.`;
          avisos.push(`<div class="sbc-av err">${esc(bloquea)}</div>`);
        } else if (t.sm != null && sbc < Math.round(t.sm * FACTOR_MINIMO * 100) / 100) {
          avisos.push(`<div class="sbc-av">Aviso: está por debajo del salario mínimo integrado con las prestaciones mínimas de ley (aprox. ${esc(dinero(Math.round(t.sm * FACTOR_MINIMO * 100) / 100))}). Revisa el factor de integración; no impide registrar.</div>`);
        }
        if (vigente != null && sbc < vigente) {
          motivoLab.textContent = 'Motivo (obligatorio: el SBC baja)';
          const mot = val(form, 'motivo');
          avisos.push(`<div class="sbc-av">El nuevo SBC es <b>menor</b> que el vigente (${esc(dinero(vigente))} → ${esc(dinero(sbc))}). Una reducción requiere sustento (p. ej. salario variable o convenio): escribe la justificación en el motivo.</div>`);
          if (mot.length < 5 && !bloquea) bloquea = 'Escribe la justificación de la disminución del SBC en el motivo (al menos 5 caracteres).';
        }
      }
      caja.innerHTML = avisos.join('');
      const usar = caja.querySelector('[data-usar-tope]');
      if (usar) usar.onclick = () => {
        const sdiEl = form.querySelector('[name=sdi]');
        if (!val(form, 'sdi')) sdiEl.value = formatoImporte(sbc);
        form.querySelector('[name=sbc]').value = formatoImporte(t.tope);
        revisar();
      };
      enviar.disabled = !!(bloquea && bloquea.startsWith('El SBC')); // tope o mínimo: la base lo rechazaría
      return { bloquea };
    }
    ['sbc', 'sdi'].forEach((n) => {
      const el = form.querySelector(`[name=${n}]`);
      el.addEventListener('input', () => formatearAlEscribir(el));
      el.addEventListener('blur', () => { const v = leerImporte(el.value); if (v != null && !isNaN(v)) el.value = formatoImporte(v); });
    });
    form.querySelector('[name=sbc]').addEventListener('input', revisar);
    form.querySelector('[name=fecha]').addEventListener('change', revisar);
    form.querySelector('[name=motivo]').addEventListener('input', revisar);
    const pintarFaltantes = () => {
      const c = document.getElementById('hl-faltan-07-' + relId);
      if (!c) return;
      const faltan = faltantesIdse07(r, val(form, 'ts'));
      c.innerHTML = faltan.length
        ? `<div class="sbc-av"><b>Se puede registrar el movimiento, pero su archivo todavía no estará listo para generar.</b> Para el archivo IDSE falta: ${faltan.map(esc).join(', ')}. `
          + 'Los datos de la relación se completan en Relación laboral → «Corregir datos»; los de la persona, en su ficha.</div>'
        : '<div class="sbc-av ok">Con estos datos, el archivo IDSE quedará listo para generar en la bandeja.</div>';
    };
    form.querySelector('[name=ts]').addEventListener('change', pintarFaltantes);
    pintarFaltantes();
    revisar();
  }

  // Tras cambiar un sueldo en Compensación: se avisa, sin tocar el SBC. El 07 que se
  // ofrece es SOLO el de la relación laboral de ese esquema; nunca se adivina.
  async function trasCambioSueldo(registroId) {
    if (!puedeOperar() || !registroId) return;
    const { data } = await sb.from('personal_registros_pago').select('relacion_laboral_id,sueldo,modalidad_sueldo,fecha_inicio').eq('id', registroId).maybeSingle();
    const relId = data && data.relacion_laboral_id;
    const esquemaTxt = data ? `${dinero(data.sueldo)} ${data.modalidad_sueldo || ''} desde ${fechaMx(data.fecha_inicio)}`.replace(/\s+/g, ' ') : '';
    // La lista «Esquemas de pago de esta relación» debe mostrar el sueldo recién guardado.
    const pid = estado.personaId;
    const esq = await sb.from('personal_registros_pago').select('id,sueldo,modalidad_sueldo,empresa_id,registro_patronal_id,clasificacion_id,fecha_inicio,relacion_laboral_id')
      .eq('personal_id', pid).eq('activo', true);
    if (estado.personaId !== pid) return;
    if (!esq.error) { estado.esquemas = esq.data || []; estado.pendientes = estado.esquemas.filter((e) => !e.relacion_laboral_id); pintarSbc(); }
    const r = estado.relaciones.find((x) => x.id === relId);
    const txt = 'Cambiaste un sueldo en los esquemas de pago. El SBC ante el IMSS no se actualiza solo: si también cambia, registra la modificación de salario (07).';
    if (!r) {
      mensaje(null, true, `${esc(txt)} <b>Este esquema no tiene relación laboral asignada</b>: asígnalo en <a href="#" onclick="cambiarSeccionDetalle('laboral');return false;">Relación laboral</a> para saber a qué registro patronal corresponde.`, 'sbc-msg');
      return;
    }
    if (r.estado !== 'vigente' || !r.registro_patronal_id) return;
    mensaje(null, true, `${esc(txt)} <button type="button" class="hl-btn2" id="sbc-desde-sueldo">Registrar modificación (07) · ${esc(nombreEmpresa(r.empresa_id))} · RP ${esc(textoRP(r.registro_patronal_id))}</button>`, 'sbc-msg');
    const b = document.getElementById('sbc-desde-sueldo');
    if (b) b.onclick = () => formSalario(r.id, `Origen: cambio del esquema de pago ${esquemaTxt}, que pertenece a la relación ${nombreEmpresa(r.empresa_id)} · RP ${textoRP(r.registro_patronal_id)} (ingreso ${fechaMx(r.fecha_ingreso)}). El SBC no se calcula del sueldo: captúralo tú.`);
  }

  // Desde un aviso: cierra la ficha y abre la bandeja IDSE en ese registro patronal.
  async function irABandeja(rpId) {
    if (typeof cerrarDetalle === 'function') cerrarDetalle();
    if (typeof cambiarPestana === 'function') cambiarPestana('idse');
    idse.rp = rpId;
    await abrirIdse();
  }
  // Fecha de hoy en la hora de México (no UTC: después de las 18:00 UTC ya sería «mañana»).
  function hoyMexico() {
    try { return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Mexico_City', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date()); }
    catch (e) { const d = new Date(); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); }
  }

  // Lo mismo que exige idse_validar para un 07. Es solo un aviso anticipado:
  // la base vuelve a validar al generar el archivo.
  // Mismo cálculo que public.es_nss_imss_valido: posiciones pares ×2 (Luhn) sobre los 10 primeros.
  function nssImssValido(n) {
    const t = String(n || '');
    if (!/^[0-9]{11}$/.test(t)) return false;
    let s = 0;
    for (let i = 0; i < 10; i++) { const d = Number(t[i]) * (i % 2 ? 2 : 1); s += Math.floor(d / 10) + (d % 10); }
    return (10 - (s % 10)) % 10 === Number(t[10]);
  }
  function faltantesIdse07(r, tipoSalarioElegido) {
    const p = estado.persona || {};
    const curpOk = typeof CURP_REGEX !== 'undefined' ? CURP_REGEX.test(String(p.curp || '')) : String(p.curp || '').length === 18;
    const f = [];
    if (!/^[0-9]{11}$/.test(String(p.nss || ''))) f.push('NSS de 11 dígitos');
    else if (!nssImssValido(p.nss)) f.push('NSS válido (el dígito verificador no corresponde)');
    if (/[0-9]/.test(`${p.primer_apellido || ''}${p.segundo_apellido || ''}${p.nombres || ''}`)) f.push('nombre y apellidos sin dígitos');
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
      if (!Object.keys(cambios).length) { mensaje('No cambiaste ningún dato.', false, null, 'rl-msg'); return; }
      await ejecutar('laboral_corregir_datos', { p_relacion_id: relId, p_cambios: cambios, p_motivo: val(f, 'motivo') }, 'Corrección registrada.', 'laboral', 'rl-msg');
    });
  }

  function formAnular(evId, relId) {
    const e = estado.eventos.find((x) => x.evento_id === evId) || {};
    montar('hl-form-' + relId, `<b>Anular ${esc(TIPOS[e.tipo] || 'movimiento')} del ${fechaMx(e.fecha_efectiva)}</b>
      <div class="hl-grid"><div><label>Motivo de la anulación</label><input name="motivo" required></div></div>
      <p class="hint" style="margin:6px 0">Se deshace su efecto${e.idse_estado === 'pendiente' ? ' y su movimiento pendiente sale de la bandeja IDSE' : ''}. En Historia laboral queda visible, marcado como anulado.</p>${botones('Anular movimiento')}`, async (f) => {
      await ejecutar('laboral_anular_evento', { p_evento_id: evId, p_motivo: val(f, 'motivo') }, 'Movimiento anulado. En Historia laboral queda marcado como anulado.', 'laboral', 'rl-msg');
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
        <div><label>Guía IDSE</label><input id="idse-guia" maxlength="5" inputmode="numeric" ${esAdmin() ? '' : 'disabled'}><div class="hl-meta" id="idse-guia-nota"></div></div>
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
    if (gi) gi.value = r.guia_idse || '00000'; if (zo) zo.value = r.zona_salario_minimo || 'general';
    const nota = document.getElementById('idse-guia-nota');
    if (nota) nota.textContent = (r.guia_idse ? 'Guía capturada.' : 'Sin guía configurada: se usa 00000 (valor inicial).')
      + ' Confírmala con la subdelegación del IMSS de este registro patronal' + (esAdmin() ? '.' : '; solo Administrador la edita.');
  }
  async function guardarRP() {
    const guia = document.getElementById('idse-guia').value.trim();
    if (!/^\d{5}$/.test(guia)) { idseMsg('La guía IDSE tiene 5 dígitos (sin guía de la subdelegación se usa 00000).', false); return; }
    const { error } = await sb.from('empresas_registros_patronales').update({ guia_idse: guia, zona_salario_minimo: document.getElementById('idse-zona').value }).eq('id', idse.rp);
    if (error) { idseMsg(msgError(error), false); return; }
    await cargarCatalogos(); pintarRP(); await refrescarIdse(); idseMsg('Datos del registro patronal guardados.', true);
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
        <td>${(f.errores || []).map((x) => `<div class="idse-err">${x.includes(':') ? esc(x) : 'Falta: ' + esc(x)}</div>`).join('')}${(f.avisos || []).map((x) => `<div class="idse-aviso">${esc(x)}</div>`).join('')}${okF && !(f.avisos || []).length ? '<span class="hl-chip vigente">Lista</span>' : ''}</td></tr>`;
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
    const ESTA = { generado: 'Archivo generado', presentado: 'Presentado', con_resultado: 'Resultado recibido', cancelado: 'Cancelado' };
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
  window.BH_laboral = { alAbrirDetalle, trasAlta, abrirIdse, fichaBloqueada, irABandeja, trasCambioSueldo };
  prepararAlta();
  const bIdse = document.querySelector('nav.tabs button[data-tab="idse"]');
  if (bIdse) bIdse.addEventListener('click', () => { abrirIdse(); });
})();
