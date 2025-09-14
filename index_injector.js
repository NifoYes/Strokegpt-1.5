/* index_injector.js — style *...* segments without touching your layout */
(function(){
  function formatNarrativeSegments(text){
    try{
      if (typeof text !== "string") return text;
      if (text.indexOf('action-asterisk') !== -1) return text;
      // Keep asterisks visible; to HIDE them use '<span class="action-asterisk">$1</span>'
      return text.replace(/\*([^*]+)\*/g, '<span class="action-asterisk">*$1*</span>');
    }catch(e){ return text; }
  }
  window.formatNarrativeSegments = formatNarrativeSegments;

  // Inject CSS
  try{
    var style = document.createElement('style');
    style.textContent = '.action-asterisk{font-style:italic;color:#bfc7d5;}';
    document.head.appendChild(style);
  }catch(e){}

  // Observe DOM for message bubbles and post-process them
  try{
    var mo = new MutationObserver(function(muts){
      for (var i=0;i<muts.length;i++){
        var m = muts[i];
        if (!m.addedNodes) continue;
        for (var j=0;j<m.addedNodes.length;j++){
          var node = m.addedNodes[j];
          if (!node || node.nodeType !== 1) continue;
          var targets = node.matches && node.matches('.msg, .message, .bubble, .assistant, .user, [data-role="message"]') ? [node] : [];
          var q = node.querySelectorAll ? node.querySelectorAll('.msg, .message, .bubble, .assistant, .user, [data-role="message"]') : [];
          for (var k=0;k<q.length;k++) targets.push(q[k]);
          for (var t=0;t<targets.length;t++){
            var el = targets[t];
            if (el.getAttribute && el.getAttribute('data-asterisk-processed') === '1') continue;
            try {
              el.innerHTML = formatNarrativeSegments(el.innerHTML);
              el.setAttribute('data-asterisk-processed','1');
            } catch(e) {}
          }
        }
      }
    });
    mo.observe(document.documentElement || document.body, {childList:true, subtree:true});
  }catch(e){}
})();