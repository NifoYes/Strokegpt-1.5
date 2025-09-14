
(function(){
  if (window.__sgpt_clean_v1) return; window.__sgpt_clean_v1 = true;

  function onceStyle(id, css){
    if(document.getElementById(id)) return;
    const s = document.createElement('style'); s.id = id; s.textContent = css; document.head.appendChild(s);
  }

  // ===== CSS (only layout) =====
  onceStyle('sgpt-clean-css', `
    /* Reply Length segmented control in 3 columns */
    #reply-length-section .sgpt-segmented{
      display:grid; grid-template-columns:repeat(3,1fr); gap:8px; width:100%;
    }
    #reply-length-section .sgpt-segmented label{
      display:flex; align-items:center; justify-content:center; gap:8px;
      background:rgba(255,255,255,.06); border-radius:10px; padding:8px 10px;
    }
    #reply-length-section .sgpt-segmented input[type="radio"]{ margin:0; }

    /* Audio card scoped tweaks */
    .sgpt-audio-card .setting-body{ overflow:hidden; }
    .sgpt-audio-card .sgpt-audio-buttons{ display:grid; grid-template-columns:repeat(2,1fr); gap:8px; margin-bottom:8px; }
    .sgpt-audio-card .sgpt-audio-buttons .my-button{ width:100%; }
    .sgpt-audio-card #aud-vol{ display:block; width:100%; max-width:100%; margin:6px 0; }
    .sgpt-audio-card #aud-reload{ float:right; margin-top:6px; }
    .sgpt-audio-card .setting-body::after{ content:''; display:block; clear:both; }
    .sgpt-audio-card #aud-loop, .sgpt-audio-card #aud-shuf, .sgpt-audio-card #aud-rand{ margin-right:10px; }
    .sgpt-audio-card small, .sgpt-audio-card span{ word-break:break-word; }
  `);

  function norm(t){ return (t||'').replace(/\s+/g,' ').trim().toLowerCase(); }

  // Remove only slideshow panels
  function removeSlides(){
    document.querySelectorAll('.setting-section h3').forEach(h3=>{
      const t = norm(h3.textContent);
      if (t.includes('slideshow')){
        const sec = h3.closest('.setting-section');
        if (sec) sec.remove();
      }
    });
  }

  function findPersonaSection(){
    const h3s = document.querySelectorAll('.setting-section h3');
    for (const h3 of h3s){
      if (/persona/i.test(h3.textContent)) return h3.closest('.setting-section');
    }
    return null;
  }

  function ensureSkeletons(){
    if (!document.getElementById('ai-model-section')){
      const sec = document.createElement('div');
      sec.className = 'setting-section'; sec.id = 'ai-model-section';
      sec.innerHTML = `
        <h3>AI Model</h3>
        <div class="setting-body">
          <label class="input-label">Engine</label>
          <select id="ai-engine-select" class="select-box">
            <option value="current">Current (Hermes 7B)</option>
            <option value="ollama">Ollama</option>
            <option value="openai">OpenAI-compatible</option>
            <option value="custom">Custom…</option>
          </select>
          <div id="ai-adv" style="display:none;margin-top:8px;">
            <input id="ai-model-id" class="input-text" placeholder="Model ID (e.g. llama3:8b, nous-hermes…)">
            <input id="ai-endpoint-url" class="input-text" placeholder="Endpoint URL (optional)">
          </div>
          <button id="ai-apply" class="my-button" style="margin-top:10px">Apply</button>
          <small style="opacity:.7;display:block;margin-top:6px">Skeleton only — backend wiring later.</small>
        </div>`;
      const persona = findPersonaSection();
      if (persona) persona.after(sec);
    }

    if (!document.getElementById('reply-length-section')){
      const sec = document.createElement('div');
      sec.className = 'setting-section'; sec.id = 'reply-length-section';
      sec.innerHTML = `
        <h3>Reply Length</h3>
        <div class="setting-body">
          <div class="sgpt-segmented" id="reply-length-group">
            <label><input type="radio" name="replyLen" value="short"> Short</label>
            <label><input type="radio" name="replyLen" value="medium" checked> Medium</label>
            <label><input type="radio" name="replyLen" value="long"> Long</label>
          </div>
        </div>`;
      const anchor = document.getElementById('ai-model-section') || findPersonaSection();
      if (anchor) anchor.after(sec);
    }

    // Wire minimal localStorage behavior (unchanged)
    const engineSel = document.getElementById('ai-engine-select');
    const adv = document.getElementById('ai-adv');
    const modelId = document.getElementById('ai-model-id');
    const endpoint = document.getElementById('ai-endpoint-url');
    const apply = document.getElementById('ai-apply');
    const lenGroup = document.getElementById('reply-length-group');
    if (engineSel && adv){
      try {
        const saved = JSON.parse(localStorage.getItem('sgpt.ai.model')||'{}');
        if (saved.engine) engineSel.value = saved.engine;
        if (saved.modelId) modelId.value = saved.modelId;
        if (saved.endpoint) endpoint.value = saved.endpoint;
        adv.style.display = (engineSel.value==='openai'||engineSel.value==='custom') ? 'block':'none';
      } catch(e){}
      engineSel.addEventListener('change', ()=>{
        adv.style.display = (engineSel.value==='openai'||engineSel.value==='custom') ? 'block':'none';
      });
      apply && apply.addEventListener('click', ()=>{
        const payload = {engine: engineSel.value, modelId: (modelId?.value||'').trim(), endpoint: (endpoint?.value||'').trim()};
        localStorage.setItem('sgpt.ai.model', JSON.stringify(payload));
        console.log('[SGPT] AI model saved', payload);
      });
    }
    if (lenGroup){
      try {
        const savedLen = localStorage.getItem('sgpt.reply.length') || 'medium';
        const input = lenGroup.querySelector(`input[value="${savedLen}"]`);
        if (input) input.checked = true;
      } catch(e){}
      lenGroup.addEventListener('change', (e)=>{
        if (e.target && e.target.name==='replyLen'){
          localStorage.setItem('sgpt.reply.length', e.target.value);
          console.log('[SGPT] reply length saved', e.target.value);
        }
      });
    }
  }

  function markAudioCard(){
    document.querySelectorAll('.setting-section h3').forEach(h3=>{
      if (norm(h3.textContent).includes('audio (pip locale)')){
        const sec = h3.closest('.setting-section');
        if (!sec) return;
        sec.classList.add('sgpt-audio-card');
        // Find lowest common ancestor of the 4 buttons within this section
        const ids = ['aud-prev','aud-play','aud-pause','aud-next'];
        const nodes = ids.map(id=>sec.querySelector('#'+id)).filter(Boolean);
        if (nodes.length===4){
          function ancestors(el){
            const arr=[]; while(el && el!==sec){ arr.push(el); el=el.parentElement; } return arr;
          }
          const A = nodes.map(ancestors);
          // intersect
          let lca = null;
          const set = new Set(A[0]);
          for(const cand of set){
            if (A.every(list => list.includes(cand))){ lca = cand; break; }
          }
          (lca||sec).classList.add('sgpt-audio-buttons');
        }
      }
    });
  }

  document.addEventListener('DOMContentLoaded', ()=>{
    removeSlides();
    ensureSkeletons();
    markAudioCard(); // purely CSS-driven
  });
})();
