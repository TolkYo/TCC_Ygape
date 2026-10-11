/* ==========================================================================
   Ygapé — Visão do Capitão (dados operacionais da API)
   WCAG/e-MAG: aria-live, gestão de foco, validação acessível, contraste
   Integração real: POST /api/v1/rotas/calcular + Dexie (offline A*)
   ========================================================================== */
(function(){
  'use strict';
  let installPrompt = null;
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    installPrompt = event;
    const button = document.getElementById('btnInstalarApp');
    if (button) button.hidden = false;
  });
  window.addEventListener('load', () => {
    if ('serviceWorker' in navigator) navigator.serviceWorker.register('./sw.js').catch(() => {});
  });
  document.addEventListener('click', async event => {
    if (event.target.closest('#btnInstalarApp') && installPrompt) {
      installPrompt.prompt();
      await installPrompt.userChoice;
      installPrompt = null;
      const button = document.getElementById('btnInstalarApp');
      if (button) button.hidden = true;
    }
  });
  window.addEventListener('appinstalled', () => {
    const button = document.getElementById('btnInstalarApp');
    if (button) button.hidden = true;
  });
  const state = { estacoes: [] };
  let apiStatus = document.getElementById('apiStatus');
  if (!apiStatus) {
    apiStatus = document.createElement('div');
    apiStatus.id = 'apiStatus';
    apiStatus.setAttribute('role', 'status');
    apiStatus.className = 'text-center mt-2 small text-secondary';
    apiStatus.textContent = 'Modo local: entre para consultar a rota calculada pela API.';
    const help = document.getElementById('help-calcular');
    if (help) help.insertAdjacentElement('afterend', apiStatus);
  }

  function setApiStatus(message, remote) {
    if (!apiStatus) return;
    apiStatus.textContent = message;
    apiStatus.className = 'text-center mt-2 small ' + (remote ? 'text-success' : 'text-secondary');
  }

  function normalizarTrechos(items) {
    return (items || []).map(t => ({
      origem: t.no_origem || t.origem || 'Trecho', destino: t.no_destino || t.destino || 'seguinte',
      km: Number(t.distancia_km ?? t.km ?? 0), profundidadeM: Number(t.profundidade_m ?? t.profundidadeM ?? 0),
      transitavel: t.transitavel !== false
    }));
  }

  async function obterRota(origem, destino, calado, velocidade) {
    if (!window.HidroWizeApi) {
      setApiStatus('Cliente da API indisponível.', false);
      announce('Cliente da API indisponível.', true);
      return null;
    }
    try {
      const data = await window.HidroWizeApi.calcularRota({
        origem_nome: origem, destino_nome: destino, calado_m: calado, margem_seguranca_m: 0.5,
        velocidade_embarcacao_kmh: velocidade, monitorar: false
      });
      const trechos = normalizarTrechos(data.items);
      const profMin = trechos.length ? Math.min(...trechos.map(t => t.profundidadeM)) : calado + 0.5;
      const folga = profMin - (calado + 0.5);
      const criticos = Number(data.trechos_criticos ?? trechos.filter(t => !t.transitavel).length);
      let nota = 10 - Math.min(criticos * 2, 4);
      if (folga < 1.2) nota -= 2;
      if (folga < 0.4) nota -= 3;
      setApiStatus('Dados atualizados pela API.', true);
      return { km:Number(data.distancia_total_km), tempo:Number(data.tempo_total_h), profMin, folga,
        nota:Math.max(1, Math.min(10, Math.round(nota))), criticos, trechos, geojson:data.geojson };
    } catch (_) {
      setApiStatus('API indisponível. Nenhuma rota foi calculada.', false);
      announce('Não foi possível consultar a API.', true);
      return null;
    }
  }

  let locais = [];

  const selO = document.getElementById('origem');
  const selD = document.getElementById('destino');
  function optionList(sel, selected){
    if (!sel) return;
    sel.innerHTML = '<option value="">Selecione um porto</option>' + locais.map(l=> `<option value="${l}" ${l===selected?'selected':''}>${l}</option>`).join('');
  }

  function renderPortos(){
    const wrap = document.getElementById('listaPortos');
    const total = document.getElementById('totalPortos');
    if (!wrap) return;
    if (total) total.textContent = `${locais.length} ${locais.length === 1 ? 'porto' : 'portos'}`;
    if (!locais.length) {
      wrap.innerHTML = '<p class="small text-secondary mb-0" role="status">Nenhum porto disponível. Atualize os dados para carregar a lista.</p>';
      return;
    }
    wrap.innerHTML = locais.map(local => `
      <article class="hw-port-item" role="listitem">
        <span class="hw-port-item__name"><i class="bi bi-geo-alt-fill" aria-hidden="true"></i>${local}</span>
        <span class="hw-port-item__actions">
          <button class="btn btn-sm btn-outline-success" type="button" data-port-role="origem" data-port-name="${local}">Origem</button>
          <button class="btn btn-sm btn-outline-danger" type="button" data-port-role="destino" data-port-name="${local}">Destino</button>
        </span>
      </article>`).join('');
  }

  document.getElementById('listaPortos')?.addEventListener('click', event => {
    const button = event.target.closest('button[data-port-role]');
    if (!button) return;
    const select = button.dataset.portRole === 'origem' ? selO : selD;
    select.value = button.dataset.portName;
    select.dispatchEvent(new Event('change', { bubbles: true }));
    announce(`${button.dataset.portName} definido como ${button.dataset.portRole}.`);
  });

  optionList(selO, '');
  optionList(selD, '');
  renderPortos();

  const caladoEl = document.getElementById('calado');
  const velEl = document.getElementById('velocidade');
  const profMinEl = document.getElementById('profMin');
  const announcer = document.getElementById('announcer');
  const announcerAssertive = document.getElementById('announcer-assertive');

  function announce(msg, assertive){
    const el = assertive ? announcerAssertive : announcer;
    if(!el) return;
    el.textContent = '';
    setTimeout(()=>{ el.textContent = msg; }, 50);
  }

  function atualizaProfMin(){
    const c = parseFloat(caladoEl.value);
    if(isNaN(c) || c < 0.5 || c > 6){ profMinEl.textContent = '—'; return; }
    profMinEl.textContent = (c+0.5).toFixed(2).replace('.',',')+' m';
  }
  caladoEl.addEventListener('input', ()=>{ clearErr('calado'); atualizaProfMin(); });
  caladoEl.addEventListener('blur', atualizaProfMin);
  velEl.addEventListener('input', ()=> clearErr('velocidade'));
  selO.addEventListener('change', ()=> clearErr('origem'));
  selD.addEventListener('change', ()=> clearErr('destino'));
  atualizaProfMin();

  // Inverter com anúncio acessível
  const btnSwap = document.getElementById('btnSwap');
  btnSwap.addEventListener('click',()=>{
    const a=selO.value; selO.value=selD.value; selD.value=a;
    clearErr('origem'); clearErr('destino');
    announce('Origem e destino invertidos: '+selO.value+' para '+selD.value);
    selO.focus();
  });

  // Acessibilidade: alto contraste e fonte (e-MAG)
  const btnContraste = document.getElementById('btnA11yContraste');
  if(btnContraste){
    const saved = localStorage.getItem('hw-contrast')==='1';
    if(saved){ document.documentElement.classList.add('hw-contrast'); btnContraste.setAttribute('aria-pressed','true'); }
    btnContraste.addEventListener('click',()=>{
      const on = document.documentElement.classList.toggle('hw-contrast');
      btnContraste.setAttribute('aria-pressed', String(on));
      localStorage.setItem('hw-contrast', on?'1':'0');
      announce(on ? 'Alto contraste ativado' : 'Alto contraste desativado');
    });
  }
  const btnFonte = document.getElementById('btnA11yFonte');
  if(btnFonte){
    let lvl = parseInt(localStorage.getItem('hw-fontlvl')||'0',10);
    applyFont(lvl);
    btnFonte.addEventListener('click',()=>{
      lvl = (lvl+1)%3;
      applyFont(lvl);
      localStorage.setItem('hw-fontlvl', String(lvl));
      announce('Tamanho da fonte '+(lvl===0?'normal':lvl===1?'aumentado':'grande'));
    });
    function applyFont(l){
      document.documentElement.style.fontSize = l===0?'16px': l===1?'18px':'20px';
    }
  }

  // Estações
  function renderEstacoes(){
    const wrap=document.getElementById('listaEstacoes');
    if(!wrap) return;
    const cls = s => s==='ok'?'ok': s==='alerta'?'warn':'bad';
    wrap.innerHTML = state.estacoes.map(e=>`
      <article class="hw-trecho ${cls(e.status)}" role="listitem">
        <span class="hw-trecho-dot" aria-hidden="true"></span>
        <div class="d-flex align-items-center gap-2 flex-grow-1">
          <span class="badge text-bg-light border hw-code" aria-label="Código da estação ${e.codigo}">${e.codigo}</span>
          <div>
            <div class="fw-bold" style="font-size:.92rem">${e.nome}</div>
            <div class="small text-secondary">${e.rio} · ${e.municipio}</div>
          </div>
        </div>
        <div class="text-end">
          <div class="fw-bold" aria-label="Nível ${(e.nivelCm/100).toFixed(2).replace('.',',')} metros">${(e.nivelCm/100).toFixed(2).replace('.',',')} m</div>
          <div class="small text-secondary">${e.atualizado} · ${e.chuvaMm} mm</div>
        </div>
      </article>
    `).join('') || '<p class="small text-secondary mb-0" role="status">Nenhuma estação carregada. Faça login e atualize os dados.</p>';
  }

  async function atualizarEstacoesDaApi() {
    if (!window.HidroWizeApi) return false;
    try {
      const data = await window.HidroWizeApi.listarEstacoes();
      state.estacoes = (data.items || []).map(e => ({
        codigo: e.codigo_estacao, nome: e.nome_estacao, rio: e.nome_rio, municipio: e.municipio,
        nivelCm: Number(e.nivel_atual_cm || 0), chuvaMm: 0,
        atualizado: e.atualizado_em ? new Date(e.atualizado_em).toLocaleTimeString('pt-BR', { hour:'2-digit', minute:'2-digit' }) : 'agora',
        status: 'ok'
      }));
      locais = [...new Set(state.estacoes.map(e => e.nome).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'pt-BR'));
      optionList(selO, selO.value);
      optionList(selD, selD.value);
      renderPortos();
      renderEstacoes();
      setApiStatus('Estações atualizadas pela API.', true);
      return true;
    } catch (_) {
      setApiStatus('API indisponível. Exibindo estações locais.', false);
      return false;
    }
  }
  renderEstacoes();
  atualizarEstacoesDaApi();
  const btnAtualizar = document.getElementById('btnAtualizar');
  if(btnAtualizar){
    btnAtualizar.addEventListener('click',()=>{
      const origHTML = btnAtualizar.innerHTML;
      btnAtualizar.disabled=true;
      btnAtualizar.innerHTML='<span class="spinner-border spinner-border-sm" aria-hidden="true"></span> Atualizando…';
      announce('Atualizando estações');
      atualizarEstacoesDaApi().then(remote => {
        btnAtualizar.disabled=false; btnAtualizar.innerHTML=origHTML;
        if (!remote) renderEstacoes();
        announce(remote ? 'Estações atualizadas pela API.' : 'Não foi possível carregar as estações.');
      });
    });
  }

  // Histórico
  const histWrap=document.getElementById('listaHistorico');
  const badgeHist=document.getElementById('badgeHist');
  let rotasSalvas = [];
  function renderHist(){
    badgeHist.textContent = rotasSalvas.length;
    badgeHist.setAttribute('aria-label', rotasSalvas.length+' rotas salvas');
    histWrap.innerHTML = rotasSalvas.map(r=>`
      <div class="hw-trecho ok" role="listitem">
        <i class="bi bi-bookmark-fill text-primary" aria-hidden="true"></i>
        <div class="flex-grow-1">
          <div class="fw-bold">${r.origem} → ${r.destino}</div>
          <div class="small text-secondary">${r.data} · calado ${r.caladoM} m · ${r.km} km</div>
        </div>
        <span class="badge ${r.status==='ok'?'text-bg-success':r.status==='alerta'?'text-bg-warning':'text-bg-danger'}" aria-label="Status ${r.status}">${r.status}</span>
      </div>
    `).join('') || '<div class="small text-secondary" role="status">Nenhuma rota salva ainda. Calcule e salve a primeira.</div>';
  }
  renderHist();

  // Notificações
  const notifs = document.getElementById('listaNotifs');
  if(notifs) notifs.innerHTML = '<p class="small text-secondary" role="status">Nenhuma notificação disponível.</p>';

  // Segurança 1-10
  function segurancaMeta(nota){
    if(nota>=8) return {cls:'text-bg-success', rot:'Muito segura — folga ampla', desc:'Profundidade bem acima do calado + margem. Rota estável mesmo com variação de nível.'};
    if(nota>=6) return {cls:'text-bg-success', rot:'Boa — margem confortável', desc:'Folga suficiente. Apenas 1 trecho exige atenção (Careiro). Desvio já aplicado.'};
    if(nota>=4) return {cls:'text-bg-warning', rot:'Moderada — exige atenção', desc:'Pouca folga em 2+ trechos. Verifique o nível nas últimas 6 horas antes de zarpar.'};
    return {cls:'text-bg-danger', rot:'Baixa — risco de encalhe', desc:'Profundidade próxima ao limite. Considere reduzir o calado ou aguardar a cheia.'};
  }
  function renderSafety(nota){
    const meta=segurancaMeta(nota);
    document.getElementById('resSeg').textContent=nota;
    document.getElementById('resSegRotulo').textContent=meta.rot;
    document.getElementById('resSegRotulo').className='small fw-bold '+(nota>=6?'text-success':nota>=4?'text-warning':'text-danger');
    document.getElementById('safetyBadge').textContent=nota+'/10';
    document.getElementById('safetyBadge').className='hw-safety-badge '+meta.cls;
    document.getElementById('safetyDesc').textContent=meta.desc;
    const scale=document.getElementById('safetyScale');
    scale.setAttribute('aria-label','Escala de segurança: '+nota+' de 10 preenchidos, '+meta.rot);
    scale.innerHTML='';
    for(let i=1;i<=10;i++){
      const d=document.createElement('div');
      d.className='hw-safety-step '+(i<=nota?'on ':'')+(i<=3?'low':i<=6?'mid':'high');
      d.setAttribute('aria-hidden','true');
      scale.appendChild(d);
    }
  }

  // Validação acessível
  function setErr(id, msg){
    const el = document.getElementById(id);
    const err = document.getElementById('err-'+id);
    if(el){ el.setAttribute('aria-invalid','true'); el.classList.add('is-invalid'); }
    if(err){ err.textContent = msg; }
  }
  function clearErr(id){
    const el = document.getElementById(id);
    const err = document.getElementById('err-'+id);
    if(el){ el.removeAttribute('aria-invalid'); el.classList.remove('is-invalid'); }
    if(err){ err.textContent = ''; }
  }
  function clearAllErr(){ ['origem','destino','calado','velocidade'].forEach(clearErr); }

  const form=document.getElementById('formRota');
  const resSec=document.getElementById('resultado');
  const btnCalc=document.getElementById('btnCalcular');
  const resultadoConteudo=resSec?.querySelector(':scope > .card-body');
  const resultadoCabecalho=resSec?.querySelector('.hw-result-head');
  const linkVerMapa=document.getElementById('linkVerMapa');
  const figuraMapa=document.getElementById('sec-mapa');
  let btnResultadoToggle=null;

  if (resultadoConteudo && resultadoCabecalho) {
    resultadoConteudo.id='resultadoConteudo';
    const badge=document.getElementById('resBadge');
    const controls=document.createElement('div');
    controls.className='d-flex align-items-center gap-2';
    if (badge) controls.appendChild(badge);
    btnResultadoToggle=document.createElement('button');
    btnResultadoToggle.type='button';
    btnResultadoToggle.className='hw-result-toggle';
    btnResultadoToggle.setAttribute('aria-controls','resultadoConteudo');
    btnResultadoToggle.innerHTML='<i class="bi bi-chevron-up" aria-hidden="true"></i>';
    controls.appendChild(btnResultadoToggle);
    resultadoCabecalho.appendChild(controls);
  }

  function alternarResultado(forceOpen) {
    if (!resultadoConteudo || !btnResultadoToggle) return;
    const aberto=typeof forceOpen==='boolean' ? forceOpen : resultadoConteudo.hidden;
    resultadoConteudo.hidden=!aberto;
    btnResultadoToggle.setAttribute('aria-expanded', String(aberto));
    btnResultadoToggle.setAttribute('aria-label', aberto ? 'Recolher detalhes do resultado' : 'Expandir detalhes do resultado');
  }
  if (btnResultadoToggle) btnResultadoToggle.addEventListener('click',()=>alternarResultado());

  function atualizarTamanhoMapa(){
    if (!window.YgapeMapa) return;
    window.YgapeMapa.ensureInit();
    setTimeout(()=>window.YgapeMapa.getMap()?.invalidateSize(), 180);
  }

  function fecharMapaAmpliado(){
    if (!figuraMapa?.classList.contains('hw-map-expanded')) return;
    figuraMapa.classList.remove('hw-map-expanded');
    document.body.style.overflow='';
    atualizarTamanhoMapa();
    linkVerMapa?.focus();
  }

  if (linkVerMapa && figuraMapa) {
    const btnFecharMapa=document.createElement('button');
    btnFecharMapa.type='button';
    btnFecharMapa.className='hw-map-close';
    btnFecharMapa.hidden=true;
    btnFecharMapa.setAttribute('aria-label','Fechar mapa ampliado');
    btnFecharMapa.innerHTML='<i class="bi bi-x-lg" aria-hidden="true"></i>';
    figuraMapa.appendChild(btnFecharMapa);

    linkVerMapa.addEventListener('click',(event)=>{
      event.preventDefault();
      figuraMapa.classList.add('hw-map-expanded');
      document.body.style.overflow='hidden';
      btnFecharMapa.hidden=false;
      atualizarTamanhoMapa();
      btnFecharMapa.focus();
    });
    btnFecharMapa.addEventListener('click',()=>{
      btnFecharMapa.hidden=true;
      fecharMapaAmpliado();
    });
    document.addEventListener('keydown',(event)=>{
      if (event.key==='Escape' && figuraMapa.classList.contains('hw-map-expanded')) {
        btnFecharMapa.hidden=true;
        fecharMapaAmpliado();
      }
    });
  }

  /* ---- Roteamento sobre a malha hidrográfica real (HIDROVIAS_PROF) ----
     Usa Dijkstra nos trechos de rio, preferindo segmentos mais profundos
     e de maior ordem (nustrahler). Fallback: linha reta simplificada. */
  let malhaCache = null;

  function geoDist(a, b){ // a,b = [lon,lat]
    const R=6371, dLat=(b[1]-a[1])*Math.PI/180, dLon=(b[0]-a[0])*Math.PI/180;
    const s=Math.sin(dLat/2)**2 + Math.cos(a[1]*Math.PI/180)*Math.cos(b[1]*Math.PI/180)*Math.sin(dLon/2)**2;
    return 2*R*Math.asin(Math.sqrt(s));
  }

  function chainsDe(feat){
    const g=feat.geometry;
    if(!g) return [];
    if(g.type==='LineString') return [g.coordinates];
    if(g.type==='MultiLineString') return g.coordinates;
    return [];
  }

  function construirMalha(){
    if (malhaCache) return malhaCache;
    const features = (window.HIDROVIAS_PROF && window.HIDROVIAS_PROF.features) || [];
    const nodes=[];                    // [lon,lat]
    const adj=[];                      // adj[id] = [{to,w,depth,strahler}]
    const map=new Map();
    let count=0;
    const addNode=(x,y)=>{
      const k=x.toFixed(5)+','+y.toFixed(5);
      let id=map.get(k);
      if(id===undefined){
        id=nodes.length;
        nodes.push([x,y]);
        adj.push([]);
        map.set(k,id);
        if(++count>200000){ map.clear(); throw new Error('limite'); }
      }
      return id;
    };
    const addEdge=(a,b,w,depth,strahler)=>{
      adj[a].push({to:b,w,depth,strahler});
      adj[b].push({to:a,w,depth,strahler});
    };
    for(const f of features){
      const p=f.properties||{};
      const depth=typeof p.hig_drn_depth_m==='number'&&isFinite(p.hig_drn_depth_m)?p.hig_drn_depth_m:5;
      const strahler=p.nustrahler||0;
      for(const ch of chainsDe(f)){
        if(!ch||ch.length<2) continue;
        const ids=ch.map(c=>addNode(c[0],c[1]));
        for(let i=0;i<ids.length-1;i++){
          addEdge(ids[i],ids[i+1], geoDist(ch[i],ch[i+1]), depth, strahler);
        }
      }
    }
    malhaCache={nodes,adj};
    return malhaCache;
  }

  function snapParaPonto(malha, ref){ // projeta ref na malha
    const features=(window.HIDROVIAS_PROF&&window.HIDROVIAS_PROF.features)||[];
    let best=null;
    for(const f of features){
      for(const ch of chainsDe(f)){
        for(let i=0;i<ch.length-1;i++){
          const ax=ch[i][0], ay=ch[i][1], bx=ch[i+1][0], by=ch[i+1][1];
          const dx=bx-ax, dy=by-ay, l2=(dx*dx+dy*dy)||1e-12;
          let t=((ref[0]-ax)*dx+(ref[1]-ay)*dy)/l2;
          t=Math.max(0,Math.min(1,t));
          const x=ax+dx*t, y=ay+dy*t;
          const d=geoDist(ref,[x,y]);
          if(!best||d<best.d) best={d,x,y, sa:ch[i], sb:ch[i+1]};
        }
      }
    }
    return best;
  }

  function injetarPonto(malha, ref){ // insere nó na malha e conecta nos extremos do trecho
    const snap=snapParaPonto(malha, ref);
    if(!snap) return null;
    const {nodes}=malha, {adj}=malha;
    const map=new Map(); nodes.forEach((n,i)=>map.set(n[0].toFixed(5)+','+n[1].toFixed(5), i));
    const addN=(x,y)=>{
      const k=x.toFixed(5)+','+y.toFixed(5);
      if(map.has(k)) return map.get(k);
      const id=nodes.length; nodes.push([x,y]); adj.push([]); map.set(k,id); return id;
    };
    const push=(a,b)=>{
      const w=geoDist(nodes[a],nodes[b]);
      adj[a].push({to:b,w,depth:5,strahler:0});
      adj[b].push({to:a,w,depth:5,strahler:0});
    };
    const s=addN(snap.x,snap.y);
    const e1=addN(snap.sa[0],snap.sa[1]);
    const e2=addN(snap.sb[0],snap.sb[1]);
    push(s,e1); push(s,e2);
    return s;
  }

  // Dijkstra com heap binário + penalidade por profundidade baixa
  function dijkstraRio(malha, inicio, fim, calado){
    const minProf=(calado||1.8)+0.5;
    const N=malha.nodes.length;
    const dist=new Float64Array(N); dist.fill(Infinity); dist[inicio]=0;
    const prev=new Int32Array(N); prev.fill(-1);
    const pq=[];
    const pushP=(prio,node)=>{
      pq.push([prio,node]);
      let i=pq.length-1;
      while(i>0){
        const p=(i-1)>>1;
        if(pq[p][0]<=prio) break;
        pq[i]=pq[p]; i=p;
      }
      pq[i]=[prio,node];
    };
    pushP(0, inicio);
    const popP=()=>{
      const top=pq[0], last=pq.pop();
      if(pq.length){
        pq[0]=last; let i=0;
        for(;;){
          const l=2*i+1, r=l+1; let m=i;
          if(l<pq.length&&pq[l][0]<pq[m][0]) m=l;
          if(r<pq.length&&pq[r][0]<pq[m][0]) m=r;
          if(m===i) break;
          const tmp=pq[i]; pq[i]=pq[m]; pq[m]=tmp; i=m;
        }
      }
      return top;
    };
    while(pq.length){
      const cur=popP();
      const d=cur[0], u=cur[1];
      if(u===fim) break;
      if(d>dist[u]) continue;
      for(const ed of malha.adj[u]){
        let pen=1;
        const prof=ed.depth||5;
        if(prof<minProf) pen = 1 + Math.min((minProf-prof)*0.3, 2.5);
        if((ed.strahler||0)<6) pen += 0.35;
        const nd=d + ed.w*pen;
        if(nd<dist[ed.to]){
          dist[ed.to]=nd; prev[ed.to]=u;
          pushP(nd,ed.to);
        }
      }
    }
    if(!isFinite(dist[fim])) return null;
    const coords=[];
    let cur=fim;
    while(cur!==-1){ coords.push(malha.nodes[cur]); cur=prev[cur]; }
    coords.reverse();
    return coords;
  }

  // Gera GeoJSON da rota seguindo a malha hidrográfica real
  function gerarGeoJSONRota(origem, destino, km, trechos, calado) {
    // Coordenadas de referência (fallback se malha indisponível)
    const coords = {
      'MANAUS': [-60.0272, -3.1383],
      'JATUARANA': [-59.6478, -3.0633],
      'CAREIRO': [-59.8336, -3.1961],
      'ITACOATIARA': [-58.4114, -3.1539],
      'PARINTINS': [-56.7519, -2.6306],
      'PONTO 01': [-59.8, -3.1],
      'PONTO 02': [-59.5, -3.05],
      'PONTO 03': [-59.2, -3.15],
      'PONTO 04 (DESVIO)': [-59.0, -3.1],
      'PONTO 05': [-58.7, -3.12]
    };
    let lineCoords = null;
    try{
      if(window.HIDROVIAS_PROF && window.HIDROVIAS_PROF.features){
        const malha=construirMalha();
        const o=injetarPonto(malha, coords[origem]||coords['MANAUS']);
        const d=injetarPonto(malha, coords[destino]||coords['ITACOATIARA']);
        if(o!==null && d!==null){
          const path=dijkstraRio(malha, o, d, calado);
          if(path && path.length>=2) lineCoords=path;
        }
      }
    }catch(err){
      lineCoords=null;
    }
    if(!lineCoords){
      const path=[origem, ...trechos.slice(0,5).map(t=>t.destino), destino];
      const uniq=[...new Set(path)];
      lineCoords=uniq.map(p=>coords[p]||coords['MANAUS']);
    }
    return {
      type:'Feature',
      properties:{
        origem: origem,
        destino: destino,
        distance_km: km,
        tempo_h: null,
        seguranca_1_10: null
      },
      geometry:{ type:'LineString', coordinates: lineCoords }
    };
  }

  form.addEventListener('submit', async (e)=>{
    e.preventDefault();
    clearAllErr();
    let hasError = false;
    let firstInvalid = null;
    const origem=selO.value, destino=selD.value;
    const caladoRaw = caladoEl.value.trim();
    const calado=parseFloat(caladoRaw.replace(',','.'));
    const velRaw = velEl.value.trim();
    const vel=parseFloat(velRaw.replace(',','.'))||18;

    if(!origem){
      setErr('origem','Selecione a origem.');
      hasError=true; firstInvalid=firstInvalid||selO;
    }
    if(!destino){
      setErr('destino','Selecione o destino.');
      hasError=true; firstInvalid=firstInvalid||selD;
    }
    if(origem && destino && origem===destino){
      setErr('destino','Origem e destino não podem ser iguais. Escolha localidades diferentes.');
      hasError=true; firstInvalid=firstInvalid||selD;
    }
    if(caladoRaw==='' || isNaN(calado)){
      setErr('calado','Informe o calado, por exemplo 1,8.');
      hasError=true; firstInvalid=firstInvalid||caladoEl;
    } else if(calado < 0.5 || calado > 6){
      setErr('calado','Calado deve estar entre 0,5 e 6,0 metros.');
      hasError=true; firstInvalid=firstInvalid||caladoEl;
    }
    if(velRaw!=='' && (isNaN(vel) || vel < 6 || vel > 35)){
      setErr('velocidade','Velocidade deve estar entre 6 e 35 km/h.');
      hasError=true; firstInvalid=firstInvalid||velEl;
    }

    if(hasError){
      announce('Corrija os erros no formulário.', true);
      if(firstInvalid) firstInvalid.focus();
      return;
    }

    btnCalc.disabled=true;
    btnCalc.innerHTML='<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span> Calculando rota…';
    announce('Calculando rota de '+origem+' para '+destino+'. Aguarde.');
    try {
      const r=await obterRota(origem,destino,calado,vel);
      if (!r) return;
      document.getElementById('resTitulo').textContent = origem+' → '+destino;
      document.getElementById('resSub').textContent = r.km.toFixed(1).replace('.',',')+' km · via hidrovia principal';
      const badge = document.getElementById('resBadge');
      const rotuloNav = r.folga>=0.3?'Navegável': r.folga>= -0.4 ? 'Restrito':'Crítico';
      badge.textContent = rotuloNav;
      badge.className = 'badge rounded-pill '+(r.folga>=0.3?'text-bg-success': r.folga>=-0.4?'text-bg-warning':'text-bg-danger');
      document.getElementById('resTempo').textContent = r.tempo.toFixed(1).replace('.',',')+' h';
      document.getElementById('resTempoDet').textContent = 'a '+vel+' km/h · correnteza estimada 5,5 km/h';
      document.getElementById('resKm').textContent = r.km.toFixed(1).replace('.',',')+' km';
      document.getElementById('resCriticos').textContent = String(r.criticos);
      document.getElementById('resProfMin').textContent = r.profMin.toFixed(1).replace('.',',')+' m';
      renderSafety(r.nota);

      const lista=document.getElementById('listaTrechos');
      const caladoRef=calado;
      lista.innerHTML = (r.trechos||[]).slice(0,7).map(t=>{
        const ok = t.profundidadeM >= caladoRef+0.5;
        const warn = !ok && t.profundidadeM >= caladoRef+0.1;
        const cls = ok?'ok': warn?'warn':'bad';
        const badgeT = ok?'Transitável': warn?'Restrito':'Bloqueado';
        const bcls = ok?'text-bg-success': warn?'text-bg-warning':'text-bg-danger';
        return `<div class="hw-trecho ${cls}" role="listitem">
          <span class="hw-trecho-dot" aria-hidden="true"></span>
          <div class="flex-grow-1">
            <div class="fw-semibold" style="font-size:.88rem">${t.origem} → ${t.destino}</div>
            <div class="small text-secondary">${t.km} km · prof. ${t.profundidadeM.toFixed(1).replace('.',',')} m</div>
          </div>
          <span class="badge ${bcls}" aria-label="${badgeT}">${badgeT}</span>
        </div>`;
      }).join('');
      resSec.classList.remove('hw-hidden');
      resSec.classList.add('hw-fade');
      resSec.removeAttribute('hidden');
      alternarResultado(true);
      document.getElementById('alertCount').textContent = String(r.criticos || 0);
      resSec.dataset.origem=origem; resSec.dataset.destino=destino;
      resSec.dataset.km=r.km; resSec.dataset.tempo=r.tempo;
      resSec.dataset.seguranca=r.nota; resSec.dataset.calado=calado;
      // Envia rota para o mapa (GeoJSON)
      const geojson = r.geojson;
      if (!geojson) {
        announce('A API não retornou a geometria da rota.', true);
        return;
      }
      if (geojson.type === 'Feature') {
        geojson.properties = geojson.properties || {};
        geojson.properties.tempo_h = r.tempo;
        geojson.properties.seguranca_1_10 = r.nota;
      }
      if (window.YgapeMapa) {
        window.YgapeMapa.mostrarRota(geojson, origem, destino);
      }
      // Foco acessível: move para o título do resultado
      const tituloRes = document.getElementById('tituloResultado');
      tituloRes.setAttribute('tabindex','-1');
      tituloRes.focus();
      announce('Rota calculada: '+origem+' para '+destino+', '+r.km.toFixed(1).replace('.',',')+' quilômetros, tempo '+r.tempo.toFixed(1).replace('.',',')+' horas, segurança '+r.nota+' de 10, '+rotuloNav+'.');
      // Scroll apenas se prefers-reduced-motion não bloquear
      if(!window.matchMedia('(prefers-reduced-motion: reduce)').matches){
        resSec.scrollIntoView({behavior:'smooth', block:'start'});
      } else {
        resSec.scrollIntoView({block:'start'});
      }
    } finally {
      btnCalc.disabled=false;
      btnCalc.innerHTML='<i class="bi bi-signpost-2 me-2" aria-hidden="true"></i> Calcular rota mais eficiente';
    }
  });

  // Salvar rota
  const btnSalvar = document.getElementById('btnSalvar');
  btnSalvar.addEventListener('click',()=>{
    const sec=document.getElementById('resultado');
    if(sec.classList.contains('hw-hidden')){ announce('Calcule uma rota antes de salvar.', true); return; }
    const nova={
      id: Date.now(),
      origem: sec.dataset.origem, destino: sec.dataset.destino,
      caladoM: parseFloat(sec.dataset.calado), km: parseFloat(sec.dataset.km),
      data: new Date().toLocaleString('pt-BR',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'}),
      status: parseInt(sec.dataset.seguranca)>=6?'ok': parseInt(sec.dataset.seguranca)>=4?'alerta':'erro'
    };
    try{ localStorage.setItem('ygapé_ultima_rota', JSON.stringify(nova)); }catch(e){}
    rotasSalvas.unshift(nova);
    if(rotasSalvas.length>5) rotasSalvas.pop();
    renderHist();
    const toastEl=document.getElementById('toastSalvar');
    if(window.bootstrap) new bootstrap.Toast(toastEl,{delay:2600}).show();
    announce('Rota de '+nova.origem+' para '+nova.destino+' salva.');
    const old=btnSalvar.innerHTML; btnSalvar.innerHTML='<i class="bi bi-check-lg me-2" aria-hidden="true"></i> Rota salva!';
    btnSalvar.disabled=true;
    setTimeout(()=>{ btnSalvar.innerHTML=old; btnSalvar.disabled=false; btnSalvar.focus(); },1800);
  });

  renderSafety(7);
  // esconde resultado inicialmente para leitores de tela
  if(resSec.classList.contains('hw-hidden')) resSec.setAttribute('hidden','');
})();
