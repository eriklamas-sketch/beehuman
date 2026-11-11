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
.rl-grupo{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--v21-texto-2,#5B6680)}
.rl-internos-cab{margin:22px 0 4px;padding-top:14px;border-top:1px solid var(--v21-borde,#E5E9F1)}
.hl-falta{outline:2px solid #E0A800!important;outline-offset:1px;background:#FFFBEF!important}
.hl-falta-lab{display:inline-block;margin-left:6px;padding:0 6px;border-radius:999px;background:#FFF3D6;color:#8A6400;font-size:10.5px;font-weight:700}
.idse-config{border:1px solid var(--v21-borde,#E5E9F1);border-radius:12px;padding:12px 14px;margin:0 0 6px;background:var(--v21-fondo,#F6F8FB)}
.idse-config h4{margin:0 0 8px;font-size:13.5px;color:var(--v21-navy,#16264A)}
.idse-sec{margin:20px 0 6px;font-size:14.5px;color:var(--v21-navy,#16264A)}
.idse-completar{margin-top:6px;display:flex;gap:6px;flex-wrap:wrap}.idse-completar .hl-btn2{padding:4px 10px;font-size:12px}
.rl-internos{margin:0 0 4px;font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--v21-texto-2,#5B6680)}
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
.rl-campos{display:grid;grid-template-columns:1fr 1fr;gap:0 32px;margin:10px 0 12px}
.rl-col{display:flex;flex-direction:column}
.rl-campo{display:flex;justify-content:space-between;align-items:baseline;gap:12px;padding:7px 0;border-bottom:1px solid var(--v21-borde-2,#EEF1F6)}
.rl-campo:last-child{border-bottom:0}
.rl-lab{font-size:12px;color:var(--v21-texto-2,#5B6680)}
.rl-val{font-weight:600;color:var(--v21-texto,#16264A);text-align:right}.rl-val small{display:block;font-weight:500;color:#8A6400}
.rl-val.vacio{font-weight:400;color:#8A94A8}
.rl-internos-card{border:1px solid var(--v21-borde,#E5E9F1);border-radius:12px;padding:14px 16px 6px;margin:18px 0 0;background:var(--v21-superficie,#fff)}
.rl-internos-card .rl-internos-cab{margin:0 0 6px;padding:0;border:0}
.bd-lista{margin:6px 0 10px;padding:0;list-style:none}.bd-lista li{padding:5px 0;border-bottom:1px solid var(--v21-borde-2,#EEF1F6)}
.bd-lista small{display:block;color:var(--v21-texto-2,#5B6680)}
.bd-lista .bd-falta{color:#B42318;font-weight:600}
.bd-lista .bd-corregir,.bd-error .bd-corregir{margin:6px 0 0;padding:6px 10px;font-size:12.5px}
.bd-error li{margin:6px 0}
.ing-aviso{margin:10px 0 0}
.bd-confirma{display:flex;gap:12px;align-items:center;margin:12px 0 4px;padding:12px 14px;min-height:48px;box-sizing:border-box;
  background:#FFF6D6;border:2px solid #E8B400;border-radius:10px;font-weight:700;font-size:14px;color:var(--v21-navy,#16264A);cursor:pointer}
.bd-confirma:hover{background:#FFEFB8}
.bd-confirma:focus-within{outline:3px solid rgba(232,180,0,.45);outline-offset:2px}
.bd-confirma input{width:22px!important;height:22px!important;min-width:0!important;flex:none;margin:0!important;padding:0!important;accent-color:#16264A;cursor:pointer}
.bd-resumen{margin-top:10px}
.hl-form button[type=submit]:disabled{opacity:.42;cursor:not-allowed;filter:grayscale(.35);box-shadow:none}
.hl-form button[type=submit]:not(:disabled){opacity:1}
.bd-esq{display:block;margin-top:3px;color:#24427A}
.bd-esq.sin{color:var(--v21-texto-2,#5B6680);font-style:italic}
.rl-esqs{margin:4px 0 6px;font-size:12.5px;color:var(--v21-texto-2,#5B6680)}
.rl-esqs b{color:var(--v21-texto,#16264A)}
.ri-sec{margin:14px 0 6px;font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--v21-texto-2,#5B6680);font-weight:700}
.ri-ref{border:1px solid var(--v21-borde,#E5E9F1);border-left:4px solid #9AA8C2;border-radius:10px;padding:10px 12px;background:#F6F8FB;margin:4px 0 8px}
.ri-ref h5{margin:0 0 6px;font-size:13px;color:var(--v21-navy,#16264A)}
.ri-ref .rl-campos{margin:4px 0}
.ri-ref .ri-nota{font-size:12px;color:#5B6680;margin:6px 0 0}
.ri-bloqueo{margin:8px 0;padding:10px 12px;border-radius:9px;background:#FDECEA;color:#8F2A1E;font-size:13px}
.ri-bloqueo .hl-btn2{margin:8px 8px 0 0}
.fd-aviso{margin:8px 0 0;padding:8px 10px;border-radius:9px;background:#FFF3D6;color:#6B4E00;font-size:13px}
.ing-tipo-txt{margin:8px 0 4px;padding:8px 12px;border-radius:9px;background:#EEF4FF;color:var(--v21-navy,#16264A);font-size:13px}
.ing-tipo-txt.reingreso{background:#EAF6EE;color:#1F5130}
.esq-fila{display:grid;grid-template-columns:1.4fr 1fr .8fr 1fr auto;gap:10px;align-items:end;padding:10px 0;border-bottom:1px dashed var(--v21-borde,#E5E9F1)}
.esq-fila .esq-quitar .hl-btn2{margin:0}
.esq-fila .esq-nota{grid-column:1/-1;font-size:12px;color:var(--v21-texto-2,#5B6680);margin-top:-4px}
.esq-fila .esq-nota:empty{display:none}
.esq-fila .esq-nota.err{color:#B42318;font-weight:600}
.ing-err:empty{display:none}
.ing-err.activo{margin:12px 0 0;padding:10px 14px;border-radius:9px;background:#FDECEA;color:#8F2A1E;font-size:13px;border:1px solid #F5C2BC}
.ing-err ul{margin:6px 0 0;padding-left:18px}
details.ri-ref summary{cursor:pointer;font-size:13px;color:var(--v21-navy,#16264A)}
@media (max-width:640px){.esq-fila{grid-template-columns:1fr 1fr}.esq-fila>div:first-child{grid-column:1/-1}}
#hl-aviso-imss{position:fixed;inset:0;z-index:80;background:rgba(14,26,51,.45);display:flex;align-items:center;justify-content:center;padding:16px}
#hl-aviso-imss .av-caja{background:#fff;border-radius:14px;max-width:560px;width:100%;padding:20px 22px;box-shadow:0 18px 40px rgba(14,26,51,.25);max-height:90vh;overflow:auto}
#hl-aviso-imss h3{margin:0 0 8px;font-size:16px;text-transform:none;letter-spacing:0;color:var(--v21-navy,#16264A)}
#hl-aviso-imss .av-rel{border:1px solid var(--v21-borde,#E5E9F1);border-radius:10px;padding:10px 12px;margin:10px 0}
#hl-aviso-imss .av-pasos{list-style:none;margin:8px 0 0;padding:0;font-size:13px}
#hl-aviso-imss .av-pasos li{padding:3px 0 3px 22px;position:relative;color:#8A94A8}
#hl-aviso-imss .av-pasos li::before{content:"○";position:absolute;left:2px}
#hl-aviso-imss .av-pasos li.hecho{color:#1F6B33}#hl-aviso-imss .av-pasos li.hecho::before{content:"✓"}
#hl-aviso-imss .av-pasos li.actual{color:#8A6400;font-weight:600}#hl-aviso-imss .av-pasos li.actual::before{content:"●"}
#hl-aviso-imss .av-pasos li.error{color:#B42318;font-weight:600}#hl-aviso-imss .av-pasos li.error::before{content:"✕"}
#hl-aviso-imss .av-acc{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end;margin-top:14px}
#hl-aviso-imss .av-acc button{margin:0}
@media (max-width:640px){.rl-campos{grid-template-columns:1fr}.rl-col+.rl-col .rl-campo:first-child{border-top:1px solid var(--v21-borde-2,#EEF1F6)}}
@media (max-width:640px){.hl-card{padding:12px}.hl-grid{grid-template-columns:1fr}.hl-ev-cab{gap:6px}}
/* Registrar ingreso / reingreso: proceso por etapas (solo presentación) */
.hl-form.ri-form{border:0;background:transparent;padding:0;margin:10px 0}
.ri-cab{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;padding:18px 20px;margin:0 0 16px;border-radius:var(--v21-radio,14px);border:1px solid var(--v21-tarjeta-borde,#E6E9EF);background:linear-gradient(180deg,#FFFFFF 0%,#F6F8FC 100%);box-shadow:var(--v21-sombra,0 4px 14px rgba(22,38,74,.05))}
.ri-titulo{text-transform:none;margin:0;font-size:18px;line-height:1.25;font-weight:700;letter-spacing:-.01em;color:var(--v21-navy,#16264A)}
.ri-lead{margin:6px 0 0;max-width:62ch;font-size:13px;line-height:1.5;color:var(--v21-texto-2,#5B6680)}
.ri-global{flex:none;align-self:center;padding:7px 12px;border-radius:999px;font-size:12.5px;font-weight:600;white-space:nowrap;background:#EEF1F6;color:var(--v21-texto-2,#5B6680)}
.ri-global[data-estado=ok]{background:var(--v21-verde-suave,#E6F4EC);color:#1F5130}
.ri-global[data-estado=atencion]{background:#FFF3D6;color:#7A5800}
.ri-pasos{list-style:none;margin:0;padding:0}
.ri-paso{position:relative;margin:0 0 18px;border-radius:var(--v21-radio,14px);border:1px solid var(--v21-tarjeta-borde,#E6E9EF);background:var(--v21-superficie,#FFFFFF);box-shadow:var(--v21-sombra,0 4px 14px rgba(22,38,74,.05));transition:border-color .2s,box-shadow .2s}
.ri-paso:not(:last-child)::after{content:"";position:absolute;left:37px;bottom:-19px;width:2px;height:18px;background:#D9DFEA}
.ri-paso[data-estado=atencion]{border-color:#E9C46A;box-shadow:0 0 0 3px rgba(255,200,44,.16),var(--v21-sombra,0 4px 14px rgba(22,38,74,.05))}
.ri-paso-cab{display:flex;align-items:center;gap:14px;padding:14px 18px;border-bottom:1px solid var(--v21-borde-2,#EDF0F6);border-radius:var(--v21-radio,14px) var(--v21-radio,14px) 0 0;background:#FAFBFD}
.ri-num{flex:none;display:grid;place-items:center;width:38px;height:38px;border-radius:50%;font-size:14px;font-weight:700;font-variant-numeric:tabular-nums;background:#FFFFFF;color:var(--v21-navy,#16264A);border:2px solid #C9D2E3}
.ri-paso[data-estado=ok] .ri-num{background:#1F7A4D;border-color:#1F7A4D;color:#FFFFFF}
.ri-paso[data-estado=atencion] .ri-num{background:#FFC82C;border-color:#E0A800;color:#3D2C00}
.ri-paso[data-estado=opc] .ri-num,.ri-paso[data-estado=info] .ri-num{border-style:dashed;color:var(--v21-texto-2,#5B6680)}
.ri-paso-tit{min-width:0;flex:1}
.ri-paso-tit h4{margin:0;font-size:15px;line-height:1.3;font-weight:700;color:var(--v21-navy,#16264A)}
.ri-paso-tit p{margin:2px 0 0;font-size:12.5px;line-height:1.4;color:var(--v21-texto-3,#8690A6)}
.ri-estado{flex:none;padding:3px 10px;border-radius:999px;font-size:11.5px;font-weight:600;white-space:nowrap;background:#EEF1F6;color:var(--v21-texto-2,#5B6680)}
.ri-estado[data-estado=ok]{background:var(--v21-verde-suave,#E6F4EC);color:#1F5130}
.ri-estado[data-estado=atencion]{background:#FFF3D6;color:#7A5800}
.ri-estado[data-estado=opc],.ri-estado[data-estado=info]{background:transparent;border:1px dashed #C9D2E3;color:var(--v21-texto-3,#8690A6)}
.ri-cuerpo{padding:16px 18px 18px}
.ri-cuerpo>.hint:first-child{margin-top:0!important}
.ri-cuerpo .ri-ref{margin-top:0}
.ri-paso[data-paso="5"]{background:#FBFCFE;box-shadow:none}
.ri-paso[data-paso="5"] .ri-paso-cab{background:transparent}
.ri-pie{margin:2px 0 0;padding:14px 18px;border-radius:var(--v21-radio,14px);border:1px solid var(--v21-tarjeta-borde,#E6E9EF);background:var(--v21-superficie,#FFFFFF);box-shadow:var(--v21-sombra,0 4px 14px rgba(22,38,74,.05))}
.ri-cuerpo .ing-imss-ayuda{font-size:12px!important;line-height:1.5;color:var(--v21-texto-2,#5B6680);background:#F6F8FB;border-radius:9px;padding:8px 12px;margin:0 0 12px!important}
.ri-pie .ing-err.activo{margin:0 0 10px}
.ri-pie .hl-acc{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
@media (max-width:640px){.ri-cab{flex-direction:column;padding:14px}.ri-global{align-self:flex-start}.ri-paso-cab{padding:12px;gap:10px;flex-wrap:wrap}.ri-num{width:32px;height:32px;font-size:13px}.ri-paso-tit{flex:1 1 calc(100% - 52px)}.ri-paso-tit p{font-size:12px}.ri-estado{margin-left:42px}.ri-cuerpo{padding:12px}.ri-paso:not(:last-child)::after{left:27px}}
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
  let avisoTrasBaja = null;
  // Baja en una empresa interrumpida para corregir una relación: se guarda lo capturado
  // y se vuelve al formulario al guardar (o cancelar) la corrección.
  let bajaEnCurso = null; // persona cuya ficha debe mostrar el aviso IDSE al terminar de cargar
  // Ingreso o reingreso a medio capturar: si la ficha se vuelve a pintar (p. ej. al guardar
  // los datos personales), se restaura lo capturado.
  let ingresoEnCurso = null;
  let abrirReingresoAl = null; // desde «Nuevo empleado»: abrir el expediente existente en el reingreso

  async function alAbrirDetalle(p) {
    const raiz = document.getElementById('hl-raiz');
    if (!raiz || !p) return;
    estado = { personaId: p.id, persona: p, relaciones: [], eventos: [], pendientes: [], esquemas: [], formAbierto: null };
    const ret = document.getElementById('idse-retorno'); if (ret) ret.remove();
    document.querySelectorAll('[data-detail-section="personal"] .hl-falta').forEach((el) => el.classList.remove('hl-falta'));
    bloquearFicha(false);
    raiz.innerHTML = '<p class="hint">Cargando historia laboral…</p>';
    asegurarContenedores();
    ['rl-raiz', 'sbc-raiz'].forEach((k) => { const c = document.getElementById(k); if (c) c.innerHTML = '<p class="hint">Cargando relación laboral…</p>'; });
    if (!causas.length || !rps.length) await cargarCatalogos();
    const id = p.id;
    const [rel, hist, pend] = await Promise.all([
      sb.from('relaciones_laborales').select('*').eq('personal_id', id),
      sb.rpc('laboral_historial', { p_personal_id: id }),
      // Todos los esquemas (activos y cerrados): cada uno se muestra con su relación laboral.
      sb.from('personal_registros_pago').select('id,sueldo,modalidad_sueldo,empresa_id,registro_patronal_id,clasificacion_id,periodicidad_id,dias_periodo,fecha_inicio,fecha_fin,activo,relacion_laboral_id')
        .eq('personal_id', id),
    ]);
    if (estado.personaId !== id) return; // se abrió otra ficha mientras cargaba
    if (rel.error || hist.error) {
      raiz.innerHTML = `<div class="hl-msg err">No se pudo cargar la historia laboral: ${esc(msgError(rel.error || hist.error))}</div>`;
      return;
    }
    estado.relaciones = (rel.data || []).filter((r) => r.estado !== 'anulada');
    estado.eventos = hist.data || [];
    estado.todosEsquemas = pend.error ? [] : (pend.data || []);
    estado.esquemas = estado.todosEsquemas.filter((e) => e.activo);
    estado.pendientes = estado.esquemas.filter((e) => !e.relacion_laboral_id);
    bloquearFicha(estado.relaciones.length > 0);
    pintar();
    msgPendiente = null; // un aviso solo se muestra en la ficha que lo generó, una vez
    // Compensación muestra a qué relación pertenece cada esquema: se repinta con estos datos.
    if (typeof renderRegistrosPagoDetalle === 'function' && typeof detalleRegistrosPagoEstado !== 'undefined' && detalleRegistrosPagoEstado === 'ok') renderRegistrosPagoDetalle();
    aplicarPendienteAbrir();
    if (ingresoEnCurso && ingresoEnCurso.personaId !== id) ingresoEnCurso = null;
    if (ingresoEnCurso && !document.querySelector('#hl-form-ingreso form')) {
      const b = ingresoEnCurso;
      formIngreso(b);
      mensaje(null, true, 'Seguimos con el registro de ingreso / reingreso: se conservó todo lo que habías capturado.', 'rl-msg');
    }
    if (abrirReingresoAl && abrirReingresoAl.personaId === id) {
      const a = abrirReingresoAl; abrirReingresoAl = null;
      if (typeof cambiarSeccionDetalle === 'function') cambiarSeccionDetalle('laboral');
      formIngreso(null, a.empresa || null);
      if (a.nota) mensaje(null, true, a.nota, 'rl-msg');
    }
    if (bajaEnCurso && bajaEnCurso.personaId !== id) bajaEnCurso = null;
    if (bajaEnCurso && bajaEnCurso.volver) { const b = bajaEnCurso; bajaEnCurso = null; formBajaDefinitiva(b); }
    if (avisoTrasBaja === id) {
      avisoTrasBaja = null;
      avisoCierre(() => (typeof cerrarDetalleYa === 'function' ? cerrarDetalleYa() : cerrarDetalle({ sinAvisoImss: true })), true);
    }
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
      // En Baja con historial, el estatus no se cambia a mano: el menú ofrece el atajo
      // a «Registrar ingreso / reingreso» (la persona vuelve a Activo al registrarlo).
      const atajo = si && enBaja && puedeOperar();
      let opIng = est.querySelector('option[value="__ingreso"]');
      if (atajo && !opIng) { opIng = new Option('Registrar ingreso / reingreso…', '__ingreso'); est.appendChild(opIng); }
      if (!atajo && opIng) opIng.remove();
      est.disabled = si && enBaja && !atajo;
      const vig = estado.relaciones.some((r) => r.estado === 'vigente');
      [...est.options].forEach((o) => {
        if (o.value === 'Baja' || o.text === 'Baja') o.disabled = si && !enBaja && !(vig && puedeOperar());
        else if (o.value !== '__ingreso') o.disabled = atajo;
      });
      est.title = !si ? '' : enBaja ? 'Sin relaciones vigentes. Para reactivarla, registra su ingreso o reingreso.' : 'Baja: dar de baja en una empresa';
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
      const t = document.createElement('div'); t.className = 'rl-internos-cab';
      t.innerHTML = '<h4 class="rl-internos">Datos internos de la empresa</h4><p class="hint" style="margin:0 0 8px">Uso interno de la empresa: no se envían al IMSS. Se guardan con «Guardar cambios».</p>';
      const card = document.createElement('div'); card.className = 'rl-internos-card'; card.id = 'rl-internos';
      d.insertAdjacentElement('afterend', card); card.appendChild(t);
      [...secL.querySelectorAll(':scope > .grid3')].forEach((g) => card.appendChild(g));
      const fi = document.getElementById('d-fechainicio');
      const labFi = fi && fi.closest('div') ? fi.closest('div').querySelector('label') : null;
      if (labFi) labFi.textContent = 'Fecha de ingreso (administrativa)';
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
    if (msgPendiente && msgPendiente.personaId === estado.personaId) mensaje(msgPendiente.texto, !msgPendiente.error, msgPendiente.html, msgPendiente.destino);
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
      <p class="hint" style="margin:0 0 10px">Solo consulta. Ingresos, reingresos, bajas, correcciones y la anulación del último movimiento se registran en <a href="#" onclick="cambiarSeccionDetalle('laboral');return false;">Relación laboral</a>; los esquemas de pago y la modificación de salario (SDI), en <a href="#" onclick="cambiarSeccionDetalle('compensacion');return false;">Compensación</a>.${varias ? ' Esta persona tiene más de una relación laboral: cada acontecimiento indica su empresa y registro patronal.' : ''}</p>
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
  // Tarjeta en dos columnas: etiqueta a la izquierda, valor a la derecha.
  const campoRl = (lab, val, vacio) => `<div class="rl-campo"><span class="rl-lab">${lab}</span><span class="rl-val${vacio ? ' vacio' : ''}">${val}</span></div>`;
  function camposRelacion(r, rpTxt) {
    const v = (x) => (x == null || x === '' || x === '—');
    const fi = fechaMx(r.fecha_ingreso), fa = fechaMx(r.fecha_reconocimiento_antiguedad);
    const izq = [campoRl('Estado', r.estado === 'vigente' ? 'Vigente' : 'Baja'), campoRl('Ingreso', fi, v(fi)), campoRl('Antigüedad reconocida', fa, v(fa))];
    if (r.estado === 'baja') izq.push(campoRl('Baja', `${fechaMx(r.fecha_baja)}${r.causa_baja ? '<small>' + esc(valorLegible('causa_baja', r.causa_baja)) + '</small>' : ''}`));
    const der = [];
    if (rpTxt) {
      const tt = valorLegible('tipo_trabajador', r.tipo_trabajador), ts = valorLegible('tipo_salario', r.tipo_salario), jo = valorLegible('jornada', r.jornada);
      izq.push(campoRl('Tipo de trabajador', esc(tt || '—'), v(tt)));
      der.push(campoRl('Tipo de salario', esc(ts || '—'), v(ts)), campoRl('Jornada IMSS', esc(jo || '—'), v(jo)),
        campoRl('SDI', `${sdiDe(r) == null ? 'No registrado' : dinero(sdiDe(r))}${r.sbc != null && sdiDe(r) != null && Number(r.sbc) !== sdiDe(r) ? `<small>cotiza con el tope ${esc(dinero(r.sbc))}</small>` : ''}`, sdiDe(r) == null),
        campoRl('UMF', esc(r.umf || '—'), !r.umf));
    }
    der.push(campoRl('Número interno', esc(r.numero_interno || '—'), !r.numero_interno));
    return `<div class="rl-campos"><div class="rl-col">${izq.join('')}</div><div class="rl-col">${der.join('')}</div></div>`;
  }
  function pintarRelaciones() {
    const raiz = document.getElementById('rl-raiz');
    if (!raiz) return;
    const rels = [...estado.relaciones].sort((a, b) => (a.estado === 'vigente' ? 0 : 1) - (b.estado === 'vigente' ? 0 : 1)
      || String(b.fecha_ingreso || '').localeCompare(String(a.fecha_ingreso || '')));
    let h = `<div class="hl-wrap"><div class="hl-cab"><h4 class="rl-grupo" style="margin:0">Datos de la relación y seguridad social</h4>
      ${puedeOperar() ? '<div class="hl-acc" style="margin:0"><button type="button" class="primary" style="margin:0" id="hl-btn-ingreso">Registrar ingreso / reingreso</button></div>' : ''}</div>
      <div class="hl-msg" id="rl-msg"></div><div id="hl-form-ingreso"></div><div id="hl-form-bajacab"></div>`;
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
    if (!rels.length) h += `<p class="hint">Esta persona todavía no tiene relaciones laborales registradas.${puedeOperar() ? ' Usa «Registrar ingreso / reingreso».' : ''}</p>`;
    rels.forEach((r) => {
      const rpTxt = textoRP(r.registro_patronal_id);
      h += `<div class="hl-card ${r.estado}" data-relacion="${r.id}"><h4>${esc(nombreEmpresa(r.empresa_id))} · ${esc(rpTxt ? 'RP ' + rpTxt : 'Sin registro patronal (sin IDSE)')}
        <span class="hl-chip ${r.estado}">${r.estado === 'vigente' ? 'Vigente' : 'Baja'}</span>
        ${(r.pendientes_migracion || []).map((p) => `<span class="hl-chip aviso">${esc(PENDIENTE[p] || p)}</span>`).join('')}</h4>
        ${camposRelacion(r, rpTxt)}${esquemasDeRelacionHtml(r)}`;
      if (puedeOperar()) {
        // Anulación: solo el último movimiento IMSS de esta relación que todavía no
        // se presentó (la regla vive en la base: laboral_anular_evento).
        const anu = estado.eventos.find((e) => e.evento_id === ultimoAnulable(r.id));
        h += '<div class="hl-acc">';
        if (r.estado === 'vigente') h += `<button type="button" class="hl-btn2" data-accion="baja" data-rel="${r.id}">Dar de baja esta relación</button>`;
        h += `<button type="button" class="hl-btn2" data-accion="corregir" data-rel="${r.id}">Corregir datos</button>`;
        if (anu) h += `<button type="button" class="hl-btn2 peligro" data-anular="${anu.evento_id}" data-rel="${r.id}">Anular último movimiento: ${esc(TIPOS[anu.tipo] || anu.tipo)} del ${fechaMx(anu.fecha_efectiva)}</button>`;
        h += `</div><div id="hl-form-${r.id}"></div>`;
      }
      h += '</div>';
    });
    raiz.innerHTML = h + '</div>';
    const bi = document.getElementById('hl-btn-ingreso');
    if (bi) bi.onclick = () => { ingresoEnCurso = null; formIngreso(); };
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
    let h = `<div class="card sbc-card"><div class="hl-cab"><h4 style="margin:0">Salario ante el IMSS (SDI)</h4></div>
      <p class="hint" style="margin:0 0 8px">${esc(SDI_AYUDA)} Cambiar el sueldo de un esquema no cambia el SDI: si el SDI cambia, se registra aquí y genera la modificación de salario (07) pendiente en la bandeja IDSE.</p>
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
      const sdiV = sdiDe(r);
      h += `<div>SDI vigente registrado: <b>${sdiV == null ? 'No registrado' : dinero(sdiV) + ' diario'}</b>${sdiV != null && desde ? ` <span class="hl-meta">(desde ${fechaMx(desde)})</span>` : ''}${r.sbc != null && sdiV != null && Number(r.sbc) !== sdiV ? ` <span class="hl-meta">· cotiza con el tope: ${esc(dinero(r.sbc))}</span>` : ''}</div>
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
    return topeEnRp(fecha, r.registro_patronal_id);
  }
  async function topeEnRp(fecha, rpId) {
    const rp = rps.find((x) => x.id === rpId) || {};
    const zlfn = rp.zona_salario_minimo === 'zlfn';
    const [uma, sm] = await Promise.all([parametro('UMA_DIARIA', fecha), parametro(zlfn ? 'SALARIO_MINIMO_ZLFN' : 'SALARIO_MINIMO_GENERAL', fecha)]);
    return { uma, sm, zlfn, tope: uma == null ? null : Math.round(uma * 25 * 100) / 100 };
  }
  // Un solo dato capturado: el SDI (salario diario integrado). El SBC que exige el
  // formato IMSS se deriva de él: igual al SDI, o el tope de 25 UMA si lo rebasa.
  // (El piso —salario mínimo— no se ajusta: si el SDI es menor, se rechaza.)
  const sbcDeSdi = (sdi, tope) => (sdi == null || isNaN(sdi) ? null : (tope != null && sdi > tope ? tope : sdi));
  const sdiDe = (r) => (r.sdi != null ? Number(r.sdi) : (r.sbc != null ? Number(r.sbc) : null));
  const SDI_AYUDA = 'SDI = salario diario integrado: el importe diario con las prestaciones integradas que se usa como base de cotización en los movimientos ante el IMSS. '
    + 'No es el sueldo diario nominal (sueldo mensual ÷ 30) ni se calcula de los esquemas de pago. Si rebasa el tope de 25 UMA, el archivo IDSE lleva el tope como SBC.';
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
    if (html) { m.innerHTML = html; ligarAcciones(m); } else m.textContent = texto;
    m.className = 'hl-msg ' + (ok ? 'ok' : 'err');
    if (destino) m.scrollIntoView({ block: 'nearest' }); // éxito o error: el mensaje siempre queda a la vista
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
    // Cambios pendientes reales: solo si la persona escribió o eligió algo en el formulario.
    ['input', 'change'].forEach((t) => f.addEventListener(t, (ev) => { if (ev.isTrusted) f.dataset.sucio = '1'; }));
    f.onsubmit = async (ev) => {
      ev.preventDefault();
      const b = f.querySelector('button[type=submit]'); b.disabled = true;
      try { await alEnviar(f); } finally { if (document.body.contains(b)) { b.disabled = false; actualizarEnvio(f); } }
    };
    const primero = f.querySelector('input,select'); if (primero) primero.focus();
  }
  // Confirmaciones obligatorias: el botón principal se ve inactivo mientras falte marcar
  // alguna casilla visible con data-requerida. Es solo visual: cada envío vuelve a
  // revisar las casillas en su propia lógica (y la base aplica sus reglas).
  function confirmacionesPendientes(f) {
    return [...f.querySelectorAll('input[type=checkbox][data-requerida]')].filter((c) => c.offsetParent !== null && !c.checked);
  }
  function actualizarEnvio(f) {
    if (!f) return;
    const b = f.querySelector('button[type=submit]'); if (!b) return;
    // Formularios «siempre activos»: el botón nunca se apaga; al enviar se dice qué falta.
    const falta = !f.dataset.siempreActivo && (confirmacionesPendientes(f).length > 0 || f.dataset.bloqueado === '1');
    b.disabled = falta;
    b.title = falta ? (f.dataset.bloqueado === '1' ? 'Resuelve lo indicado antes de continuar.' : 'Marca la confirmación obligatoria para continuar.') : '';
  }
  function ligarEnvio(f) {
    if (!f || f.dataset.ligado) return;
    f.dataset.ligado = '1';
    f.addEventListener('change', () => actualizarEnvio(f));
    actualizarEnvio(f);
  }
  const val = (f, n) => { const el = f.querySelector(`[name="${n}"]`); return el ? (el.value || '').trim() : ''; };
  const num = (f, n) => { const v = val(f, n).replace(/,/g, ''); return v === '' ? null : Number(v); };

  // =====================================================================
  // Nuevo ingreso y reingreso (Relación laboral)
  // - Nuevo ingreso: la persona nunca tuvo relación con esa empresa.
  // - Reingreso: ya trabajó en esa empresa y su relación terminó. Se abre un
  //   periodo NUEVO (otra relación laboral) con laboral_registrar_ingreso; la
  //   relación anterior, sus eventos, su 02 y sus esquemas no se tocan.
  // En ambos casos es el mismo expediente (mismo ID BeeHuman, CURP, RFC y NSS).
  // =====================================================================
  const empresasActivas = () => (typeof empresas !== 'undefined' ? empresas : []).filter((e) => e.activo !== false);
  const rpCorto = (rpId) => (textoRP(rpId) ? 'RP ' + textoRP(rpId) : 'sin registro patronal');
  const relsEn = (empId, est) => estado.relaciones.filter((r) => r.empresa_id === empId && (!est || r.estado === est));
  const ultimaBajaEn = (empId) => relsEn(empId, 'baja').sort((a, b) => String(b.fecha_baja || '').localeCompare(String(a.fecha_baja || ''))
    || String(b.fecha_ingreso || '').localeCompare(String(a.fecha_ingreso || '')))[0] || null;
  const nombreEn = (lista, id) => ((lista || []).find((x) => x.id === id) || {}).nombre || null;
  function esquemaTexto(e) {
    const cl = nombreEn(typeof clasificaciones !== 'undefined' ? clasificaciones : [], e.clasificacion_id);
    const pe = nombreEn(typeof periodicidades !== 'undefined' ? periodicidades : [], e.periodicidad_id);
    return [cl, `${dinero(e.sueldo)} ${e.modalidad_sueldo || ''}`.trim(), pe].filter(Boolean).join(' · ');
  }
  const esquemasDe = (relId) => (estado.todosEsquemas || []).filter((e) => e.relacion_laboral_id === relId);
  function esquemasDeRelacionHtml(r) {
    const esq = esquemasDe(r.id), act = esq.filter((e) => e.activo), cer = esq.filter((e) => !e.activo);
    if (!esq.length) return '<div class="rl-esqs">Esquemas de pago de esta relación: <i>ninguno asociado</i>.</div>';
    return `<div class="rl-esqs">Esquemas de pago de esta relación: ${[...act.map((e) => `<b>${esc(esquemaTexto(e))}</b> (activo)`),
      ...cer.map((e) => `${esc(esquemaTexto(e))} (cerrado${e.fecha_fin ? ' el ' + fechaMx(e.fecha_fin) : ''})`)].join('; ')}.</div>`;
  }
  // Para Compensación: a qué relación pertenece cada esquema.
  function relacionDeEsquema(esqId) {
    if (!estado.personaId) return null;
    const e = (estado.todosEsquemas || []).find((x) => x.id === esqId);
    if (!e) return null;
    if (!e.relacion_laboral_id) return { texto: 'Sin relación laboral asignada', sin: true };
    const r = estado.relaciones.find((x) => x.id === e.relacion_laboral_id);
    if (!r) return { texto: 'Relación anulada' };
    return { texto: `${nombreEmpresa(r.empresa_id)} · ${rpCorto(r.registro_patronal_id)} · ingreso ${fechaMx(r.fecha_ingreso)}${r.estado === 'baja' ? ` · baja ${fechaMx(r.fecha_baja)}` : ''}` };
  }

  // Revisión de la empresa y el registro patronal elegidos (mismas reglas que la base).
  // BeeHuman decide el tipo; RH no elige entre «ingreso» y «reingreso»:
  //   bloqueado: ya hay una relación vigente en esa empresa y ese RP (la base también lo impide).
  //   adicional: ya hay una relación vigente en esa empresa con otro RP (se registra confirmándolo).
  //   reingreso: la persona trabajó antes en esa empresa y esa relación terminó.
  //   nuevo: nunca tuvo relación con esa empresa.
  function analizarIngreso(empId, rpId) {
    if (!empId) return {};
    const vig = relsEn(empId, 'vigente');
    const igual = vig.find((r) => (r.registro_patronal_id || null) === (rpId || null));
    const sinFecha = vig.find((r) => !r.fecha_ingreso && esMigrada(r.id));
    const accCorregir = (r) => `<button type="button" class="hl-btn2" data-ir-corregir="${r.id}">Corregir datos de esa relación</button>`;
    if (igual) {
      const migr = !igual.fecha_ingreso && esMigrada(igual.id);
      return { tipo: 'bloqueado', bloqueo: `<b>No se puede registrar.</b> La persona ya tiene una relación <b>vigente</b> en ${esc(nombreEmpresa(empId))} · ${esc(rpCorto(rpId))} (${igual.fecha_ingreso ? 'ingreso ' + fechaMx(igual.fecha_ingreso) : 'sin fecha de ingreso'}): solo puede haber una relación vigente por empresa y registro patronal.${
        migr ? ' Es una relación migrada a la que <b>solo le falta su fecha de ingreso</b>: captúrala con «Corregir datos».' : ' Si la persona dejó de laborar, primero registra su baja; si entra con otro registro patronal, elígelo arriba.'}<br>${migr ? accCorregir(igual) : ''}` };
    }
    if (vig.length) {
      const datos = vig.map((r) => `${esc(nombreEmpresa(r.empresa_id))} · ${esc(rpCorto(r.registro_patronal_id))} (${r.fecha_ingreso ? 'ingreso ' + fechaMx(r.fecha_ingreso) : 'sin fecha de ingreso'}${esquemasDe(r.id).filter((e) => e.activo).length ? `, con ${esquemasDe(r.id).filter((e) => e.activo).length} esquema(s) de pago` : ''})`).join('; ');
      return { tipo: 'adicional', adicional: `<p class="hl-aviso-sueldo" style="margin:0">Esta persona ya tiene una relación vigente en ${datos}. <b>Registrar este ingreso no la completa: crea una relación laboral adicional</b> en ${esc(rpCorto(rpId))}${rpId ? ', con su alta (08)' : ''}. La relación existente y sus esquemas de pago siguen vigentes.${sinFecha ? ' Si solo querías capturar la fecha de ingreso, cancela y usa «Corregir datos» en esa relación.' : ''}</p>
          <label class="bd-confirma"><input type="checkbox" name="confirma_adicional" data-requerida> <span>Entiendo que se creará una relación laboral adicional.</span></label>` };
    }
    const prev = ultimaBajaEn(empId);
    return { tipo: prev ? 'reingreso' : 'nuevo', prev };
  }
  // Otra relación de la persona con la misma fecha de ingreso: se dice dónde está.
  function fechaYaRegistrada(fecha, excluirId) {
    if (!fecha) return [];
    return estado.relaciones.filter((r) => r.id !== excluirId && r.fecha_ingreso && String(r.fecha_ingreso).slice(0, 10) === fecha);
  }
  const textoDonde = (r) => `${nombreEmpresa(r.empresa_id)} · ${rpCorto(r.registro_patronal_id)} (${r.estado === 'vigente' ? 'vigente' : 'baja ' + fechaMx(r.fecha_baja)})`;

  function ligarAcciones(raiz) {
    if (!raiz) return;
    raiz.querySelectorAll('[data-ir-corregir]').forEach((b) => { b.onclick = () => { ingresoEnCurso = null; formCorregir(b.dataset.irCorregir); }; });
    raiz.querySelectorAll('[data-ir-reingreso]').forEach((b) => { b.onclick = () => { ingresoEnCurso = null; formIngreso(null, b.dataset.irReingreso); }; });
    raiz.querySelectorAll('[data-definir-esquema]').forEach((b) => { b.onclick = () => definirEsquema(b.dataset.definirEsquema, b.dataset.fecha); });
  }

  // Condiciones del periodo. Los datos IMSS (SDI, tipos, jornada, UMF) solo se piden
  // cuando la relación lleva registro patronal: sin RP no hay alta ante el IMSS.
  const camposCondiciones = (pre) => `
        <div><label>Fecha de ingreso</label><input name="fecha" type="date" required></div>
        <div><label>Antigüedad reconocida (opcional)</label><input name="antig" type="date"></div>
        <div><label>Número interno (opcional)</label><input name="num" maxlength="10" value="${esc(pre.num || '')}"></div>
        <div class="ing-imss-campo"><label>SDI — salario diario integrado</label><input name="sdi" inputmode="decimal" placeholder="Ej. 450.00" autocomplete="off"></div>
        <div class="ing-imss-campo"><label>Tipo de trabajador</label><select name="tt">${opciones(TIPO_TRAB, pre.tt)}</select></div>
        <div class="ing-imss-campo"><label>Tipo de salario</label><select name="ts">${opciones(TIPO_SAL, pre.ts)}</select></div>
        <div class="ing-imss-campo"><label>Jornada IMSS</label><select name="jo">${opciones(JORNADA, pre.jo)}</select></div>
        <div class="ing-imss-campo"><label>UMF (opcional)</label><input name="umf" maxlength="3" inputmode="numeric" placeholder="3 dígitos"></div>
        <div><label>Motivo / nota (opcional)</label><input name="motivo"></div>`;

  // ---------- Formas de pago del nuevo periodo (esquemas) ----------
  // Una clasificación que exige NSS es de nómina IMSS: necesita registro patronal y
  // el esquema lleva el RP de la relación. Las demás (efectivo, transferencia,
  // honorarios…) se ligan a la relación sin RP y no piden datos de afiliación.
  const clasifs = () => (typeof clasificaciones !== 'undefined' ? clasificaciones : []).filter((c) => c.activo !== false)
    .slice().sort((a, b) => String(a.nombre).localeCompare(String(b.nombre), 'es'));
  const periods = () => (typeof periodicidades !== 'undefined' ? periodicidades : []).slice().sort((a, b) => String(a.nombre).localeCompare(String(b.nombre), 'es'));
  const esImss = (c) => !!(c && c.requiere_nss);
  function filaEsquemaHtml(v) {
    v = v || {};
    const op = (lista, sel) => '<option value="">Elige…</option>' + lista.map((x) => `<option value="${esc(x.id)}" ${x.id === sel ? 'selected' : ''}>${esc(x.nombre)}</option>`).join('');
    return `<div class="esq-fila">
      <div><label>Forma de pago</label><select data-esq="cl">${op(clasifs(), v.cl)}</select></div>
      <div><label>Periodicidad</label><select data-esq="per">${op(periods(), v.per)}</select></div>
      <div><label>Sueldo</label><select data-esq="mod"><option value="">Elige…</option><option value="bruto" ${v.mod === 'bruto' ? 'selected' : ''}>Bruto</option><option value="neto" ${v.mod === 'neto' ? 'selected' : ''}>Neto</option></select></div>
      <div><label>Importe por periodo</label><input data-esq="sueldo" inputmode="decimal" placeholder="Ej. 9,000.00" autocomplete="off" value="${esc(v.sueldo || '')}"></div>
      <div class="esq-quitar"><button type="button" class="hl-btn2" data-esq-quitar title="Quitar esta forma de pago">Quitar</button></div>
      <div class="esq-nota"></div></div>`;
  }
  const leerFilas = (f) => [...f.querySelectorAll('.esq-fila')].map((d) => {
    const g = (k) => { const el = d.querySelector(`[data-esq="${k}"]`); return el ? (el.value || '').trim() : ''; };
    return { el: d, cl: g('cl'), per: g('per'), mod: g('mod'), sueldo: g('sueldo') };
  });
  const filaVacia = (x) => !x.cl && !x.per && !x.mod && !x.sueldo;
  function notasFilas(f) {
    const conRp = !!val(f, 'rp');
    leerFilas(f).forEach((x) => {
      const c = clasifs().find((k) => k.id === x.cl), n = x.el.querySelector('.esq-nota');
      if (!n) return;
      n.textContent = !c ? '' : esImss(c)
        ? (conRp ? `Nómina IMSS: se liga al registro patronal ${textoRP(val(f, 'rp')) || ''} de esta relación.` : 'Nómina IMSS: necesita un registro patronal (sección 2).')
        : 'Sin datos de afiliación al IMSS: se liga a esta relación sin registro patronal.';
      n.classList.toggle('err', !!c && esImss(c) && !conRp);
    });
  }

  // Datos del expediente: se muestran y se editan en sus secciones; nada se vuelve a capturar.
  function expedienteHtml() {
    const p = detalleActual || {};
    const d = (x) => esc(x == null || x === '' ? '—' : x);
    return `<div class="ri-ref"><h5>Expediente ${d(p.empleado_id)} · ${d(p.nombre_completo)}</h5>
      <div class="rl-campos"><div class="rl-col">${campoRl('CURP', d(p.curp))}${campoRl('RFC', d(p.rfc))}${campoRl('NSS', d(p.nss))}${campoRl('Código postal fiscal', d(p.cp_fiscal))}</div>
      <div class="rl-col">${campoRl('Contacto de emergencia', d([p.contacto_emergencia_nombre, p.contacto_emergencia_parentesco].filter(Boolean).join(' · ')))}${campoRl('Teléfono de emergencia', d(p.contacto_emergencia_telefono))}${campoRl('No. FONACOT', d(p.no_fonacot))}</div></div>
      <p class="ri-nota">Es el mismo expediente: no se crea otra persona. Si algún dato cambió, actualízalo; lo que captures aquí se conserva.
      <button type="button" class="hl-btn2" data-ir-seccion="personal" style="margin-left:6px">Actualizar datos personales</button>
      <button type="button" class="hl-btn2" data-ir-seccion="contacto">Actualizar contacto</button>
      <button type="button" class="hl-btn2" data-ir-seccion="prestaciones">Actualizar FONACOT</button></p></div>`;
  }

  // Antecedentes de la persona en OTRAS empresas del grupo (referencia en un ingreso nuevo).
  function antecedentesGrupo(empId) {
    const otras = estado.relaciones.filter((r) => r.estado === 'baja' && r.empresa_id !== empId);
    if (!otras.length) return '';
    return `<div class="ri-ref"><h5>Antecedentes de esta persona en el grupo (referencia)</h5>
      <ul class="bd-lista" style="margin:0">${otras.map((r) => `<li>${esc(nombreEmpresa(r.empresa_id))} · ${esc(rpCorto(r.registro_patronal_id))} · ingreso ${fechaMx(r.fecha_ingreso)} · baja ${fechaMx(r.fecha_baja)}</li>`).join('')}</ul>
      <p class="ri-nota">La relación con cada empresa se registra por separado; las relaciones anteriores no cambian.</p></div>`;
  }

  // Relación anterior en la empresa elegida (referencia en un reingreso): visible, no se copia.
  function referenciaAnterior(empId) {
    const r = ultimaBajaEn(empId);
    if (!r) return '';
    const v = (x) => esc(x == null || x === '' ? '—' : x);
    const esq = esquemasDe(r.id);
    const izq = [campoRl('Registro patronal', v(textoRP(r.registro_patronal_id) || 'Sin registro patronal')), campoRl('Ingreso', fechaMx(r.fecha_ingreso)),
      campoRl('Antigüedad reconocida', fechaMx(r.fecha_reconocimiento_antiguedad)),
      campoRl('Baja', `${fechaMx(r.fecha_baja)}${r.causa_baja ? '<small>' + esc(valorLegible('causa_baja', r.causa_baja)) + '</small>' : ''}`),
      campoRl('SDI', r.sdi != null ? dinero(r.sdi) : '—')];
    const der = [campoRl('Tipo de trabajador', v(valorLegible('tipo_trabajador', r.tipo_trabajador))), campoRl('Tipo de salario', v(valorLegible('tipo_salario', r.tipo_salario))),
      campoRl('Jornada IMSS', v(valorLegible('jornada', r.jornada))), campoRl('UMF', v(r.umf)), campoRl('Número interno', v(r.numero_interno))];
    return `<details class="ri-ref" data-ref-relacion="${r.id}"><summary><b>Relación anterior en ${esc(nombreEmpresa(empId))}</b> · ingreso ${fechaMx(r.fecha_ingreso)} · baja ${fechaMx(r.fecha_baja)} (ver detalle)</summary>
      <div class="rl-campos"><div class="rl-col">${izq.join('')}</div><div class="rl-col">${der.join('')}</div></div>
      <div class="rl-esqs">Esquemas de pago de ese periodo: ${esq.length ? esq.map((e) => `${esc(esquemaTexto(e))} (${e.activo ? 'activo' : 'cerrado' + (e.fecha_fin ? ' el ' + fechaMx(e.fecha_fin) : '')})`).join('; ') : '<i>ninguno</i>'}.</div>
      <p class="ri-nota">No se copian ni se reactivan: la relación anterior, sus movimientos y sus esquemas quedan como están.</p></details>
      <button type="button" class="hl-btn2" data-copiar-anterior="${r.id}" style="margin:0 0 6px">Usar las condiciones anteriores como punto de partida</button>`;
  }

  // Tipo detectado, en una línea, para que RH sepa qué se va a registrar.
  function textoTipo(an, empId) {
    const emp = esc(nombreEmpresa(empId));
    if (an.tipo === 'reingreso') return `<b>Reingreso a ${emp}.</b> Trabajó ahí del ${fechaMx(an.prev.fecha_ingreso)} al ${fechaMx(an.prev.fecha_baja)} (${esc(rpCorto(an.prev.registro_patronal_id))}). Se abre un periodo nuevo; la relación anterior queda como está.`;
    if (an.tipo === 'nuevo') return `<b>Ingreso nuevo a ${emp}.</b> La persona no ha tenido relación con esta empresa.`;
    if (an.tipo === 'adicional') return `<b>Relación adicional en ${emp}.</b>`;
    return '';
  }

  // =====================================================================
  // Registrar ingreso / reingreso: un solo formulario. RH elige la empresa
  // y BeeHuman determina si es ingreso nuevo, reingreso o relación adicional.
  // =====================================================================
  function formIngreso(borrador, empPre) {
    const p = detalleActual || {};
    const emps = empresasActivas();
    const pre = empPre || (borrador && borrador.empresa) || (emps.some((e) => e.id === p.empresa_id) ? p.empresa_id : '');
    const primera = !estado.relaciones.length;
    const paso = (n, tit, sub, cuerpo) => `<li class="ri-paso" data-paso="${n}" data-estado="pend"><div class="ri-paso-cab">
        <span class="ri-num" aria-hidden="true">${n}</span><div class="ri-paso-tit"><h4>${tit}</h4><p>${sub}</p></div>
        <span class="ri-estado" data-estado="pend">Pendiente</span></div><div class="ri-cuerpo">${cuerpo}</div></li>`;
    montar('hl-form-ingreso', `<div class="ri-cab"><div><h3 class="ri-titulo">Registrar ingreso / reingreso</h3>
      <p class="ri-lead">Elige la empresa: BeeHuman indica si es un ingreso nuevo o un reingreso. Las relaciones anteriores y sus esquemas de pago no cambian ni se reactivan.</p></div>
      <span class="ri-global" aria-live="polite"></span></div>
      <ol class="ri-pasos">
      ${paso(1, 'Persona', 'Expediente existente y datos de identificación', expedienteHtml())}
      ${paso(2, 'Empresa y registro patronal', 'Empresa a la que ingresa; BeeHuman detecta si es ingreso o reingreso', `<div class="hl-grid">
        <div><label>Empresa</label><select name="empresa" required><option value="">Elige…</option>${emps.map((e) => `<option value="${e.id}" ${e.id === pre ? 'selected' : ''}>${esc(e.nombre)}</option>`).join('')}</select></div>
        <div><label>Registro patronal</label><select name="rp"></select></div>
      </div><div class="ing-tipo"></div><div class="ing-aviso"></div><div class="ri-ref-caja"></div>`)}
      ${paso(3, 'Condiciones laborales', 'Fecha de ingreso y, con registro patronal, SDI, jornada y datos de afiliación', `<p class="hint ing-imss-ayuda" style="margin:0 0 8px">Con registro patronal se piden los datos del alta ante el IMSS. ${esc(SDI_AYUDA)}</p>
      <div class="hl-grid">${camposCondiciones({ tt: '1', ts: '0', jo: '0', num: primera ? p.numero_interno_trabajador : '' })}</div><div class="ing-fecha"></div>`)}
      ${paso(4, 'Formas de pago', 'IMSS, efectivo, transferencia, honorarios o una combinación', `<p class="hint" style="margin:0 0 8px">Una o varias (IMSS, efectivo, transferencia, honorarios…). Se ligan a este nuevo periodo e inician en la fecha de ingreso. Puedes dejarlas para después en Compensación.</p>
      <div class="esq-filas"></div>
      <button type="button" class="hl-btn2" data-esq-agregar style="margin:0">Agregar otra forma de pago</button>`)}
      ${paso(5, 'Prestaciones y créditos', 'Referencia a los datos existentes y módulos relacionados', `<p class="hint" style="margin:0">FONACOT se revisa en el expediente (sección 1). INFONAVIT y otros descuentos se registrarán en el módulo de créditos y deducciones (pendiente).</p>`)}
      </ol>
      <div class="ri-pie"><div class="ing-err" role="alert" aria-live="assertive"></div>
      ${botones('Registrar ingreso')}</div>`, (f) => enviarIngreso(f));
    const f = document.querySelector('#hl-form-ingreso form'); if (!f) return;
    f.dataset.siempreActivo = '1'; // nunca un botón que «no hace nada»: al enviar se dice qué falta
    f.classList.add('ri-form');
    // Estado visual de cada etapa (solo presentación; las reglas viven en revisarIngreso y en la base).
    const pintarEtapas = () => {
      const pon = (n, e, txt) => {
        const li = f.querySelector(`.ri-paso[data-paso="${n}"]`); if (!li) return;
        const pill = li.querySelector('.ri-estado');
        if (li.dataset.estado !== e) li.dataset.estado = e;
        if (pill.dataset.estado !== e) pill.dataset.estado = e;
        if (pill.textContent !== txt) pill.textContent = txt;
      };
      const falta = (n) => !!f.querySelector(`.ri-paso[data-paso="${n}"] .hl-falta:not([title])`);
      const v = (n) => (f.querySelector(`[name=${n}]`) || {}).value || '';
      pon(1, 'ok', 'Identificada');
      const tipoTxt = f.querySelector('.ing-tipo-txt');
      const conf = f.querySelector('[name=confirma_adicional]');
      if (f.querySelector('.ing-aviso .ri-bloqueo') || falta(2)) pon(2, 'atencion', 'Requiere atención');
      else if (!v('empresa')) pon(2, 'pend', 'Pendiente');
      else if (conf && !conf.checked) pon(2, 'atencion', 'Confirma la relación adicional');
      else pon(2, 'ok', tipoTxt && tipoTxt.classList.contains('reingreso') ? 'Reingreso' : tipoTxt && tipoTxt.classList.contains('adicional') ? 'Relación adicional' : 'Ingreso nuevo');
      if (falta(3)) pon(3, 'atencion', 'Requiere atención');
      else pon(3, v('fecha') && (!v('rp') || v('sdi')) ? 'ok' : 'pend', v('fecha') && (!v('rp') || v('sdi')) ? 'Completo' : 'Pendiente');
      const nPago = [...f.querySelectorAll('.esq-fila [data-esq=sueldo]')].filter((i) => i.value.trim()).length;
      if (falta(4) || f.querySelector('.esq-fila .esq-nota.err')) pon(4, 'atencion', 'Requiere atención');
      else pon(4, nPago ? 'ok' : 'opc', nPago ? (nPago === 1 ? '1 forma de pago' : nPago + ' formas de pago') : 'Opcional');
      pon(5, 'info', 'Informativo');
      const g = f.querySelector('.ri-global');
      const est = [2, 3, 4].map((n) => f.querySelector(`.ri-paso[data-paso="${n}"]`).dataset.estado);
      const pend = [[2, 'empresa'], [3, 'condiciones']].filter(([n]) => est[n - 2] === 'pend').map(([, t]) => t);
      const [ge, gt] = est.includes('atencion') ? ['atencion', 'Revisa las etapas marcadas'] : pend.length ? ['pend', 'Falta: ' + pend.join(' y ')] : ['ok', 'Listo para registrar'];
      if (g.dataset.estado !== ge) g.dataset.estado = ge;
      if (g.textContent !== gt) g.textContent = gt;
    };
    let etapasRaf = 0;
    const programarEtapas = () => { if (!etapasRaf) etapasRaf = requestAnimationFrame(() => { etapasRaf = 0; pintarEtapas(); }); };
    ['input', 'change'].forEach((t) => f.addEventListener(t, programarEtapas));
    new MutationObserver((ms) => { if (ms.some((m) => !m.target.closest || !m.target.closest('.ri-paso-cab, .ri-global'))) programarEtapas(); })
      .observe(f, { subtree: true, childList: true, attributes: true, attributeFilter: ['class', 'style'] });
    programarEtapas();
    const selE = f.querySelector('[name=empresa]'), selR = f.querySelector('[name=rp]');
    const caja = f.querySelector('.ing-aviso'), ref = f.querySelector('.ri-ref-caja'), avFecha = f.querySelector('.ing-fecha'), tipo = f.querySelector('.ing-tipo');
    const filas = f.querySelector('.esq-filas');
    const agregarFila = (v) => { filas.insertAdjacentHTML('beforeend', filaEsquemaHtml(v)); notasFilas(f); };
    const llenarRP = (rpSel) => {
      const lista = rps.filter((r) => r.empresa_id === selE.value && r.activo !== false);
      const prev = ultimaBajaEn(selE.value);
      const pref = rpSel !== undefined ? rpSel : prev ? (prev.registro_patronal_id || '') : (p.empresa_id === selE.value ? p.registro_patronal_id : undefined);
      selR.innerHTML = '<option value="">Sin registro patronal (sin IDSE)</option>' + lista.map((r) => `<option value="${r.id}">${esc(r.registro_patronal)}</option>`).join('');
      if (pref != null && [...selR.options].some((o) => o.value === pref)) selR.value = pref;
      else if (lista.length) selR.value = lista[0].id;
      revisar();
    };
    const revisar = () => {
      const m = document.getElementById('rl-msg'); if (m && m.classList.contains('err')) { m.innerHTML = ''; m.className = 'hl-msg'; }
      const an = analizarIngreso(selE.value, selR.value || null);
      const confirmado = (f.querySelector('[name=confirma_adicional]') || {}).checked;
      tipo.innerHTML = selE.value ? `<p class="ing-tipo-txt ${an.tipo || ''}">${textoTipo(an, selE.value)}</p>` : '<p class="hint" style="margin:6px 0">Elige la empresa en la que trabajará.</p>';
      caja.innerHTML = an.bloqueo ? `<div class="ri-bloqueo">${an.bloqueo}</div>` : (an.adicional || '');
      if (confirmado && caja.querySelector('[name=confirma_adicional]')) caja.querySelector('[name=confirma_adicional]').checked = true;
      ligarAcciones(caja);
      if (ref) ref.innerHTML = an.tipo === 'reingreso' ? referenciaAnterior(selE.value) : (an.tipo === 'nuevo' ? antecedentesGrupo(selE.value) : '');
      const conRp = !!selR.value;
      f.querySelectorAll('.ing-imss-campo').forEach((d) => { d.style.display = conRp ? '' : 'none'; });
      f.querySelector('.ing-imss-ayuda').style.display = conRp ? '' : 'none';
      const bt = f.querySelector('button[type=submit]'); if (bt) bt.textContent = an.tipo === 'reingreso' ? 'Registrar reingreso' : 'Registrar ingreso';
      if (avFecha) {
        const fe = val(f, 'fecha'), otras = fechaYaRegistrada(fe, null).filter((r) => r.empresa_id === selE.value);
        avFecha.innerHTML = otras.length ? `<div class="fd-aviso">La fecha ${fechaMx(fe)} ya está registrada como ingreso de: ${otras.map((r) => '<b>' + esc(textoDonde(r)) + '</b>').join('; ')}. Este registro crea un periodo distinto; revisa que no sea la misma relación.</div>` : '';
      }
      notasFilas(f);
    };
    selE.onchange = () => llenarRP(); selR.addEventListener('change', revisar);
    f.querySelector('[name=fecha]').addEventListener('change', revisar);
    const sdiIng = f.querySelector('[name=sdi]');
    sdiIng.addEventListener('input', () => formatearAlEscribir(sdiIng));
    sdiIng.addEventListener('blur', () => { const v = leerImporte(sdiIng.value); if (v != null && !isNaN(v)) sdiIng.value = formatoImporte(v); });
    f.addEventListener('input', (ev) => { if (ev.target.matches('[data-esq="sueldo"]')) formatearAlEscribir(ev.target); });
    f.addEventListener('change', (ev) => { if (ev.target.matches('[data-esq]')) notasFilas(f); });
    f.addEventListener('click', (ev) => {
      if (ev.target.closest('[data-esq-agregar]')) { agregarFila(); f.dataset.sucio = '1'; guardarBorrador(); return; }
      const q = ev.target.closest('[data-esq-quitar]');
      if (q) { q.closest('.esq-fila').remove(); if (!filas.children.length) agregarFila(); f.dataset.sucio = '1'; guardarBorrador(); return; }
      const s = ev.target.closest('[data-ir-seccion]');
      if (s && typeof cambiarSeccionDetalle === 'function') { cambiarSeccionDetalle(s.dataset.irSeccion); return; }
      const b = ev.target.closest('[data-copiar-anterior]'); if (!b) return;
      const r = estado.relaciones.find((x) => x.id === b.dataset.copiarAnterior); if (!r) return;
      [['tt', r.tipo_trabajador], ['ts', r.tipo_salario], ['jo', r.jornada], ['umf', r.umf], ['num', r.numero_interno]].forEach(([k, v]) => {
        const el = f.querySelector(`[name="${k}"]`); if (el && v != null) { el.value = v; el.classList.add('hl-falta'); el.title = 'Copiado de la relación anterior: revísalo'; }
      });
      f.dataset.sucio = '1'; guardarBorrador();
      mensaje('Se copiaron como punto de partida (marcados en amarillo): tipo de trabajador, salario, jornada, UMF y número interno. Revísalos; el SDI y las formas de pago se capturan de nuevo.', true, null, 'rl-msg');
    });
    // Borrador: si la ficha se vuelve a pintar (p. ej. al guardar datos personales), se restaura todo.
    const guardarBorrador = () => {
      const valores = {}, marcas = {};
      f.querySelectorAll('input[name],select[name]').forEach((el) => { if (el.type === 'checkbox') marcas[el.name] = el.checked; else valores[el.name] = el.value; });
      ingresoEnCurso = { personaId: estado.personaId, empresa: selE.value, valores, marcas,
        esquemas: leerFilas(f).map(({ cl, per, mod, sueldo }) => ({ cl, per, mod, sueldo })) };
    };
    f.addEventListener('input', guardarBorrador); f.addEventListener('change', guardarBorrador);
    f.querySelector('[data-cancelar]').addEventListener('click', () => { ingresoEnCurso = null; });
    (borrador && borrador.esquemas && borrador.esquemas.length ? borrador.esquemas : [null]).forEach((v) => agregarFila(v));
    if (borrador && borrador.valores) {
      if (borrador.valores.empresa) selE.value = borrador.valores.empresa;
      llenarRP(borrador.valores.rp);
      Object.entries(borrador.valores).forEach(([k, v]) => { if (k === 'empresa' || k === 'rp') return; const el = f.querySelector(`[name="${k}"]`); if (el) el.value = v; });
      revisar();
      Object.entries(borrador.marcas || {}).forEach(([k, v]) => { const el = f.querySelector(`[name="${k}"]`); if (el) el.checked = v; });
      f.dataset.sucio = '1';
      revisar();
    } else llenarRP();
    ligarEnvio(f);
  }

  // Revisión completa antes de enviar: junta TODO lo que falta, con su sección.
  function revisarIngreso(f) {
    const faltan = [], marcar = [];
    const emp = val(f, 'empresa'), rp = val(f, 'rp') || null, fecha = val(f, 'fecha');
    const campo = (n) => f.querySelector(`[name="${n}"]`);
    const an = analizarIngreso(emp, rp);
    if (!emp) { faltan.push('Elige la <b>empresa</b> (sección 2).'); marcar.push(campo('empresa')); }
    if (an.bloqueo) faltan.push('Ya existe una relación vigente en esa empresa y registro patronal (sección 2): revisa el aviso en rojo.');
    if (an.adicional && !(campo('confirma_adicional') || {}).checked) { faltan.push('Confirma que se creará una <b>relación laboral adicional</b> (sección 2).'); marcar.push(campo('confirma_adicional')); }
    if (!fecha) { faltan.push('Captura la <b>fecha de ingreso</b> (sección 3).'); marcar.push(campo('fecha')); }
    else if (an.tipo === 'reingreso' && an.prev && an.prev.fecha_baja && fecha <= String(an.prev.fecha_baja).slice(0, 10)) {
      faltan.push(`La <b>fecha de ingreso</b> debe ser posterior a la baja anterior en ${esc(nombreEmpresa(emp))} (${fechaMx(an.prev.fecha_baja)}) (sección 3).`); marcar.push(campo('fecha'));
    }
    const sdi = leerImporte(val(f, 'sdi'));
    if (rp) {
      if (sdi == null) { faltan.push('Captura el <b>SDI</b>: la relación lleva registro patronal y genera el alta ante el IMSS (sección 3).'); marcar.push(campo('sdi')); }
      else if (isNaN(sdi) || sdi <= 0) { faltan.push('El <b>SDI</b> debe ser un importe mayor a cero, con hasta 2 decimales (sección 3).'); marcar.push(campo('sdi')); }
      [['tt', 'tipo de trabajador'], ['ts', 'tipo de salario'], ['jo', 'jornada IMSS']].forEach(([k, t]) => { if (!val(f, k)) { faltan.push(`Elige el <b>${t}</b> (sección 3).`); marcar.push(campo(k)); } });
      if (val(f, 'umf') && !/^\d{3}$/.test(val(f, 'umf'))) { faltan.push('La <b>UMF</b> lleva 3 dígitos (sección 3).'); marcar.push(campo('umf')); }
    }
    const esquemas = [];
    leerFilas(f).forEach((x, i) => {
      if (filaVacia(x)) return;
      const n = `forma de pago ${i + 1}`, c = clasifs().find((k) => k.id === x.cl);
      const sel = (k) => x.el.querySelector(`[data-esq="${k}"]`);
      if (!c) { faltan.push(`Elige el tipo de la <b>${n}</b> (sección 4).`); marcar.push(sel('cl')); }
      if (!x.per) { faltan.push(`Elige la periodicidad de la <b>${n}</b> (sección 4).`); marcar.push(sel('per')); }
      if (!x.mod) { faltan.push(`Indica si el sueldo de la <b>${n}</b> es bruto o neto (sección 4).`); marcar.push(sel('mod')); }
      const s = leerImporte(x.sueldo);
      if (s == null || isNaN(s) || s <= 0) { faltan.push(`Captura el importe de la <b>${n}</b>: un número mayor a cero, con hasta 2 decimales (sección 4).`); marcar.push(sel('sueldo')); }
      if (c && esImss(c) && !rp) { faltan.push(`La <b>${n}</b> (${esc(c.nombre)}) es de nómina IMSS: elige un registro patronal (sección 2) o cambia la forma de pago.`); marcar.push(sel('cl'), campo('rp')); }
      if (c && typeof requisitosFaltantesRegistroPago === 'function') {
        const req = requisitosFaltantesRegistroPago(c, detalleActual || {});
        if (req.length) faltan.push(`Para la <b>${n}</b> (${esc(c.nombre)}) el expediente debe tener ${esc(req.join(', '))} completos y válidos: actualízalos en «Datos personales» (sección 1).`);
      }
      if (c) esquemas.push({ c, per: x.per, mod: x.mod, sueldo: s });
    });
    return { faltan, marcar: marcar.filter(Boolean), an, emp, rp, fecha, sdi, esquemas };
  }
  function mostrarFaltantes(f, rev) {
    f.querySelectorAll('.hl-falta').forEach((el) => { if (!el.title) el.classList.remove('hl-falta'); });
    rev.marcar.forEach((el) => el.classList.add('hl-falta'));
    const caja = f.querySelector('.ing-err');
    caja.innerHTML = `<b>Falta${rev.faltan.length > 1 ? 'n' : ''} ${rev.faltan.length} dato${rev.faltan.length > 1 ? 's' : ''} para registrar:</b><ul>${rev.faltan.map((t) => `<li>${t}</li>`).join('')}</ul>`;
    caja.className = 'ing-err activo';
    caja.scrollIntoView({ block: 'nearest' });
  }

  // Envío: relación laboral (con su 08 si lleva RP) y después sus formas de pago.
  // LIMITACIÓN CONOCIDA (fase A): son dos pasos, no atómicos. Si una forma de pago
  // falla, la relación ya quedó registrada y el mensaje dice cuál falta.
  async function enviarIngreso(f) {
    const rev = revisarIngreso(f);
    if (rev.faltan.length) { mostrarFaltantes(f, rev); return; }
    const caja = f.querySelector('.ing-err'); caja.innerHTML = ''; caja.className = 'ing-err';
    const { emp, rp, fecha, sdi, an } = rev;
    const sbc = sdi == null || !rp ? null : sbcDeSdi(sdi, (await topeEnRp(fecha, rp)).tope);
    const { data: relId, error } = await sb.rpc('laboral_registrar_ingreso', {
      p_personal_id: estado.personaId, p_empresa_id: emp, p_registro_patronal_id: rp,
      p_fecha_ingreso: fecha, p_fecha_reconocimiento_antiguedad: val(f, 'antig') || null,
      p_sbc: rp ? sbc : null, p_sdi: rp ? sdi : null, p_tipo_trabajador: rp ? (val(f, 'tt') || null) : null, p_tipo_salario: rp ? (val(f, 'ts') || null) : null,
      p_jornada: rp ? (val(f, 'jo') || null) : null, p_umf: rp ? (val(f, 'umf') || null) : null, p_numero_interno: val(f, 'num') || null, p_motivo: val(f, 'motivo') || null,
    });
    if (error) { mostrarFaltantes(f, { faltan: [esc(msgError(error))], marcar: [] }); return; }
    const guardados = [], fallidos = [];
    for (const e of rev.esquemas) {
      const fila = { personal_id: estado.personaId, clasificacion_id: e.c.id, periodicidad_id: e.per, sueldo: e.sueldo, modalidad_sueldo: e.mod,
        empresa_id: emp, registro_patronal_id: esImss(e.c) ? rp : null, fecha_inicio: fecha, relacion_laboral_id: relId };
      const id = typeof nuevoUuidRegistroPago === 'function' ? nuevoUuidRegistroPago() : null; if (id) fila.id = id;
      let r; try { r = await sb.from('personal_registros_pago').insert(fila); } catch (x) { r = { error: x }; }
      const txt = `${esc(e.c.nombre)} · ${dinero(e.sueldo)} ${esc(e.mod)} · ${esc(nombreEn(periods(), e.per) || '')}`;
      if (r.error) fallidos.push(`${txt} (${esc(msgError(r.error))})`); else guardados.push(txt);
    }
    ingresoEnCurso = null;
    const donde = `${esc(nombreEmpresa(emp))} · ${esc(rpCorto(rp))}`;
    const html = `<b>${an.tipo === 'reingreso' ? 'Reingreso registrado' : 'Ingreso registrado'}</b> en ${donde} con fecha ${fechaMx(fecha)}. `
      + (rp ? `El alta (08) quedó <b>pendiente</b> en la bandeja IDSE del registro patronal <b>${esc(textoRP(rp))}</b>.${enlaceBandeja(rp)}` : 'Sin registro patronal: no genera movimiento IDSE.')
      + (an.tipo === 'reingreso' ? '<br>La relación anterior y su historia no cambiaron; sus esquemas de pago siguen cerrados.' : '')
      + (guardados.length ? `<br><b>Formas de pago registradas:</b> ${guardados.join('; ')}.` : '')
      + (fallidos.length ? `<br><b>No se guardó:</b> ${fallidos.join('; ')}. La relación sí quedó registrada. <button type="button" class="hl-btn2" data-definir-esquema="${esc(relId)}" data-fecha="${esc(fecha)}">Agregar la forma de pago en Compensación</button>`
        : !guardados.length ? `<br>Sin forma de pago registrada. <button type="button" class="hl-btn2" data-definir-esquema="${esc(relId)}" data-fecha="${esc(fecha)}">Definir la forma de pago</button>` : '');
    await reabrir({ html, error: fallidos.length > 0 });
  }

  // Paso 2: Compensación con el alta de esquema ya ligada a la nueva relación (empresa, RP y fecha).
  async function definirEsquema(relId, fecha) {
    const r = estado.relaciones.find((x) => x.id === relId);
    if (!r || typeof abrirFormRegistroPago !== 'function') return;
    if (typeof cambiarSeccionDetalle === 'function') cambiarSeccionDetalle('compensacion');
    for (let i = 0; i < 50 && (typeof detalleRegistrosPagoEstado === 'undefined' || detalleRegistrosPagoEstado !== 'ok'); i++) await new Promise((res) => setTimeout(res, 100));
    abrirFormRegistroPago();
    const form = document.getElementById('rp-form'), se = document.getElementById('rp-empresa');
    if (!form || form.style.display === 'none' || !se) return;
    se.value = r.empresa_id; se.dispatchEvent(new Event('change'));
    const sr = document.getElementById('rp-registro-patronal'); if (sr) sr.value = r.registro_patronal_id || '';
    const fi = document.getElementById('rp-fecha-inicio'); if (fi && (fecha || r.fecha_ingreso)) fi.value = fecha || r.fecha_ingreso;
    if (typeof mostrarToastRegistrosPago === 'function') mostrarToastRegistrosPago(`Nuevo esquema para la relación ${nombreEmpresa(r.empresa_id)} · ${rpCorto(r.registro_patronal_id)} (ingreso ${fechaMx(r.fecha_ingreso)}). Elige clasificación, periodicidad, modalidad y sueldo: no se copian del periodo anterior.`, 'ok');
    form.scrollIntoView({ block: 'center' });
  }

  // «Nuevo empleado»: si la CURP, el RFC o el NSS ya existen, no se crea otra persona.
  // Devuelve null si no hay coincidencias. Si las hay, agrupa por persona:
  //   unica: todas las coincidencias son de UNA persona → se puede abrir ese expediente.
  //   conflicto: CURP, RFC o NSS apuntan a personas distintas → se bloquea y se listan
  //   todas para revisión; nunca se elige una (ni la primera) automáticamente.
  //   error: no se pudo verificar → se bloquea el alta (no se arriesga un duplicado).
  // Solo consulta: no crea ni modifica fichas.
  const normId = (v) => String(v == null ? '' : v).trim().toUpperCase();
  async function expedienteExistente(nuevo) {
    const filtros = [['curp', nuevo.curp], ['rfc', nuevo.rfc], ['nss', nuevo.nss]].map(([k, v]) => [k, normId(v)]).filter(([, v]) => v);
    if (!filtros.length) return null;
    if (filtros.some(([, v]) => !/^[A-Z0-9Ñ&]+$/.test(v))) return { error: true };
    let data = null, error = null;
    try { ({ data, error } = await sb.from('personal').select('id,empleado_id,nombre_completo,curp,rfc,nss,estatus').or(filtros.map(([k, v]) => `${k}.eq.${v}`).join(','))); }
    catch (e) { error = e; }
    if (error) return { error: true };
    const filas = (data || []).map((p) => ({ ...p, coincide: filtros.filter(([k, v]) => normId(p[k]) === v).map(([k]) => k.toUpperCase()) }))
      .filter((p) => p.coincide.length)
      .sort((x, y) => String(x.empleado_id || '').localeCompare(String(y.empleado_id || '')));
    if (!filas.length) return null;
    // Identificadores capturados que no coinciden con la persona encontrada (solo informativo).
    const distintos = (p) => filtros.filter(([k, v]) => p[k] && normId(p[k]) !== v).map(([k, v]) => ({ campo: k.toUpperCase(), capturado: v, expediente: normId(p[k]) }));
    if (filas.length === 1) return { unica: true, persona: filas[0], coincide: filas[0].coincide, distintos: distintos(filas[0]) };
    return { conflicto: true, personas: filas };
  }
  // Texto del aviso en «Alta de personal» (lo pinta index.html).
  function avisoExpedienteExistente(r) {
    const e = (v) => esc(v == null || v === '' ? '—' : v);
    const ficha = (p) => `<b>${e(p.empleado_id)} · ${e(p.nombre_completo)}</b> (estatus ${e(p.estatus)})`;
    if (r.error) return { html: '<b>No se dio de alta:</b> no se pudo verificar si la CURP, el RFC o el NSS ya pertenecen a otro expediente. Revisa la conexión y vuelve a intentarlo.' };
    if (r.conflicto) {
      return { html: `<b>No se dio de alta: los datos de identidad apuntan a expedientes distintos.</b> Ninguno se abrió ni se modificó. Revísalos antes de continuar:
        <ul style="margin:6px 0 4px;padding-left:18px">${r.personas.map((p) => `<li data-exp-conflicto="${esc(p.id)}">${ficha(p)}: coincide ${p.coincide.join(', ')}</li>`).join('')}</ul>
        Puede ser un error de captura o una ficha duplicada. Búscalos por su ID en Personal; si la persona regresa a trabajar, registra el reingreso en el expediente correcto.` };
    }
    const p = r.persona;
    return { personaId: p.id, html: `<b>No se creó otra persona:</b> ya existe el expediente ${ficha(p)} con la misma ${r.coincide.join(', ')}.${
      r.distintos.length ? ` <span style="display:block;margin-top:4px">Ojo: ${r.distintos.map((d) => `el ${d.campo} capturado (${esc(d.capturado)}) es distinto al del expediente (${esc(d.expediente)})`).join('; ')}. Revísalo en el expediente.</span>` : ''}
      Si la persona regresa a trabajar, registra su reingreso en ese expediente. <button type="button" class="primary" id="btn-alta-abrir-existente" style="margin:6px 0 0">Abrir expediente para registrar el reingreso</button>` };
  }
  async function abrirExpedienteParaReingreso(personaId) {
    abrirReingresoAl = { personaId, nota: 'Expediente existente: registra aquí el regreso de la persona. No se creó otra ficha.' };
    if (typeof abrirDetalle === 'function') await abrirDetalle(personaId, 'laboral');
  }

  // ¿La relación admite capturar fecha de ingreso en «Corregir datos»? (misma regla que la base)
  const esMigrada = (relId) => estado.eventos.some((e) => e.relacion_id === relId && ['ingreso', 'reingreso'].includes(e.tipo) && e.estado === 'vigente' && e.origen === 'migracion')
    && !estado.eventos.some((e) => e.relacion_id === relId && e.tipo === 'modificacion_salario' && e.estado === 'vigente');
  const textoRelacion = (r) => `${nombreEmpresa(r.empresa_id)} · ${textoRP(r.registro_patronal_id) ? 'RP ' + textoRP(r.registro_patronal_id) : 'sin registro patronal'} · ingreso ${fechaMx(r.fecha_ingreso)}`;
  const notaBaja = (rpId) => rpId
    ? `Se desactivan sus esquemas de pago. Queda la baja (02) pendiente en la bandeja IDSE del registro patronal ${esc(textoRP(rpId))}; el archivo se genera desde la bandeja cuando lo decidas.`
    : 'Se desactivan sus esquemas de pago. Sin registro patronal: no genera movimiento IDSE.';
  // Qué esquemas de pago desactiva la baja de una relación (los ligados a ella y activos).
  const esquemasQueDesactiva = (r) => (estado.esquemas || []).filter((e) => e.relacion_laboral_id === r.id);
  const textoEsquemasBaja = (r) => {
    const l = esquemasQueDesactiva(r);
    return l.length ? `<small class="bd-esq">Se desactiva${l.length > 1 ? 'n' : ''}: ${l.map((e) => esc(esquemaTexto(e))).join('; ')}.</small>`
      : '<small class="bd-esq sin">No tiene esquemas de pago activos asociados: no se desactiva ninguno.</small>';
  };
  // Esquemas activos SIN relación que podrían ser de esa empresa: la baja no los desactiva.
  const pendientesDeEmpresa = (empId) => (estado.pendientes || []).filter((e) => !e.empresa_id || e.empresa_id === empId);
  const avisoPendientes = (lista) => `<b>Antes de dar de baja:</b> ${lista.length === 1 ? 'hay 1 esquema de pago activo' : `hay ${lista.length} esquemas de pago activos`} sin relación laboral asignada (${lista.map((e) => esc(esquemaTexto(e))).join('; ')}). La baja no ${lista.length === 1 ? 'lo' : 'los'} desactivaría. Asígna${lista.length === 1 ? 'lo' : 'los'} a su relación en «Esquemas de pago sin relación laboral» (arriba) y vuelve a intentarlo.`;
  const camposBaja = () => `<div><label>Fecha efectiva de la baja</label><input name="fecha" type="date" required></div>
        <div><label>Motivo de la baja (causa IMSS)</label><select name="causa" required><option value="">Elige…</option>${causas.map((c) => `<option value="${esc(c.codigo)}">${esc(c.codigo)} · ${esc(c.descripcion)}</option>`).join('')}</select></div>
        <div><label>Comentario (opcional)</label><input name="motivo"></div>`;

  // Baja de UNA relación (botón de la tarjeta): p. ej. cambio de registro patronal
  // dentro de la misma empresa. La baja en una empresa se hace desde el estatus.
  function formBaja(relId) {
    const rpId = (estado.relaciones.find((r) => r.id === relId) || {}).registro_patronal_id;
    const rel = estado.relaciones.find((r) => r.id === relId) || {};
    const pend = pendientesDeEmpresa(rel.empresa_id);
    montar('hl-form-' + relId, `<b>Dar de baja esta relación</b>
      <p class="hint" style="margin:4px 0 8px">Solo termina esta relación; las demás de la persona no cambian. ${notaBaja(rpId)}</p>
      <ul class="bd-lista"><li>${esc(textoRelacion(rel))}${textoEsquemasBaja(rel)}</li></ul>
      ${pend.length ? `<div class="ri-bloqueo">${avisoPendientes(pend)}</div>` : ''}
      <div class="hl-grid">${camposBaja()}</div>
      <label class="bd-confirma"><input type="checkbox" name="confirma" data-requerida> <span>Confirmo que se termina esta relación${esquemasQueDesactiva(rel).length ? ' y se desactivan los esquemas indicados' : ''}.</span></label>
      ${botones('Registrar baja')}`, async (f) => {
      if (pendientesDeEmpresa(rel.empresa_id).length) { mensaje(null, false, avisoPendientes(pendientesDeEmpresa(rel.empresa_id)), 'rl-msg'); return; }
      if (!f.querySelector('[name=confirma]').checked) { mensaje('Marca la confirmación para registrar la baja.', false, null, 'rl-msg'); return; }
      const html = rpId
        ? `<b>Baja registrada.</b> El movimiento de baja (02) quedó <b>pendiente</b> en la bandeja IDSE del registro patronal <b>${esc(textoRP(rpId))}</b>. El archivo se genera desde la bandeja cuando lo decidas.${enlaceBandeja(rpId)}`
        : '<b>Baja registrada.</b> Esta relación no tiene registro patronal: no genera movimiento IDSE.';
      await ejecutar('laboral_registrar_baja', { p_relacion_id: relId, p_fecha_baja: val(f, 'fecha') || null, p_causa: val(f, 'causa') || null, p_motivo: val(f, 'motivo') || null },
        { html }, 'laboral', 'rl-msg');
    });
    const fb = document.querySelector('#hl-form-' + relId + ' form');
    if (fb) { if (pend.length) fb.dataset.bloqueado = '1'; ligarEnvio(fb); }
  }

  // ---------- Dar de baja en una empresa (desde el estatus de la ficha) ----------
  // LIMITACIÓN CONOCIDA: con varias relaciones se registra una baja por relación,
  // en llamadas separadas (no atómico). La revisión previa aplica las reglas de la
  // base para evitar fallas; si aun así una falla, las anteriores quedan registradas
  // y el mensaje dice cuáles faltan. Hacerlo atómico requiere una función en la base.
  // Termina TODAS las relaciones vigentes de la persona en una empresa (si tiene
  // vigentes en varias empresas, se elige cuál; las otras no se tocan). Una baja
  // por relación con la misma función de la base; 02 solo donde hay registro patronal.
  function bajaDesdeEstatus() {
    if (fichaBloqueadaPara !== estado.personaId) return false; // sin historia laboral: comportamiento anterior
    if (!puedeOperar() || !estado.relaciones.some((r) => r.estado === 'vigente')) return true;
    if (typeof cambiarSeccionDetalle === 'function') cambiarSeccionDetalle('laboral');
    formBajaDefinitiva();
    return true;
  }
  // Fecha mínima de baja de una relación (misma regla que laboral_registrar_baja).
  function minimoBaja(r) {
    const evs = estado.eventos.filter((e) => e.relacion_id === r.id && e.estado === 'vigente' && ['ingreso', 'reingreso', 'modificacion_salario'].includes(e.tipo) && e.fecha_efectiva)
      .map((e) => String(e.fecha_efectiva).slice(0, 10));
    return [r.fecha_ingreso, ...evs].filter(Boolean).sort().pop() || null;
  }
  // Revisión con las reglas de la base (laboral_registrar_baja) antes de registrar nada.
  function revisarBaja(rels, fecha) {
    return rels.map((r) => {
      if (!r.fecha_ingreso) return { r, txt: esMigrada(r.id) ? 'falta su fecha de ingreso.' : 'falta su fecha de ingreso y no se puede capturar con «Corregir datos» porque ya tiene movimientos registrados; revisa su Historia laboral.', corregir: esMigrada(r.id) };
      const min = minimoBaja(r);
      return fecha && min && fecha < min ? { r, txt: `la baja no puede ser anterior al ${fechaMx(min)} (ingreso o última modificación de salario).` } : null;
    }).filter(Boolean);
  }
  const btnCorregirFecha = (relId) => `<button type="button" class="hl-btn2 bd-corregir" data-corregir-fecha="${relId}">Corregir la fecha de ingreso de esta relación</button>`;
  function formBajaDefinitiva(borrador) {
    const vig = estado.relaciones.filter((r) => r.estado === 'vigente');
    const emps = [...new Set(vig.map((r) => r.empresa_id || ''))];
    const varias = emps.length > 1;
    montar('hl-form-bajacab', `<b>Dar de baja en esta empresa</b>
      <p class="hint" style="margin:4px 0 8px">La persona deja de laborar en la empresa: se terminan sus relaciones laborales vigentes en esa empresa y se desactivan sus esquemas de pago. Las relaciones en otras empresas no cambian. La baja ante el IMSS se confirma solo con el resultado aceptado del movimiento 02.</p>
      ${varias ? `<div class="hl-grid"><div style="grid-column:1/-1"><label>Empresa en la que se da de baja</label><select name="empresa" required><option value="">Elige…</option>${emps.map((e) => `<option value="${esc(e)}">${esc(e ? nombreEmpresa(e) : 'Sin empresa')}</option>`).join('')}</select>
        <p class="hint" style="margin:4px 0 0">Esta persona tiene relaciones vigentes en ${emps.length} empresas.</p></div></div>` : ''}
      <div class="bd-resumen"></div>
      <div class="hl-grid">${camposBaja()}</div>
      <div class="bd-pend"></div>
      <label class="bd-confirma" style="display:none"><input type="checkbox" name="confirma" data-requerida> <span class="bd-confirma-txt"></span></label>
      ${botones('Registrar baja en esta empresa')}`, async (f) => {
      const emp = varias ? val(f, 'empresa') : emps[0];
      if (varias && !emp) { mensaje('Elige la empresa en la que se da de baja.', false, null, 'rl-msg'); return; }
      const rels = vig.filter((r) => (r.empresa_id || '') === emp);
      const fecha = val(f, 'fecha'), causa = val(f, 'causa');
      if (!fecha || !causa) { mensaje('La fecha efectiva y el motivo de la baja son obligatorios.', false, null, 'rl-msg'); return; }
      if (!f.querySelector('[name=confirma]').checked) { mensaje(rels.length > 1 ? `Confirma que se terminan las ${rels.length} relaciones listadas.` : 'Marca la confirmación para registrar la baja.', false, null, 'rl-msg'); return; }
      const pendE = pendientesDeEmpresa(emp);
      if (pendE.length) { mensaje(null, false, avisoPendientes(pendE), 'rl-msg'); return; }
      // Revisión previa con las reglas de la base: si una relación no pasa, no se registra ninguna.
      const malas = revisarBaja(rels, fecha);
      if (malas.length) { mostrarProblemas(malas, '<b>No se registró ninguna baja.</b> Lo impide:'); return; }
      const hechas = [];
      for (const r of rels) {
        const { error } = await sb.rpc('laboral_registrar_baja', { p_relacion_id: r.id, p_fecha_baja: fecha, p_causa: causa, p_motivo: val(f, 'motivo') || null });
        if (error) {
          const html = `<b>La baja en la empresa quedó incompleta.</b> ${hechas.length ? 'Dadas de baja: ' + hechas.map((x) => esc(textoRelacion(x))).join('; ') + '. ' : 'No se registró ninguna. '}No se pudo dar de baja ${esc(textoRelacion(r))}: ${esc(msgError(error))}${hechas.length ? ' Elige otra vez «Baja» en el estatus para terminar las relaciones que faltan.' : ''}`;
          if (!hechas.length) { mensaje(null, false, html, 'rl-msg'); return; }
          await reabrir({ html, error: true });
          return;
        }
        hechas.push(r);
      }
      const siguen = vig.filter((r) => (r.empresa_id || '') !== emp);
      const html = `<b>Baja registrada en ${esc(emp ? nombreEmpresa(emp) : 'la empresa')}.</b> ${hechas.length === 1 ? 'Se terminó 1 relación laboral' : `Se terminaron ${hechas.length} relaciones laborales`}:<br>`
        + hechas.map((r) => `· ${esc(textoRelacion(r))}: ${r.registro_patronal_id ? `movimiento de baja (02) <b>pendiente</b> en la bandeja IDSE de ${esc(textoRP(r.registro_patronal_id))}.${enlaceBandeja(r.registro_patronal_id)}` : 'sin registro patronal, no genera movimiento IDSE.'}`).join('<br>')
        + (siguen.length ? `<br>La persona <b>sigue activa</b> en ${[...new Set(siguen.map((r) => esc(nombreEmpresa(r.empresa_id))))].join(', ')}: su estatus no cambia a Baja.` : '');
      await reabrir({ html, avisoImss: hechas.some((r) => r.registro_patronal_id) });
    });
    const c = document.getElementById('hl-form-bajacab'); if (!c) return;
    const resumen = c.querySelector('.bd-resumen'), conf = c.querySelector('.bd-confirma'), sel = c.querySelector('[name=empresa]');
    const fb = c.querySelector('form');
    // Problemas por relación, con acceso directo a corregir la que lo permite.
    const irACorregir = (relId) => {
      bajaEnCurso = { personaId: estado.personaId, empresa: varias ? sel.value : emps[0], fecha: val(fb, 'fecha'), causa: val(fb, 'causa'), motivo: val(fb, 'motivo'), relId };
      formCorregir(relId, { volverBaja: true });
    };
    const ligar = (raiz) => raiz.querySelectorAll('[data-corregir-fecha]').forEach((b) => { b.onclick = () => irACorregir(b.dataset.corregirFecha); });
    function mostrarProblemas(malas, titulo) {
      mensaje(null, false, `<div class="bd-error">${titulo}<ul style="margin:6px 0 0;padding-left:18px">${malas.map((m) => `<li><b>${esc(textoRelacion(m.r))}</b>: ${esc(m.txt)}${m.corregir ? '<br>' + btnCorregirFecha(m.r.id) : ''}</li>`).join('')}</ul></div>`, 'rl-msg');
      ligar(document.getElementById('rl-msg'));
    }
    const pintarResumen = () => {
      const emp = varias ? (sel.value || null) : emps[0];
      if (emp === null) { resumen.innerHTML = '<p class="hint" style="margin:0 0 8px">Elige la empresa para ver qué relaciones se terminan.</p>'; conf.style.display = 'none'; fb.querySelector('.bd-pend').innerHTML = ''; fb.dataset.bloqueado = '1'; actualizarEnvio(fb); return; }
      const rels = vig.filter((r) => (r.empresa_id || '') === emp), otras = vig.filter((r) => (r.empresa_id || '') !== emp);
      resumen.innerHTML = `<label style="font-size:12px;font-weight:600;color:var(--v21-texto-2,#5B6680)">${rels.length === 1 ? 'Se termina esta relación' : `Se terminan estas ${rels.length} relaciones`}</label>
        <ul class="bd-lista">${rels.map((r) => `<li data-bd-rel="${r.id}">${esc(textoRelacion(r))}<small>${r.registro_patronal_id ? `Genera la baja (02) pendiente en la bandeja IDSE de ${esc(textoRP(r.registro_patronal_id))}.` : 'Sin registro patronal: no genera movimiento IDSE.'}</small>${textoEsquemasBaja(r)}${
          r.fecha_ingreso ? '' : `<small class="bd-falta">Falta su fecha de ingreso: sin ella no se puede dar de baja.</small>${esMigrada(r.id) ? btnCorregirFecha(r.id) : ''}`}</li>`).join('')}</ul>
        ${otras.length ? `<p class="hint" style="margin:0 0 8px">No cambian: ${otras.map((r) => esc(textoRelacion(r))).join('; ')}.</p>` : ''}`;
      const nEsq = rels.reduce((n, r) => n + esquemasQueDesactiva(r).length, 0);
      conf.style.display = rels.length ? 'flex' : 'none';
      c.querySelector('.bd-confirma-txt').textContent = (rels.length > 1 ? `Confirmo que se terminan las ${rels.length} relaciones listadas` : 'Confirmo que se termina la relación listada')
        + (nEsq ? ` y se desactiva${nEsq > 1 ? 'n' : ''} ${nEsq === 1 ? 'el esquema de pago indicado' : `los ${nEsq} esquemas de pago indicados`}.` : '.');
      const pendE = pendientesDeEmpresa(emp);
      fb.querySelector('.bd-pend').innerHTML = pendE.length ? `<div class="ri-bloqueo">${avisoPendientes(pendE)}</div>` : '';
      fb.dataset.bloqueado = pendE.length || !rels.length ? '1' : '';
      const ch = conf.querySelector('input'); if (ch) ch.checked = false;
      actualizarEnvio(fb);
      ligar(resumen);
      const m = document.getElementById('rl-msg'); if (m && m.classList.contains('err')) { m.innerHTML = ''; m.className = 'hl-msg'; }
    };
    if (sel) sel.addEventListener('change', pintarResumen);
    if (borrador) {
      // Regreso de la corrección: se restaura lo capturado y se vuelven a revisar TODAS las relaciones.
      if (sel && emps.includes(borrador.empresa)) sel.value = borrador.empresa;
      ['fecha', 'causa', 'motivo'].forEach((k) => { const el = fb.querySelector(`[name="${k}"]`); if (el && borrador[k]) el.value = borrador[k]; });
      if (borrador.fecha || borrador.causa || borrador.motivo) fb.dataset.sucio = '1';
    }
    pintarResumen();
    ligarEnvio(fb);
    if (borrador) {
      const emp = varias ? sel.value : emps[0];
      const rels = emp == null || emp === '' && varias ? [] : vig.filter((r) => (r.empresa_id || '') === emp);
      const malas = revisarBaja(rels, borrador.fecha);
      const pre = borrador.corregida ? `<b>Corrección registrada.</b> ` : '';
      if (malas.length) mostrarProblemas(malas, `${pre}Volviste a «Dar de baja en esta empresa». Todavía lo impide:`);
      else if (rels.length) mensaje(null, true, `${pre}Volviste a «Dar de baja en esta empresa» con lo que ya habías capturado. Revisé de nuevo ${rels.length === 1 ? 'la relación: cumple' : `las ${rels.length} relaciones: todas cumplen`} las reglas para la baja.${rels.length > 1 ? ' Confirma y registra.' : ''}`, 'rl-msg');
    }
    c.scrollIntoView({ block: 'nearest' });
  }
  // Vuelve a abrir la ficha con el resultado y, si hubo 02, el aviso IDSE con su estado real.
  async function reabrir(res) {
    const id = estado.personaId;
    msgPendiente = { html: res.html, destino: 'rl-msg', personaId: id, error: !!res.error };
    if (typeof cargarPersonal === 'function') await cargarPersonal();
    avisoTrasBaja = res.avisoImss ? id : null; // se muestra cuando la ficha termine de cargar
    if (typeof abrirDetalle === 'function') await abrirDetalle(id, 'laboral');
  }

  // Aviso al cerrar la ficha: relaciones dadas de baja en BeeHuman cuyo 02 todavía
  // no tiene resultado aceptado del IMSS. Informa; no impide nada.
  const PASO_02 = { pendiente: 1, en_archivo: 2, presentado: 3, rechazado: 3 };
  const SITUACION_02 = {
    pendiente: 'Movimiento 02 pendiente de generar en la bandeja IDSE.',
    en_archivo: 'Archivo de baja (02) generado, pendiente de presentar ante el IMSS.',
    presentado: 'Archivo presentado ante el IMSS, sin resultado registrado.',
    rechazado: 'Resultado registrado: el IMSS rechazó la baja. Corrígela y vuelve a generar el 02.' };
  function bajasSinConfirmarImss() {
    if (!estado.personaId) return [];
    return estado.relaciones.filter((r) => r.estado === 'baja' && r.registro_patronal_id).map((r) => {
      const ev = estado.eventos.filter((e) => e.relacion_id === r.id && e.tipo === 'baja' && e.estado === 'vigente')
        .sort((a, b) => String(b.registrado_en).localeCompare(String(a.registrado_en)))[0];
      return ev && PASO_02[ev.idse_estado] ? { r, idse: ev.idse_estado } : null;
    }).filter(Boolean);
  }
  function avisoCierre(cerrar, trasBaja) {
    const lista = bajasSinConfirmarImss();
    if (!lista.length) return false;
    const pasos = (st) => {
      const n = PASO_02[st];
      const li = (i, hecho, falta) => `<li class="${i < n ? 'hecho' : i === n ? 'actual' : ''}">${i < n ? hecho : falta}</li>`;
      return `<ol class="av-pasos"><li class="hecho">Baja registrada en BeeHuman</li>${li(1, 'Archivo de baja (02) generado', 'Archivo de baja (02) pendiente de generar')}${
        li(2, 'Archivo presentado ante el IMSS', 'Archivo pendiente de presentar ante el IMSS')}${
        st === 'rechazado' ? '<li class="error">Resultado registrado: rechazado por el IMSS</li>' : li(3, 'Resultado registrado', 'Resultado del IMSS sin registrar')}</ol>`;
    };
    const d = document.createElement('div'); d.id = 'hl-aviso-imss'; d.setAttribute('role', 'dialog'); d.setAttribute('aria-modal', 'true');
    d.innerHTML = `<div class="av-caja"><h3>${trasBaja ? 'Baja registrada en BeeHuman: falta el IMSS' : 'La baja todavía no está confirmada ante el IMSS'}</h3>
      <p style="margin:0">La relación laboral se dio de baja en BeeHuman, pero el trabajador continúa registrado ante el IMSS. Se recomienda generar el archivo de baja (02) en IDSE y presentarlo ante el IMSS.</p>
      ${lista.map(({ r, idse: st }) => `<div class="av-rel"><b>${esc(nombreEmpresa(r.empresa_id))} · RP ${esc(textoRP(r.registro_patronal_id))}</b>
        <div class="hint" style="margin:2px 0 0">Baja en BeeHuman el ${fechaMx(r.fecha_baja)}. ${SITUACION_02[st]}</div>${pasos(st)}</div>`).join('')}
      <div class="av-acc"><button type="button" class="hl-btn2" data-av="seguir">Seguir en la ficha</button>
        <button type="button" class="hl-btn2" data-av="bandeja">Ir a la bandeja IDSE</button>
        <button type="button" class="primary" data-av="cerrar">Cerrar la ficha</button></div></div>`;
    document.body.appendChild(d);
    const rp = lista[0].r.registro_patronal_id;
    d.querySelector('[data-av="seguir"]').onclick = () => d.remove();
    d.querySelector('[data-av="cerrar"]').onclick = () => { d.remove(); cerrar(); };
    d.querySelector('[data-av="bandeja"]').onclick = () => { d.remove(); irABandeja(rp); };
    d.querySelector('[data-av="cerrar"]').focus();
    return true;
  }

  // Modificación de salario (07) desde Compensación. Se captura UN dato: el SDI.
  // El SBC técnico del formato IMSS se deriva (SDI, o el tope de 25 UMA a la fecha
  // efectiva si lo rebasa). El sueldo de los esquemas de pago no interviene.
  const FACTOR_MINIMO = 1.0493; // integración mínima de ley (15 días de aguinaldo, 12 de vacaciones, 25 % de prima)
  function formSalario(relId, avisoSueldo) {
    const r = estado.relaciones.find((x) => x.id === relId) || {};
    const rpId = r.registro_patronal_id;
    const sbcVig = r.sbc == null ? null : Number(r.sbc);
    const sdiVig = sdiDe(r);
    const otras = estado.relaciones.filter((x) => x.estado === 'vigente' && x.registro_patronal_id && x.id !== relId).length;
    montar('sbc-form-' + relId, `<b>Modificación de salario (07) · ${esc(nombreEmpresa(r.empresa_id))} · RP ${esc(textoRP(rpId) || '')}</b>
      ${otras ? `<p class="hl-aviso-sueldo">Esta persona tiene ${otras + 1} relaciones vigentes con registro patronal. El movimiento se registrará <b>solo</b> para ${esc(nombreEmpresa(r.empresa_id))} · RP ${esc(textoRP(rpId))} (ingreso ${fechaMx(r.fecha_ingreso)}).</p>` : ''}
      ${avisoSueldo ? `<p class="hl-aviso-sueldo">${esc(avisoSueldo)}</p>` : ''}
      <p class="hint" style="margin:4px 0 8px">${esc(SDI_AYUDA)}</p>
      <div class="sbc-resumen">
        <div><span>SDI vigente registrado</span><b>${sdiVig == null ? 'No registrado' : dinero(sdiVig)}</b>${sdiVig == null ? '<small>Dato migrado sin SDI. El movimiento quedará como «No registrado → nuevo»; no se inventa un valor anterior.</small>' : (sbcVig != null && sbcVig !== sdiVig ? `<small>Cotiza al IMSS con ${esc(dinero(sbcVig))} (tope)</small>` : '')}</div>
        <div><span>Nuevo SDI diario</span><b class="sbc-nuevo">—</b></div>
        <div><span>SBC para el archivo IDSE</span><b class="sbc-tecnico">—</b><small class="sbc-tope-det"></small></div>
      </div>
      <div class="sbc-avisos"></div>
      <div class="hl-grid"><div><label>Fecha efectiva del cambio (no la fecha de captura)</label><input name="fecha" type="date" required value="${hoyMexico()}"></div>
        <div><label>SDI — salario diario integrado</label><input name="sdi" inputmode="decimal" required placeholder="Ej. 1,250.00" autocomplete="off"></div>
        <div><label>Tipo de salario</label><select name="ts">${opciones(TIPO_SAL, r.tipo_salario)}</select></div>
        <div><label class="sbc-motivo-lab">Motivo (opcional)</label><input name="motivo" maxlength="300"></div></div>
      <div id="hl-faltan-07-${relId}"></div>${botones('Registrar modificación')}`, async (f) => {
      const sdi = leerImporte(val(f, 'sdi'));
      if (sdi == null || isNaN(sdi) || sdi <= 0) { mensaje('Captura el nuevo SDI diario: un importe con hasta 2 decimales.', false, null, 'sbc-msg'); return; }
      let est = await revisar();
      while (est.obsoleta) est = await revisar();
      if (est.bloquea) { mensaje(est.bloquea, false, null, 'sbc-msg'); return; }
      const faltan = faltantesIdse07(r, val(f, 'ts'));
      const html = `<b>Modificación de salario registrada.</b> El movimiento 07 quedó <b>pendiente</b> en la bandeja IDSE del registro patronal <b>${esc(textoRP(rpId))}</b> con SBC ${esc(dinero(est.sbc))}${est.sbc !== sdi ? ' (tope de 25 UMA; SDI ' + esc(dinero(sdi)) + ')' : ''}. `
        + (faltan.length ? `<span class="sbc-pend-arch">Archivo todavía no listo: falta ${faltan.map(esc).join(', ')}.</span> ` : 'Su archivo está listo para generarse desde la bandeja cuando lo decidas.')
        + enlaceBandeja(rpId);
      const res = await ejecutar('laboral_modificar_salario', { p_relacion_id: relId, p_fecha_efectiva: val(f, 'fecha') || null, p_sbc: est.sbc,
        p_sdi: sdi, p_tipo_salario: val(f, 'ts') || null, p_motivo: val(f, 'motivo') || null }, { html }, 'compensacion', 'sbc-msg');
      if (res.error && res.error.hint === 'sbc_tope') revisar();
    });
    const form = document.querySelector('#sbc-form-' + relId + ' form');
    if (!form) return;
    const caja = form.querySelector('.sbc-avisos');
    const enviar = form.querySelector('button[type=submit]');
    // Avisos en vivo. «bloquea» = la base lo rechazaría (mínimo, motivo, sin cambio).
    let turno = 0; // solo la revisión más reciente pinta (las anteriores pueden terminar después)
    async function revisar() {
      const mio = ++turno;
      // Un error anterior deja de valer en cuanto se edita el formulario.
      const previo = document.getElementById('sbc-msg');
      if (previo && previo.classList.contains('err')) { previo.textContent = ''; previo.className = 'hl-msg'; }
      const fecha = val(form, 'fecha');
      const sdi = leerImporte(val(form, 'sdi'));
      const t = fecha ? await topeEn(fecha, relId) : {};
      if (mio !== turno) return { bloquea: null, obsoleta: true };
      const sbc = sbcDeSdi(sdi, t.tope);
      const topado = sbc != null && sdi != null && sbc !== sdi;
      form.querySelector('.sbc-nuevo').textContent = sdi == null || isNaN(sdi) ? '—' : dinero(sdi);
      form.querySelector('.sbc-tecnico').textContent = sbc == null ? '—' : dinero(sbc);
      form.querySelector('.sbc-tope-det').textContent = t.tope == null ? 'Sin UMA registrada para esa fecha.'
        : (topado ? `El SDI rebasa el tope: se usa el tope de 25 UMA × ${dinero(t.uma)} (UMA vigente al ${fechaMx(fecha)}).`
          : `Igual al SDI. Tope a esa fecha: ${dinero(t.tope)} (25 UMA × ${dinero(t.uma)}).`);
      const avisos = []; let bloquea = null;
      const motivoLab = form.querySelector('.sbc-motivo-lab');
      motivoLab.textContent = 'Motivo (opcional)';
      if (sbc != null) {
        if (topado) avisos.push(`<div class="sbc-av">El SDI (${esc(dinero(sdi))}) rebasa el tope de cotización: el movimiento 07 llevará el tope (${esc(dinero(sbc))}) como SBC y se conserva el SDI capturado.</div>`);
        if (t.sm != null && sbc < t.sm) {
          bloquea = `El SDI no puede ser menor al salario mínimo ${t.zlfn ? 'de la zona libre de la frontera norte' : 'general'} (${dinero(t.sm)}) a esa fecha. Con jornada o semana reducida también se ajusta al mínimo.`;
          avisos.push(`<div class="sbc-av err">${esc(bloquea)}</div>`);
        } else if (t.sm != null && sbc < Math.round(t.sm * FACTOR_MINIMO * 100) / 100) {
          avisos.push(`<div class="sbc-av">Aviso: está por debajo del salario mínimo integrado con las prestaciones mínimas de ley (aprox. ${esc(dinero(Math.round(t.sm * FACTOR_MINIMO * 100) / 100))}). Revisa el factor de integración; no impide registrar.</div>`);
        }
        if (!bloquea && sbcVig != null && sbc === sbcVig && (val(form, 'ts') || r.tipo_salario) === r.tipo_salario) {
          bloquea = `El SBC para el IMSS no cambia (${dinero(sbc)}): no hay modificación de salario (07) que registrar.`;
          avisos.push(`<div class="sbc-av err">${esc(bloquea)}</div>`);
        }
        if (sbcVig != null && sbc < sbcVig) {
          motivoLab.textContent = 'Motivo (obligatorio: el salario baja)';
          const mot = val(form, 'motivo');
          avisos.push(`<div class="sbc-av">El nuevo salario es <b>menor</b> que el vigente (SBC ${esc(dinero(sbcVig))} → ${esc(dinero(sbc))}). Una reducción requiere sustento (p. ej. salario variable o convenio): escribe la justificación en el motivo.</div>`);
          if (mot.length < 5 && !bloquea) bloquea = 'Escribe la justificación de la disminución del salario en el motivo (al menos 5 caracteres).';
        }
      }
      caja.innerHTML = avisos.join('');
      enviar.disabled = !!(bloquea && bloquea.startsWith('El S')); // mínimo o sin cambio: la base lo rechazaría
      return { bloquea, sbc };
    }
    const elSdi = form.querySelector('[name=sdi]');
    elSdi.addEventListener('input', () => { formatearAlEscribir(elSdi); revisar(); });
    elSdi.addEventListener('blur', () => { const v = leerImporte(elSdi.value); if (v != null && !isNaN(v)) elSdi.value = formatoImporte(v); });
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
    form.querySelector('[name=ts]').addEventListener('change', () => { pintarFaltantes(); revisar(); });
    pintarFaltantes();
    revisar();
  }

  // Tras cambiar un sueldo en Compensación: se avisa, sin tocar el SBC. El 07 que se
  // ofrece es SOLO el de la relación laboral de ese esquema; nunca se adivina.
  async function trasCambioSueldo(registroId, opc) {
    if (!puedeOperar() || !registroId) return;
    const { data } = await sb.from('personal_registros_pago').select('relacion_laboral_id,sueldo,modalidad_sueldo,fecha_inicio').eq('id', registroId).maybeSingle();
    const relId = data && data.relacion_laboral_id;
    const esquemaTxt = data ? `${dinero(data.sueldo)} ${data.modalidad_sueldo || ''} desde ${fechaMx(data.fecha_inicio)}`.replace(/\s+/g, ' ') : '';
    // La lista «Esquemas de pago de esta relación» debe mostrar el sueldo recién guardado.
    const pid = estado.personaId;
    const esq = await sb.from('personal_registros_pago').select('id,sueldo,modalidad_sueldo,empresa_id,registro_patronal_id,clasificacion_id,periodicidad_id,dias_periodo,fecha_inicio,fecha_fin,activo,relacion_laboral_id')
      .eq('personal_id', pid);
    if (estado.personaId !== pid) return;
    if (!esq.error) {
      estado.todosEsquemas = esq.data || []; estado.esquemas = estado.todosEsquemas.filter((e) => e.activo);
      estado.pendientes = estado.esquemas.filter((e) => !e.relacion_laboral_id); pintarSbc(); pintarRelaciones();
      if (typeof renderRegistrosPagoDetalle === 'function') renderRegistrosPagoDetalle();
    }
    const r = estado.relaciones.find((x) => x.id === relId);
    // Primer esquema de una relación (p. ej. tras un ingreso o reingreso): no hay sueldo anterior que comparar.
    if (opc && opc.alta && r && estado.todosEsquemas.filter((e) => e.relacion_laboral_id === r.id).length === 1 && estado.todosEsquemas.some((e) => e.id === registroId)) {
      mensaje(null, true, `<b>Esquema de pago registrado</b> para la relación ${esc(nombreEmpresa(r.empresa_id))} · ${esc(rpCorto(r.registro_patronal_id))} (ingreso ${fechaMx(r.fecha_ingreso)}): ${esc(esquemaTexto(estado.todosEsquemas.find((e) => e.id === registroId)))}.${r.registro_patronal_id ? ' El SDI ante el IMSS es el que capturaste en el ingreso.' : ''}`, 'sbc-msg');
      return;
    }
    const txt = 'Cambiaste un sueldo en los esquemas de pago. El SDI ante el IMSS no se actualiza solo: si también cambia, registra la modificación de salario (07).';
    if (!r) {
      mensaje(null, true, `${esc(txt)} <b>Este esquema no tiene relación laboral asignada</b>: asígnalo en <a href="#" onclick="cambiarSeccionDetalle('laboral');return false;">Relación laboral</a> para saber a qué registro patronal corresponde.`, 'sbc-msg');
      return;
    }
    if (r.estado !== 'vigente' || !r.registro_patronal_id) return;
    mensaje(null, true, `${esc(txt)} <button type="button" class="hl-btn2" id="sbc-desde-sueldo">Registrar modificación (07) · ${esc(nombreEmpresa(r.empresa_id))} · RP ${esc(textoRP(r.registro_patronal_id))}</button>`, 'sbc-msg');
    const b = document.getElementById('sbc-desde-sueldo');
    if (b) b.onclick = () => formSalario(r.id, `Origen: cambio del esquema de pago ${esquemaTxt}, que pertenece a la relación ${nombreEmpresa(r.empresa_id)} · RP ${textoRP(r.registro_patronal_id)} (ingreso ${fechaMx(r.fecha_ingreso)}). El SDI no se calcula del sueldo: captúralo tú.`);
  }

  // Desde un aviso: cierra la ficha y abre la bandeja IDSE en ese registro patronal.
  async function irABandeja(rpId) {
    if (typeof cerrarDetalle === 'function') cerrarDetalle({ sinAvisoImss: true });
    // Si había cambios pendientes de verdad y la persona decidió quedarse, no se navega.
    const ov = document.getElementById('modal-overlay');
    if (ov && ov.style.display !== 'none' && detalleActual) return;
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
    // Número interno (clave del trabajador) y UMF son opcionales para el IDSE.
    if (!r.tipo_trabajador) f.push('tipo de trabajador');
    if (!(tipoSalarioElegido || r.tipo_salario)) f.push('tipo de salario');
    if (!r.jornada) f.push('jornada');
    return f;
  }

  // Faltantes de la bandeja IDSE → campo de «Corregir datos» de la relación.
  const FALTA_CAMPO = { 'Tipo de trabajador': 'tipo_trabajador', 'Tipo de salario': 'tipo_salario', 'Jornada': 'jornada', 'UMF': 'umf',
    'Número interno (clave del trabajador)': 'numero_interno', 'SBC': 'sdi' };
  // Faltantes de la bandeja IDSE → campo de la ficha de la persona.
  const FALTA_PERSONA = [[/^NSS/, 'd-nss'], [/^CURP/, 'd-curp'], [/^Primer apellido/, 'd-apellido1'], [/^Nombre\(s\)/, 'd-nombres'],
    [/^Nombre con dígitos/, ['d-nombres', 'd-apellido1', 'd-apellido2']]];
  function formCorregir(relId, opc) {
    opc = opc || {};
    const r = estado.relaciones.find((x) => x.id === relId) || {};
    const migrado = estado.eventos.some((e) => e.relacion_id === relId && ['ingreso', 'reingreso'].includes(e.tipo) && e.estado === 'vigente' && e.origen === 'migracion')
      && !estado.eventos.some((e) => e.relacion_id === relId && e.tipo === 'modificacion_salario' && e.estado === 'vigente');
    const faltan = (opc.faltan || []).filter((x) => FALTA_CAMPO[x]);
    const marcar = new Set(faltan.map((x) => FALTA_CAMPO[x]));
    if (opc.volverBaja) marcar.add('fecha_ingreso');
    const etiqueta = (campo, texto) => `${texto}${marcar.has(campo) ? `<span class="hl-falta-lab">${campo === 'fecha_ingreso' && opc.volverBaja ? 'Falta para la baja' : 'Falta para IDSE'}</span>` : ''}`;
    const sdiVig = sdiDe(r);
    montar('hl-form-' + relId, `<b>Corregir datos</b>
      <p class="hint" style="margin:4px 0 6px">Relación que se corrige: <b>${esc(nombreEmpresa(r.empresa_id))} · ${esc(rpCorto(r.registro_patronal_id))}</b> (${r.estado === 'vigente' ? 'vigente' : 'baja ' + fechaMx(r.fecha_baja)}, ingreso ${r.fecha_ingreso ? fechaMx(r.fecha_ingreso) : 'sin capturar'}). Solo cambia esta relación; las demás no se tocan.</p>
      ${opc.volverBaja ? `<p class="hl-aviso-sueldo">Para dar de baja esta relación falta su <b>fecha de ingreso</b>: captúrala y guarda. Después vuelves a «Dar de baja en esta empresa» con la fecha, el motivo y el comentario que ya capturaste.</p>` : ''}
      ${faltan.length ? `<p class="hl-aviso-sueldo">Para el archivo IDSE falta: <b>${faltan.map(esc).join(', ')}</b>. Los campos están marcados.${opc.rpId ? ' Al guardar podrás volver a la bandeja IDSE.' : ''}</p>` : ''}
      <p class="hint" style="margin:4px 0 8px">Solo se guardan los campos que cambies. ${migrado ? 'Por ser un dato migrado también puedes corregir la fecha de ingreso y el SDI.' : 'La fecha de ingreso y el SDI de un movimiento real no se corrigen aquí: usa anular o modificación de salario.'}</p>
      <div class="hl-grid">
        ${migrado ? `<div><label>${etiqueta('fecha_ingreso', 'Fecha de ingreso')}</label><input name="fecha_ingreso" type="date" value="${r.fecha_ingreso || ''}"></div>
        <div><label>${etiqueta('sdi', 'SDI — salario diario integrado')}</label><input name="sdi" inputmode="decimal" autocomplete="off" value="${sdiVig == null ? '' : formatoImporte(sdiVig)}"></div>` : ''}
        <div><label>Antigüedad reconocida</label><input name="fecha_reconocimiento_antiguedad" type="date" value="${r.fecha_reconocimiento_antiguedad || ''}"></div>
        <div><label>${etiqueta('numero_interno', 'Número interno')}</label><input name="numero_interno" maxlength="10" value="${esc(r.numero_interno || '')}"></div>
        <div><label>${etiqueta('tipo_trabajador', 'Tipo de trabajador')}</label><select name="tipo_trabajador">${opciones(TIPO_TRAB, r.tipo_trabajador)}</select></div>
        <div><label>${etiqueta('tipo_salario', 'Tipo de salario')}</label><select name="tipo_salario">${opciones(TIPO_SAL, r.tipo_salario)}</select></div>
        <div><label>${etiqueta('jornada', 'Jornada IMSS')}</label><select name="jornada">${opciones(JORNADA, r.jornada)}</select></div>
        <div><label>${etiqueta('umf', 'UMF')}</label><input name="umf" maxlength="3" inputmode="numeric" value="${esc(r.umf || '')}"></div>
        <div><label>Motivo de la corrección</label><input name="motivo" required></div>
      </div><div class="fd-caja"></div>${botones('Guardar corrección')}`, async (f) => {
      const cambios = {};
      ['fecha_ingreso', 'fecha_reconocimiento_antiguedad', 'numero_interno', 'tipo_trabajador', 'tipo_salario', 'jornada', 'umf'].forEach((k) => {
        const el = f.querySelector(`[name="${k}"]`); if (!el) return;
        const v = el.value.trim(); const actual = r[k] == null ? '' : String(r[k]);
        if (v !== actual) cambios[k] = v === '' ? null : v;
      });
      const elSdi = f.querySelector('[name="sdi"]');
      if (elSdi && elSdi.value.trim() !== '') {
        const sdi = leerImporte(elSdi.value);
        if (sdi == null || isNaN(sdi) || sdi <= 0) { mensaje('El SDI debe ser un importe mayor a cero, con hasta 2 decimales.', false, null, 'rl-msg'); return; }
        if (sdi !== sdiVig) {
          const fIng = cambios.fecha_ingreso || r.fecha_ingreso || hoyMexico();
          cambios.sdi = sdi;
          cambios.sbc = sbcDeSdi(sdi, (await topeEnRp(fIng, r.registro_patronal_id)).tope);
        }
      }
      if (!Object.keys(cambios).length) { mensaje('No cambiaste ningún dato.', false, null, 'rl-msg'); return; }
      // Fecha ya registrada en otra relación: se exige confirmar que es otro periodo.
      if (cambios.fecha_ingreso && fechaYaRegistrada(cambios.fecha_ingreso, relId).length && !(f.querySelector('[name=confirma_fecha]') || {}).checked) {
        mensaje('Esa fecha de ingreso ya está registrada en otra relación: revisa el aviso y confirma antes de guardar.', false, null, 'rl-msg'); return;
      }
      const donde = `${esc(nombreEmpresa(r.empresa_id))} · ${esc(rpCorto(r.registro_patronal_id))}`;
      const detalleOk = cambios.fecha_ingreso ? ` Fecha de ingreso de la relación ${donde}: <b>${fechaMx(cambios.fecha_ingreso)}</b>.` : ` Relación ${donde}.`;
      const ok = { html: `<b>Corrección registrada.</b>${detalleOk}${opc.rpId ? enlaceBandeja(opc.rpId, 'Volver a la bandeja IDSE de ' + (textoRP(opc.rpId) || 'este registro patronal')) : ''}` };
      if (opc.volverBaja && bajaEnCurso) { bajaEnCurso.volver = true; bajaEnCurso.corregida = relId; }
      const res = await ejecutar('laboral_corregir_datos', { p_relacion_id: relId, p_cambios: cambios, p_motivo: val(f, 'motivo') }, ok, 'laboral', 'rl-msg');
      if (res && res.error && bajaEnCurso) { bajaEnCurso.volver = false; bajaEnCurso.corregida = null; }
    });
    const form = document.querySelector('#hl-form-' + relId + ' form');
    if (!form) return;
    if (opc.volverBaja) {
      form.querySelector('[data-cancelar]').textContent = 'Volver a la baja sin corregir';
      form.querySelector('[data-cancelar]').onclick = () => { const b = bajaEnCurso; bajaEnCurso = null; if (b) formBajaDefinitiva(b); };
      const mot = form.querySelector('[name=motivo]'); if (mot && !mot.value) mot.value = 'Fecha de ingreso faltante para registrar la baja';
    }
    // Aviso de fecha duplicada: dice en qué relación ya está registrada esa fecha.
    const elFi = form.querySelector('[name=fecha_ingreso]'), fdCaja = form.querySelector('.fd-caja');
    const revisarFecha = () => {
      const fe = elFi ? elFi.value : '';
      const otras = fe && fe !== String(r.fecha_ingreso || '') ? fechaYaRegistrada(fe, relId) : [];
      fdCaja.innerHTML = otras.length ? `<div class="fd-aviso">La fecha <b>${fechaMx(fe)}</b> ya está registrada como fecha de ingreso de ${otras.map((o) => `la relación <b>${esc(textoDonde(o))}</b>`).join(' y de ')}. Esta corrección la guardaría también en <b>${esc(nombreEmpresa(r.empresa_id))} · ${esc(rpCorto(r.registro_patronal_id))}</b>. Si es el mismo periodo, no la dupliques: la relación correcta ya tiene su fecha.</div>
        <label class="bd-confirma"><input type="checkbox" name="confirma_fecha" data-requerida> <span>Confirmo que esta relación es un periodo distinto que también inició el ${fechaMx(fe)}.</span></label>` : '';
      actualizarEnvio(form);
    };
    if (elFi) elFi.addEventListener('change', revisarFecha);
    ligarEnvio(form);
    const elSdi = form.querySelector('[name=sdi]');
    if (elSdi) {
      elSdi.addEventListener('input', () => formatearAlEscribir(elSdi));
      elSdi.addEventListener('blur', () => { const v = leerImporte(elSdi.value); if (v != null && !isNaN(v)) elSdi.value = formatoImporte(v); });
    }
    marcar.forEach((campo) => { const el = form.querySelector(`[name="${campo}"]`); if (el) el.classList.add('hl-falta'); });
    const primero = form.querySelector('.hl-falta') || form.querySelector('input,select');
    if (primero) { primero.focus(); primero.scrollIntoView({ block: 'center' }); }
  }

  // Desde la bandeja IDSE: abre la ficha en el lugar exacto del dato que falta.
  let pendienteAbrir = null;
  async function completarDesdeIdse(personaId, relId, faltan, rpId) {
    const deRelacion = faltan.some((x) => FALTA_CAMPO[x]);
    pendienteAbrir = { personaId, relId, faltan, rpId, deRelacion };
    if (typeof abrirDetalle === 'function') await abrirDetalle(personaId, deRelacion ? 'laboral' : 'personal');
  }
  function aplicarPendienteAbrir() {
    const pa = pendienteAbrir;
    if (!pa || pa.personaId !== estado.personaId) return;
    pendienteAbrir = null;
    if (pa.deRelacion && estado.relaciones.some((x) => x.id === pa.relId)) { formCorregir(pa.relId, { faltan: pa.faltan, rpId: pa.rpId }); return; }
    // Datos de la persona: se marcan los campos y se ofrece volver a la bandeja.
    const ids = [];
    pa.faltan.forEach((x) => FALTA_PERSONA.forEach(([re, id]) => { if (re.test(x)) ids.push(...[].concat(id)); }));
    ids.forEach((id) => { const el = document.getElementById(id); if (el) { el.classList.add('hl-falta'); el.addEventListener('input', () => el.classList.remove('hl-falta'), { once: true }); } });
    const sec = document.querySelector('[data-detail-section="personal"]');
    if (sec) {
      let n = document.getElementById('idse-retorno');
      if (!n) { n = document.createElement('div'); n.id = 'idse-retorno'; n.className = 'hl-aviso-sueldo'; sec.insertBefore(n, sec.children[1] || null); }
      n.innerHTML = `Para el archivo IDSE falta: <b>${pa.faltan.filter((x) => !FALTA_CAMPO[x]).map(esc).join(', ')}</b>. Los campos están marcados; corrígelos y usa «Guardar cambios».${enlaceBandeja(pa.rpId, 'Volver a la bandeja IDSE de ' + (textoRP(pa.rpId) || 'este registro patronal'))}`;
    }
    const primero = ids.map((id) => document.getElementById(id)).find(Boolean);
    if (primero) { primero.scrollIntoView({ block: 'center' }); primero.focus(); }
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
    return 'Ingreso registrado en su Historia laboral.' + (enviado.registro_patronal_id ? ' Completa SDI y tipos en la ficha antes de generar el IDSE.' : '');
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
      <div class="idse-config"><h4>Configuración del registro patronal</h4>
      <div class="hl-grid" style="max-width:860px"><div><label>Registro patronal</label><select id="idse-rp">${activos.map((r) =>
        `<option value="${r.id}" ${r.id === idse.rp ? 'selected' : ''}>${esc(r.registro_patronal)} · ${esc(nombreEmpresa(r.empresa_id))}</option>`).join('')}</select></div>
        <div><label>Guía IDSE</label><input id="idse-guia" maxlength="5" inputmode="numeric" ${esAdmin() ? '' : 'disabled'}></div>
        <div><label>Zona de salario mínimo</label><select id="idse-zona" ${esAdmin() ? '' : 'disabled'}><option value="general">General</option><option value="zlfn">Zona libre de la frontera norte</option></select></div>
        ${esAdmin() ? '<div><button type="button" class="hl-btn2" id="idse-guardar-rp">Guardar datos del RP</button></div>' : ''}</div>
      <div class="hl-meta" id="idse-guia-nota" style="margin-top:6px"></div></div>
      <div class="hl-msg" id="idse-msg"></div>
      <h4 class="idse-sec">Altas y reingresos pendientes (08)</h4><div id="idse-pend-08"></div>
      <h4 class="idse-sec">Bajas pendientes (02)</h4><div id="idse-pend-02"></div>
      <h4 class="idse-sec">Modificaciones de salario pendientes (07)</h4><div id="idse-pend-07"></div>
      <h4 class="idse-sec">Archivos generados</h4><div id="idse-arch"></div></div>`;
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
    let h = `<div style="overflow-x:auto"><table class="idse-tabla"><thead><tr><th><input type="checkbox" class="idse-todos" data-tipo="${tipo}" aria-label="Seleccionar todos"></th><th>Persona</th><th>${tipo === '02' ? 'Fecha de baja' : 'Fecha'}</th>${tipo === '02' ? '<th>Causa</th>' : ''}${tipo === '07' ? '<th>SBC del movimiento</th>' : ''}<th>Revisión</th></tr></thead><tbody>`;
    filas.forEach((f) => {
      const okF = !(f.errores || []).length;
      h += `<tr><td><input type="checkbox" class="idse-sel" data-tipo="${tipo}" value="${f.movimiento_id}" ${okF ? '' : 'disabled'}></td><td>${esc(f.nombre)}</td><td>${fechaMx(f.fecha_movimiento)}</td>${tipo === '02' ? `<td>${esc(causaDe(f.movimiento_id))}</td>` : ''}${tipo === '07' ? `<td>${esc(sbcDe(f.movimiento_id))}</td>` : ''}
        <td>${(f.errores || []).map((x) => `<div class="idse-err">${x.includes(':') ? esc(x) : 'Falta: ' + esc(x)}</div>`).join('')}${(f.avisos || []).map((x) => `<div class="idse-aviso">${esc(x)}</div>`).join('')}${okF && !(f.avisos || []).length ? '<span class="hl-chip vigente">Lista</span>' : ''}
          ${(() => { const m = movs.find((x) => x.id === f.movimiento_id) || {}; const e = f.errores || []; let b = '';
            if (e.some((x) => FALTA_CAMPO[x]) && m.relacion_laboral_id) b += `<button type="button" class="hl-btn2" data-completar="rel" data-mov="${f.movimiento_id}">Completar datos de la relación laboral</button>`;
            if (e.some((x) => FALTA_PERSONA.some(([re]) => re.test(x)))) b += `<button type="button" class="hl-btn2" data-completar="persona" data-mov="${f.movimiento_id}">Completar datos de la persona</button>`;
            return b ? `<div class="idse-completar">${b}</div>` : ''; })()}</td></tr>`;
    });
    h += `</tbody></table></div><div class="hl-acc"><button type="button" class="primary" style="margin:0" data-generar="${tipo}">Generar archivo de ${TITULO_TIPO[tipo]} con los seleccionados</button></div>`;
    pend.innerHTML = h;
    const t = pend.querySelector('.idse-todos');
    if (t) t.onchange = () => pend.querySelectorAll('.idse-sel:not(:disabled)').forEach((c) => { c.checked = t.checked; });
    pend.querySelector('[data-generar]').onclick = () => generar(tipo);
    pend.querySelectorAll('[data-completar]').forEach((b) => {
      b.onclick = () => {
        const fila = filas.find((x) => x.movimiento_id === b.dataset.mov) || {};
        const m = movs.find((x) => x.id === b.dataset.mov) || {};
        const errores = (fila.errores || []).filter((x) => (b.dataset.completar === 'rel' ? FALTA_CAMPO[x] : FALTA_PERSONA.some(([re]) => re.test(x))));
        completarDesdeIdse(fila.personal_id, m.relacion_laboral_id, errores, idse.rp);
      };
    });
  }

  async function refrescarIdse() {
    const arch = document.getElementById('idse-arch');
    const [v08, v02, v07, a, otros] = await Promise.all([
      sb.rpc('idse_validar', { p_registro_patronal_id: idse.rp, p_tipo: '08' }),
      sb.rpc('idse_validar', { p_registro_patronal_id: idse.rp, p_tipo: '02' }),
      sb.rpc('idse_validar', { p_registro_patronal_id: idse.rp, p_tipo: '07' }),
      sb.from('idse_archivos').select('id,nombre_archivo,num_registros,estado,lote_idse,fecha_presentacion,acuse_folio,generado_en,hash_sha256,tipo_movimiento')
        .eq('registro_patronal_id', idse.rp).order('generado_en', { ascending: false }),
      sb.from('idse_movimientos').select('id,tipo_movimiento,causa_baja,sbc,relacion_laboral_id').eq('registro_patronal_id', idse.rp).in('estado', ['pendiente', 'rechazado']),
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
  // Cambios pendientes reales en los formularios de Relación laboral y Compensación
  // (se guardan con sus propios botones; la ficha general no los compara).
  function formularioConDatos() { return !!document.querySelector('#rl-raiz form.hl-form[data-sucio], #sbc-raiz form.hl-form[data-sucio]'); }
  // Atajo desde el menú Estatus (persona en Baja): abre el registro en Relación laboral.
  function ingresoDesdeEstatus() {
    if (!puedeOperar()) return false;
    if (typeof cambiarSeccionDetalle === 'function') cambiarSeccionDetalle('laboral');
    ingresoEnCurso = null; formIngreso();
    const f = document.querySelector('#hl-form-ingreso'); if (f) f.scrollIntoView({ block: 'start' });
    return true;
  }
  // Para Compensación: relaciones de la persona abierta (null si aún no cargan o no tiene historial).
  function relacionesDe(pid) { return estado.personaId === pid && estado.relaciones.length ? estado.relaciones.slice() : null; }
  window.BH_laboral = { alAbrirDetalle, trasAlta, abrirIdse, fichaBloqueada, irABandeja, trasCambioSueldo, formularioConDatos, avisoCierre, bajaDesdeEstatus,
    relacionDeEsquema, expedienteExistente, avisoExpedienteExistente, abrirExpedienteParaReingreso, ingresoDesdeEstatus, relacionesDe };
  prepararAlta();
  const bIdse = document.querySelector('nav.tabs button[data-tab="idse"]');
  if (bIdse) bIdse.addEventListener('click', () => { abrirIdse(); });
})();
