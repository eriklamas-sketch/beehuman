// =====================================================================
// BeeHuman · Campos de fecha en DD/MM/AAAA (9-nov-2026)
// El campo nativo <input type="date"> muestra el formato del idioma del
// NAVEGADOR (en inglés: MM/DD/AAAA). En movimientos laborales e IMSS eso es
// peligroso: 11/01/2026 puede leerse como 11 de enero o 1 de noviembre.
// Este módulo convierte cada <input type="date"> (también los que se crean
// después) en un campo de texto que siempre muestra DD/MM/AAAA:
//   - se escribe con máscara: 01112026 → 01/11/2026;
//   - un botón abre el calendario del navegador (opcional) y escribe DD/MM/AAAA;
//   - .value sigue devolviendo y aceptando AAAA-MM-DD, como el campo nativo,
//     así que el resto del código no cambia; una fecha incompleta o
//     inexistente vale '' (igual que el nativo).
// =====================================================================
(function () {
  'use strict';
  const nativo = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
  const ISO = /^(\d{4})-(\d{2})-(\d{2})$/, MX = /^(\d{2})\/(\d{2})\/(\d{4})$/;
  const existe = (a, m, d) => { const f = new Date(Date.UTC(a, m - 1, d)); return f.getUTCFullYear() === a && f.getUTCMonth() === m - 1 && f.getUTCDate() === d; };
  function aIso(texto) {
    const t = String(texto || '').trim();
    let m = MX.exec(t);
    if (m && existe(+m[3], +m[2], +m[1])) return `${m[3]}-${m[2]}-${m[1]}`;
    m = ISO.exec(t);
    if (m && existe(+m[1], +m[2], +m[3])) return t;
    return '';
  }
  function aMx(valor) {
    const m = ISO.exec(String(valor || '').trim());
    return m ? `${m[3]}/${m[2]}/${m[1]}` : String(valor || '');
  }
  function enmascarar(el) {
    const crudo = nativo.get.call(el);
    if (ISO.test(crudo.trim())) { nativo.set.call(el, aMx(crudo.trim())); return; } // pegado o capturado como AAAA-MM-DD
    const d = crudo.replace(/\D/g, '').slice(0, 8);
    const txt = d.length > 4 ? `${d.slice(0, 2)}/${d.slice(2, 4)}/${d.slice(4)}` : d.length > 2 ? `${d.slice(0, 2)}/${d.slice(2)}` : d;
    if (txt !== crudo) nativo.set.call(el, txt);
  }
  function validar(el) {
    const t = nativo.get.call(el).trim();
    el.setCustomValidity(t && !aIso(t) ? 'Escribe una fecha válida con formato DD/MM/AAAA.' : '');
  }

  function convertir(el) {
    if (el.dataset.fechaMx) return;
    el.dataset.fechaMx = '1';
    const inicial = el.getAttribute('value') || nativo.get.call(el);
    el.type = 'text';
    el.inputMode = 'numeric';
    el.autocomplete = 'off';
    el.maxLength = 10;
    if (!el.placeholder) el.placeholder = 'DD/MM/AAAA';
    el.classList.add('campo-fecha-mx');
    Object.defineProperty(el, 'value', {
      configurable: true,
      get() { return aIso(nativo.get.call(this)); },
      set(v) { nativo.set.call(this, aMx(v)); validar(this); },
    });
    nativo.set.call(el, aMx(inicial));
    el.addEventListener('input', () => { enmascarar(el); validar(el); });
    el.addEventListener('blur', () => validar(el));

    // Calendario opcional: usa el selector del navegador, pero el campo visible
    // siempre queda en DD/MM/AAAA.
    const sel = document.createElement('input');
    sel.type = 'date'; sel.tabIndex = -1; sel.className = 'campo-fecha-mx-sel'; sel.setAttribute('aria-hidden', 'true');
    sel.dataset.fechaMx = 'selector';
    const btn = document.createElement('button');
    btn.type = 'button'; btn.className = 'campo-fecha-mx-btn'; btn.title = 'Elegir en el calendario'; btn.setAttribute('aria-label', 'Elegir fecha en el calendario');
    btn.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2" d="M4 6h16v14H4zM4 10h16M8 3v4M16 3v4"/></svg>';
    btn.addEventListener('click', () => {
      sel.value = el.value || '';
      try { if (sel.showPicker) sel.showPicker(); else sel.click(); } catch (e) { sel.click(); }
    });
    sel.addEventListener('change', () => {
      if (!sel.value) return;
      el.value = sel.value;
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    });
    const caja = document.createElement('span');
    caja.className = 'campo-fecha-mx-caja';
    el.parentNode.insertBefore(caja, el);
    caja.appendChild(el); caja.appendChild(btn); caja.appendChild(sel);
    btn.disabled = el.disabled;
    new MutationObserver(() => { btn.disabled = el.disabled; caja.style.display = el.style.display === 'none' ? 'none' : ''; })
      .observe(el, { attributes: true, attributeFilter: ['disabled', 'style'] });
  }

  function revisar(raiz) {
    (raiz.querySelectorAll ? raiz.querySelectorAll('input[type="date"]:not([data-fecha-mx])') : []).forEach(convertir);
  }
  const css = document.createElement('style');
  css.textContent = `.campo-fecha-mx-caja{position:relative;display:block}
.campo-fecha-mx-caja>input.campo-fecha-mx{width:100%;padding-right:40px;font-variant-numeric:tabular-nums}
.campo-fecha-mx-btn{position:absolute;right:6px;top:50%;transform:translateY(-50%);margin:0!important;width:30px;height:30px;padding:0!important;display:flex;align-items:center;justify-content:center;border:0!important;background:transparent!important;color:var(--v21-texto-2,#5B6680)!important;box-shadow:none!important;cursor:pointer}
.campo-fecha-mx-btn:disabled{opacity:.35;cursor:default}
.campo-fecha-mx-sel{position:absolute;right:0;bottom:0;width:1px;height:1px;opacity:0;pointer-events:none;border:0;padding:0}`;
  document.head.appendChild(css);
  revisar(document);
  new MutationObserver((cambios) => cambios.forEach((c) => c.addedNodes.forEach((n) => { if (n.nodeType === 1) { if (n.matches && n.matches('input[type="date"]:not([data-fecha-mx])')) convertir(n); else revisar(n); } })))
    .observe(document.documentElement, { childList: true, subtree: true });
  window.BH_fechas = { aIso, aMx };
})();
