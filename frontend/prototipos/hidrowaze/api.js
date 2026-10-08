/* Cliente HTTP compartilhado pelo protótipo HidroWize. */
(function (global) {
  'use strict';
  const DEFAULT_BASE_URL = 'http://localhost:8000/api/v1';
  const configured = document.querySelector('meta[name="hidrowize-api-url"]')?.content;

  function baseUrl() {
    return (configured || localStorage.getItem('hidrowize-api-url') || DEFAULT_BASE_URL).replace(/\/$/, '');
  }
  function token() { return localStorage.getItem('hidrowize-access-token'); }

  class ApiError extends Error {
    constructor(message, status, code) {
      super(message); this.name = 'ApiError'; this.status = status || 0; this.code = code || 'network_error';
    }
  }

  async function request(path, options) {
    const opts = options || {};
    const headers = new Headers(opts.headers || {});
    headers.set('Accept', 'application/json');
    if (opts.body) headers.set('Content-Type', 'application/json');
    if (token()) headers.set('Authorization', 'Bearer ' + token());
    let response;
    try {
      response = await fetch(baseUrl() + path, { ...opts, headers, signal: AbortSignal.timeout(60000) });
    } catch (_) {
      throw new ApiError('Não foi possível conectar ao serviço HidroWize.', 0, 'network_error');
    }
    let payload = null;
    try { payload = await response.json(); } catch (_) { /* resposta inválida */ }
    if (!response.ok || !payload || payload.success !== true) {
      const error = payload?.error || {};
      throw new ApiError(error.message || 'Não foi possível concluir a solicitação.', response.status, error.code);
    }
    return payload.data;
  }

  global.HidroWizeApi = {
    ApiError,
    baseUrl,
    hasSession: () => Boolean(token()),
    calcularRota: input => request('/rotas/calcular', { method: 'POST', body: JSON.stringify(input) }),
    listarEstacoes: () => request('/estacoes'),
    listarUsuarios: () => request('/usuarios'),
    criarUsuario: input => request('/usuarios', { method: 'POST', body: JSON.stringify(input) }),
    coletarNiveis: input => request('/niveis/coletar', { method: 'POST', body: JSON.stringify(input || {}) }),
    configurar: (base, accessToken) => {
      if (base) localStorage.setItem('hidrowize-api-url', base.replace(/\/$/, ''));
      if (accessToken) localStorage.setItem('hidrowize-access-token', accessToken);
    }
  };
})(window);
