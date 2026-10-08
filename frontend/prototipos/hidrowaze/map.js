/* ==========================================================================
   Ygapé — Mapa da Rota (Leaflet integration)
   Usa dados reais: hidrovias.js, hidrovias_profundidade.js, estacoes.js
   Integração: ao calcular rota, exibe GeoJSON no mapa
   ========================================================================== */
(function(){
  'use strict';

  const CORES_DOMINIO = {
    'Federal':       '#1d4ed8',
    'Estadual':      '#0891b2',
    'Internacional': '#7c3aed'
  };
  const ROTULO_DOMINIO = {
    'Federal': 'Federal (interestadual)',
    'Estadual': 'Estadual (navegável)',
    'Internacional': 'Internacional (fronteira)'
  };
  const CORES_STATUS = { 'OK': '#16a34a', 'WARN': '#f59e0b', 'FAR': '#ef4444' };

  const FAIXAS_PROF = [
    { max: 2,  cor: '#fdd835', rotulo: '0–2 m (raso)' },
    { max: 5,  cor: '#fb8c00', rotulo: '2–5 m' },
    { max: 10, cor: '#2c7fb8', rotulo: '5–10 m' },
    { max: 99, cor: '#08306b', rotulo: '> 10 m (profundo)' },
  ];
  function corProfundidade(d) {
    if (d == null) return '#94a3b8';
    for (const fa of FAIXAS_PROF) if (d < fa.max) return fa.cor;
    return '#08306b';
  }

  let mapaRota = null;
  let rotaLayer = null;
  let estacoesLayer = null;
  let hidroviasLayer = null;
  let profundidadeLayer = null;
  let baseOsm = null;
  let baseSat = null;
  let rotaPendente = null;

  // Wait for global GeoJSON data
  function aguardarDados(callback) {
    const check = () => {
      if (window.HIDROVIAS && window.HIDROVIAS_PROF && window.ESTACOES) {
        callback();
      } else {
        setTimeout(check, 50);
      }
    };
    check();
  }

  function initMapa() {
    const container = document.getElementById('mapaRota');
    if (!container || mapaRota) return;

    mapaRota = L.map('mapaRota', {
      zoomControl: false,
      attributionControl: false,
      tap: true,
      touchZoom: true,
      scrollWheelZoom: false,
      doubleClickZoom: false,
      boxZoom: false,
      keyboard: false
    }).setView([-3.05, -59.2], 8);

    L.control.zoom({ position: 'bottomright' }).addTo(mapaRota);

    baseOsm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19, attribution: '&copy; OpenStreetMap'
    }).addTo(mapaRota);
    baseSat = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 19, attribution: '&copy; Esri'
    });

    // Hidrovias (domínio)
    hidroviasLayer = L.geoJSON(window.HIDROVIAS, {
      style: (f) => ({
        color: CORES_DOMINIO[f.properties.dominio] || '#64748b',
        weight: f.properties.nustrahler >= 8 ? 2.5 : f.properties.nustrahler >= 6 ? 1.8 : 1.2,
        opacity: 0.8
      }),
      onEachFeature: (f, l) => {
        const p = f.properties;
        const fmt = (v, d=1) => (v == null ? '—' : Number(v).toLocaleString('pt-BR', { maximumFractionDigits: d }));
        l.bindPopup(`
          <div class="station-popup" style="font-size:12px;line-height:1.4">
            <h6 style="margin:0 0 4px;font-weight:700">${p.rio || 'Rio sem nome'}</h6>
            <span class="badge" style="background:${CORES_DOMINIO[p.dominio]};font-size:10px">${ROTULO_DOMINIO[p.dominio] || p.dominio}</span>
            <table class="mt-2 mb-0" style="font-size:11px">
              <tr><td>Strahler</td><td class="fw-semibold ps-2">${p.nustrahler ?? '—'}</td></tr>
              <tr><td>Prof. média</td><td class="fw-semibold ps-2">${fmt(p.hig_drn_depth_m)} m</td></tr>
              <tr><td>Largura média</td><td class="fw-semibold ps-2">${fmt(p.hig_drn_width_m, 0)} m</td></tr>
              <tr><td>Vazão anual</td><td class="fw-semibold ps-2">${fmt(p.hig_drn_annual_flow, 0)} m³/s</td></tr>
            </table>
          </div>`);
      }
    }).addTo(mapaRota);

    // Profundidade (por trecho)
    profundidadeLayer = L.geoJSON(window.HIDROVIAS_PROF, {
      style: (f) => ({
        color: corProfundidade(f.properties.hig_drn_depth_m),
        weight: f.properties.nustrahler >= 8 ? 2.5 : f.properties.nustrahler >= 6 ? 1.8 : 1.2,
        opacity: 0.85
      }),
      onEachFeature: (f, l) => {
        const p = f.properties;
        const fmt = (v, d=1) => (v == null ? '—' : Number(v).toLocaleString('pt-BR', { maximumFractionDigits: d }));
        l.bindPopup(`
          <div class="station-popup" style="font-size:12px;line-height:1.4">
            <h6 style="margin:0 0 4px;font-weight:700">${p.rio || 'Rio sem nome'}</h6>
            <span class="badge text-bg-light border" style="font-size:10px">${ROTULO_DOMINIO[p.dominio] || p.dominio}</span>
            <table class="mt-2 mb-0" style="font-size:11px">
              <tr><td>Prof. média</td><td class="fw-semibold ps-2">${fmt(p.hig_drn_depth_m)} m</td></tr>
              <tr><td>Largura média</td><td class="fw-semibold ps-2">${fmt(p.hig_drn_width_m, 0)} m</td></tr>
              <tr><td>Vazão anual</td><td class="fw-semibold ps-2">${fmt(p.hig_drn_annual_flow, 0)} m³/s</td></tr>
            </table>
          </div>`);
      }
    });

    // Estações ANA
    estacoesLayer = L.geoJSON(window.ESTACOES, {
      pointToLayer: (f, latlng) => L.circleMarker(latlng, {
        radius: 6, color: '#ffffff', weight: 1.5,
        fillColor: CORES_STATUS[f.properties.status] || '#64748b', fillOpacity: 0.95
      }),
      onEachFeature: (f, l) => {
        const p = f.properties;
        const fmt = (v, d=1) => (v == null ? '—' : Number(v).toLocaleString('pt-BR', { maximumFractionDigits: d }));
        l.bindPopup(`
          <div class="station-popup" style="font-size:12px;line-height:1.4">
            <h6 style="margin:0 0 4px;font-weight:700">${p.nome}</h6>
            <div class="text-muted mb-1" style="font-size:11px">${p.codigo} · ${p.rio} · ${p.municipio}</div>
            <span class="badge" style="background:${CORES_STATUS[p.status]};font-size:10px">${p.status}</span>
            <span class="badge text-bg-light border ms-1" style="font-size:10px">${ROTULO_DOMINIO[p.dominio] || p.dominio}</span>
            <table class="mt-2 mb-0" style="font-size:11px">
              <tr><td>Rio associado</td><td class="fw-semibold ps-2">${p.rio_bhae || '—'}</td></tr>
              <tr><td>Dist. ao trecho</td><td class="fw-semibold ps-2">${fmt(p.distancia_m, 0)} m</td></tr>
              <tr><td>Prof. média (AHGN)</td><td class="fw-semibold ps-2">${fmt(p.depth_m)} m</td></tr>
              <tr><td>Largura média</td><td class="fw-semibold ps-2">${fmt(p.width_m, 0)} m</td></tr>
            </table>
          </div>`);
      }
    }).addTo(mapaRota);

    L.control.layers(
      { 'Ruas (OSM)': baseOsm, 'Satélite (Esri)': baseSat },
      { 'Hidrovias (domínio)': hidroviasLayer, 'Profundidade (trecho)': profundidadeLayer, 'Estações ANA': estacoesLayer },
      { position: 'topleft', collapsed: true }
    ).addTo(mapaRota);

    setTimeout(() => {
      mapaRota.invalidateSize();
      if (rotaPendente) {
        const [geojson, origemNome, destinoNome] = rotaPendente;
        rotaPendente = null;
        mostrarRota(geojson, origemNome, destinoNome);
      }
    }, 150);
  }

  function mostrarRota(geojson, origemNome, destinoNome) {
    if (!mapaRota) {
      rotaPendente = [geojson, origemNome, destinoNome];
      ensureInit();
      return;
    }
    if (rotaLayer) {
      mapaRota.removeLayer(rotaLayer);
      rotaLayer = null;
    }
    if (!geojson) return;

    rotaLayer = L.geoJSON(geojson, {
      style: { color: '#ff6b00', weight: 4, opacity: 0.95, dashArray: '10, 6', lineCap: 'round', lineJoin: 'round' },
      onEachFeature: (f, l) => {
        const p = f.properties || {};
        const fmt = (v, d=1) => (v == null ? '—' : Number(v).toLocaleString('pt-BR', { maximumFractionDigits: d }));
        l.bindPopup(`
          <div class="station-popup" style="font-size:12px;line-height:1.4">
            <h6 style="margin:0 0 4px;font-weight:700;color:#ff6b00"><i class="bi bi-signpost-2 me-1"></i>Rota Calculada</h6>
            <div class="text-muted mb-1" style="font-size:11px">${origemNome} → ${destinoNome}</div>
            <table class="mt-2 mb-0" style="font-size:11px">
              <tr><td>Distância</td><td class="fw-semibold ps-2">${p.distance_km ? fmt(p.distance_km) + ' km' : '—'}</td></tr>
              <tr><td>Tempo estimado</td><td class="fw-semibold ps-2">${p.tempo_h ? fmt(p.tempo_h) + ' h' : '—'}</td></tr>
              <tr><td>Segurança</td><td class="fw-semibold ps-2">${p.seguranca_1_10 ? p.seguranca_1_10 + '/10' : '—'}</td></tr>
            </table>
          </div>`);
      }
    }).addTo(mapaRota);

    if (rotaLayer.getBounds().isValid()) {
      mapaRota.fitBounds(rotaLayer.getBounds(), { padding: [40, 40], maxZoom: 11 });
    }
  }

  function limparRota() {
    if (rotaLayer && mapaRota) {
      mapaRota.removeLayer(rotaLayer);
      rotaLayer = null;
    }
  }

  // Lazy init: only initialize map when explicitly called (after result section is visible)
  function ensureInit() {
    if (mapaRota) { mapaRota.invalidateSize(); return; }
    aguardarDados(initMapa);
  }

  window.YgapeMapa = {
    ensureInit: ensureInit,
    mostrarRota: mostrarRota,
    limparRota: limparRota,
    getMap: () => mapaRota
  };
})();
