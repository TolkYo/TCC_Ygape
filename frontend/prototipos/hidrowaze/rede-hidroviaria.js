(function () {
  'use strict';
  const toast = document.getElementById('rnToast');
  let timer;
  function showToast(message) {
    toast.textContent = message;
    toast.classList.add('is-visible');
    clearTimeout(timer);
    timer = setTimeout(() => toast.classList.remove('is-visible'), 3200);
  }
  document.querySelectorAll('.rn-stop').forEach(stop => {
    const select = () => showToast(`${stop.dataset.port}: condições operacionais disponíveis para consulta.`);
    stop.addEventListener('click', select);
    stop.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); select(); } });
  });
  document.getElementById('btnCamadas').addEventListener('click', event => {
    const active = !document.body.classList.toggle('rn-layers-off');
    event.currentTarget.setAttribute('aria-pressed', String(active));
    showToast(active ? 'Camadas completas exibidas.' : 'Camadas secundárias ocultadas.');
  });
  document.getElementById('btnRota').addEventListener('click', () => showToast('Detalhes da rota: 194 km · previsão de 8h40 · condição favorável.'));
  document.getElementById('btnAlerta').addEventListener('click', () => showToast('Dois trechos do Solimões exigem atenção ao calado.'));
}());
