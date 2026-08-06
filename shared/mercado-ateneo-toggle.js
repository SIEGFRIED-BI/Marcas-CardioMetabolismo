/* shared/mercado-ateneo-toggle.js
 * Agrega a la seccion "Mercado IQVIA" un selector para ver la comparativa
 * multi-periodo contra DOS universos distintos:
 *
 *   Molecula          -> D.mol_perf         (lo de siempre, es el default)
 *   Mercado (Ateneo)  -> D.mercadosAteneo   (los 79 mercados curados del Ateneo)
 *
 * ANTES ESTO ERA LA VISTA ATC III Y EL USUARIO LA RECHAZO ("pero no me armaste como los
 * mercados del ateneo"). Los mercados del Ateneo no son clases ATC: son agrupaciones
 * curadas a mano ('Roxolan (Hipolipemeantes)', 'Betabloqueantes (Dilatrend-Nebilet)').
 *
 * UN PRODUCTO PUEDE ESTAR EN VARIOS MERCADOS, y esa es la gracia: los mercados del Ateneo
 * estan ANIDADOS. DILATREND se mide 13,66% contra 'Carvedilol (Dilatrend)' y 3,84% contra
 * 'Betabloqueantes (Dilatrend-Nebilet)'. Nunca se suman entre si -- se solapan a proposito.
 *
 * La tabla emite UNA FILA POR (PRODUCTO PROPIO, MERCADO), no una por familia. Es decision
 * del usuario, sobre un caso concreto: ACNECLIN (50mg tabl) y ACNECLIN AP (100mg caps
 * A.P.) son productos DISTINTOS pero viven en la misma familia del tablero
 * (dermatologia/MINOCYCLINE), que ademas no tiene budIqviaMap. Agrupando por familia
 * salian sumados en un 17,43% que no describe a ninguno de los dos: ACNECLIN AP es el
 * LIDER de su mercado con 15,42% y ACNECLIN esta 14no con 2,01%.
 * Por eso mercadosAteneo.filas es una lista de {label, mercado, propios}.
 *
 * Pedido del usuario: "mantene los que estan pero agrega por ejemplo para roxolan el
 * mercado de hipolipemeantes" / "no quiero agregar productos y demas, son formas
 * extras de analizar el mercado".
 * Ejemplo: ROXOLAN mide 2,0% contra el mercado de ROSUVASTATIN y ademas contra
 * 'Roxolan (Hipolipemeantes)', que es el universo ancho que se pidio.
 *
 * POR QUE NO HAY QUE TOCAR multi-period-table.js
 * ----------------------------------------------
 * renderMultiPeriodTable(containerId, opts) ya acepta opts.data y lo usa como si fuera
 * el dashboard entero. Y buildIqviaFamilies() solo lee, de cada producto,
 * monthly_vals + is_sie: el mercado lo arma sumando los monthly_vals y el MS%/IE/Var pp
 * los calcula por su cuenta (computeFamily / computeBrand). Asi que basta con pasarle un
 * objeto sintetico { mol_perf: ..., budIqviaMap: ... } armado desde D.mercadosAteneo.
 * Cero cambios en el bundle compartido -> no se toca la logica de render ni se corre el
 * riesgo de duplicarla inline (shared/check-render-parity.py).
 *
 * ATRIBUCION DEL MS% PROPIO
 * -------------------------
 * Un mercado contiene VARIAS marcas Siegfried (en 'Ara II (Diov-Entr-Exfo)' estan DIOVAN,
 * DIOVAN D, ENTRESTO, EXFORGE y EXFORGE D). buildIqviaFamilies calcula
 * own = is_sie && ownList.indexOf(prod) !== -1, con ownList = budIqviaMap[familia]. Por
 * eso cada fila pasa como budIqviaMap SU PROPIO producto (fila.propios), y mide solo ese
 * contra el mercado, no todo lo Siegfried que haya adentro. Sin esto, DILATREND y
 * DILATREND AP mostrarian las dos el mismo 4,00% en vez de 4,00% y 0,33%.
 */
(function (global) {
  'use strict';

  var WRAP_ID = 'mp-iqvia-wrap';
  var BAR_ID = 'mp-atc-bar';

  function getData() {
    try { if (typeof global.OTC_DASHBOARD !== 'undefined' && global.OTC_DASHBOARD) return global.OTC_DASHBOARD; } catch (e) {}
    try { if (typeof global.D !== 'undefined' && global.D) return global.D; } catch (e) {}
    return null;
  }

  /* Arma el objeto sintetico que espera renderMultiPeriodTable. La clave lleva el mercado
   * pegado ("ROXOLAN · Roxolan (Hipolipemeantes)") porque la fila es el producto pero el
   * universo es el mercado, y sin eso la tabla diria solo "ROXOLAN" con numeros que no
   * son los de su mercado de molecula. */
  function buildAtcData(D) {
    var mA = D && D.mercadosAteneo;
    if (!mA || !mA.mercados || !mA.filas) return null;
    var mp = {}, bim = {}, n = 0;
    // UNA FILA POR (PRODUCTO PROPIO, MERCADO), no una por familia.
    // Decision del usuario: "no son el mismo producto". ACNECLIN (50mg tabl) y ACNECLIN AP
    // (100mg caps A.P.) viven en la misma familia del tablero (dermatologia/MINOCYCLINE) y
    // esa familia no tiene budIqviaMap, asi que agrupar por familia los sumaba en un 17,43%
    // que no describe a ninguno: ACNECLIN AP es el LIDER de su mercado con 15,42% y
    // ACNECLIN esta 14no con 2,01%.
    mA.filas.forEach(function (f) {
      var c = mA.mercados[f.mercado];
      if (!c || !c.products || !c.products.length) return;
      var key = f.label + ' · ' + f.mercado;
      mp[key] = { products: c.products };
      bim[key] = f.propios || [];
      n++;
    });
    if (!n) return null;
    return { mol_perf: mp, budIqviaMap: bim };
  }

  function render(modo) {
    var D = getData();
    if (!D || typeof global.renderMultiPeriodTable !== 'function') return;
    var opts = { source: 'iqvia', data: D };
    if (modo === 'atc') {
      var alt = buildAtcData(D);
      if (alt) opts.data = alt;
    }
    try {
      global.renderMultiPeriodTable(WRAP_ID, opts);
    } catch (e) {
      if (global.console) console.error('[mp-atc]', e);
    }
  }

  function build() {
    var wrap = document.getElementById(WRAP_ID);
    if (!wrap || document.getElementById(BAR_ID)) return;      // idempotente
    var D = getData();
    if (!buildAtcData(D)) return;   // la linea no tiene la vista -> no se muestra nada
    var mA = D.mercadosAteneo;
    var nClases = Object.keys(mA.mercados).length;
    var nFilas = (mA.filas || []).length;

    var bar = document.createElement('div');
    bar.id = BAR_ID;
    bar.style.cssText = 'display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:0 0 8px;';
    bar.innerHTML =
      '<span style="font-family:\'IBM Plex Mono\',monospace;font-size:9px;font-weight:700;'
      + 'letter-spacing:.1em;text-transform:uppercase;color:#6b7280;">Universo</span>'
      + '<div style="display:inline-flex;background:#fff;border:1px solid #e5e7eb;'
      + 'border-radius:6px;overflow:hidden;">'
      + '<button type="button" data-modo="mol" style="padding:4px 10px;border:0;'
      + 'border-right:1px solid #f3f4f6;background:#b01e1e;color:#fff;cursor:pointer;'
      + 'font:600 10px/1.4 inherit;">Molécula</button>'
      + '<button type="button" data-modo="atc" style="padding:4px 10px;border:0;'
      + 'background:transparent;color:#525252;cursor:pointer;font:600 10px/1.4 inherit;">'
      + 'Mercado (Ateneo)</button>'
      + '</div>'
      + '<span id="' + BAR_ID + '-hint" style="font-size:9.5px;color:#6b7280;">'
      + 'Mercado de la molécula exacta.</span>';
    wrap.parentNode.insertBefore(bar, wrap);

    var hint = bar.querySelector('#' + BAR_ID + '-hint');
    var botones = bar.querySelectorAll('button[data-modo]');
    function setModo(modo) {
      for (var i = 0; i < botones.length; i++) {
        var on = botones[i].getAttribute('data-modo') === modo;
        botones[i].style.background = on ? '#b01e1e' : 'transparent';
        botones[i].style.color = on ? '#fff' : '#525252';
      }
      hint.textContent = modo === 'atc'
        ? 'Mercados del Ateneo — ' + nClases + ' mercados, ' + nFilas + ' filas. Universo '
          + 'más amplio que la molécula: una fila por producto y mercado, y un producto puede '
          + 'aparecer en más de uno (están anidados). No se suman entre sí: se solapan.'
        : 'Mercado de la molécula exacta.';
      render(modo);
    }
    for (var j = 0; j < botones.length; j++) {
      botones[j].addEventListener('click', function () {
        setModo(this.getAttribute('data-modo'));
      });
    }
    // No se re-renderiza al iniciar: la pagina ya dibujo la vista de molecula.
  }

  function init() {
    // Corre despues del init de la pagina, que es el que dibuja la tabla por primera vez.
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function () { setTimeout(build, 120); });
    } else {
      setTimeout(build, 120);
    }
  }
  init();
  global.__sfMercadoAtc = { build: build, render: render, buildAtcData: buildAtcData };
})(window);
