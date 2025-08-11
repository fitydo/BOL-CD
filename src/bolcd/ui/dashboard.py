from __future__ import annotations

from fastapi import APIRouter, Response

router = APIRouter()


@router.get("/dashboard")
def dashboard() -> Response:
    # Simple D3 force graph + controls (recompute, segment filters)
    html = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>BOL‑CD Dashboard</title>
  <style>
    body { font-family: sans-serif; margin: 0; }
    #toolbar { padding: 8px 12px; background: #f5f5f5; border-bottom: 1px solid #ddd; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
    #legend { display: inline-flex; gap: 8px; align-items: center; margin-left: 10px; }
    #legend label { font-size: 12px; }
    #chart { width: 100vw; height: calc(100vh - 46px); }
    .node { stroke: #fff; stroke-width: 1.5px; }
    .link { stroke: #999; stroke-opacity: 0.6; }
    .label { font-size: 10px; pointer-events: none; }
    .btn { padding: 4px 8px; font-size: 12px; }
    input[type="text"], input[type="number"] { padding: 2px 4px; font-size: 12px; }
    #audit { padding: 8px 12px; background: #fafafa; border-top: 1px solid #eee; max-height: 30vh; overflow: auto; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; font-size: 12px; }
  </style>
  <script>
    (function(){
      var SVGNS = 'http://www.w3.org/2000/svg';
      function byId(id){ return document.getElementById(id); }

      function render(graph){
        var chart = byId('chart');
        while (chart.firstChild) chart.removeChild(chart.firstChild);
        var w = chart.clientWidth || 900;
        var h = chart.clientHeight || 520;
        var svg = document.createElementNS(SVGNS, 'svg');
        svg.setAttribute('width', w);
        svg.setAttribute('height', h);
        svg.setAttribute('viewBox', '0 0 '+w+' '+h);
        chart.appendChild(svg);

        var defs = document.createElementNS(SVGNS, 'defs');
        var m = document.createElementNS(SVGNS, 'marker');
        m.setAttribute('id','arrow'); m.setAttribute('viewBox','0 -5 10 10');
        m.setAttribute('refX','12'); m.setAttribute('refY','0');
        m.setAttribute('markerWidth','6'); m.setAttribute('markerHeight','6'); m.setAttribute('orient','auto');
        var p = document.createElementNS(SVGNS, 'path'); p.setAttribute('d','M0,-5L10,0L0,5'); p.setAttribute('fill','#888');
        m.appendChild(p); defs.appendChild(m); svg.appendChild(defs);

        var nodes = (graph.nodes || []).slice();
        var edges = (graph.edges || []).slice();
        var pos = {};
        var n = nodes.length;
        for (var i=0;i<n;i++){
          var x = 120 + i * Math.max(150, Math.min(240, Math.floor(w/(n+1))));
          var y = Math.floor(h/2);
          pos[nodes[i]] = {x:x,y:y};
        }

        for (var j=0;j<edges.length;j++){
          var e = edges[j], s = pos[e.src], t = pos[e.dst];
          if (!s || !t) continue;
          var line = document.createElementNS(SVGNS, 'line');
          line.setAttribute('x1', s.x); line.setAttribute('y1', s.y);
          line.setAttribute('x2', t.x); line.setAttribute('y2', t.y);
          line.setAttribute('stroke', '#888'); line.setAttribute('stroke-width','2');
          line.setAttribute('marker-end','url(#arrow)'); svg.appendChild(line);
        }
        for (var k=0;k<n;k++){
          var c = document.createElementNS(SVGNS, 'circle');
          c.setAttribute('cx', pos[nodes[k]].x); c.setAttribute('cy', pos[nodes[k]].y);
          c.setAttribute('r','7'); c.setAttribute('fill','#4285f4'); svg.appendChild(c);
          var t = document.createElementNS(SVGNS, 'text'); t.setAttribute('x', pos[nodes[k]].x + 10);
          t.setAttribute('y', pos[nodes[k]].y + 4); t.setAttribute('font-size','12'); t.textContent = nodes[k]; svg.appendChild(t);
        }
      }

      function loadGraph(){ fetch('/api/graph').then(function(r){ return r.json(); }).then(render); }
      window.runRecompute = function(){
        var key = byId('apikey').value.trim();
        var fdrq = parseFloat(byId('fdrq').value);
        var eps = parseFloat(byId('epsilon').value);
        if (key) localStorage.setItem('bolcd_apikey', key);
        fetch('/api/edges/recompute', { method:'POST', headers:{'Content-Type':'application/json','X-API-Key': key || ''}, body: JSON.stringify({fdr_q:fdrq, epsilon:eps}) })
          .then(function(r){ if(!r.ok){ alert('Recompute failed: '+r.status); return; } loadGraph(); });
      };
      window.showAudit = function(){
        var v = byId('viewkey').value.trim();
        var op = byId('apikey').value.trim();
        if (v) localStorage.setItem('bolcd_viewkey', v);
        var key = v || op;
        fetch('/api/audit', { headers: { 'X-API-Key': key || '' }})
          .then(function(r){ if(!r.ok){ byId('audit').textContent = 'Audit fetch failed: '+r.status; return null; } return r.json(); })
          .then(function(data){ if(!data) return; var lines = data.map(function(e){ var ts=e.ts||''; var actor=e.actor||''; var action=e.action||''; var edges=(e.diff&&e.diff.edges!=null)?e.diff.edges:''; var nodes=(e.diff&&e.diff.nodes!=null)?e.diff.nodes:''; return ts+' | '+actor+' | '+action+' | edges='+edges+' nodes='+nodes;}); byId('audit').textContent = lines.join('\n'); });
      };
      function init(){ var saved=localStorage.getItem('bolcd_apikey'); if(saved) byId('apikey').value=saved; loadGraph(); }
      window.addEventListener('DOMContentLoaded', init);
    })();
  </script>
</head>
<body>
  <div id="toolbar">
    <strong>BOL‑CD Dashboard</strong>
    <span>|</span>
    <a href="/api/graph">/api/graph</a>
    <span>|</span>
    <a href="/metrics">/metrics</a>
    <span>|</span>
    <a href="#" onclick="showAudit(); return false;">/api/audit</a>
    <span>|</span>
    <label>API Key (operator): <input id="apikey" type="text" size="20" placeholder="testop"/></label>
    <label>API Key (viewer): <input id="viewkey" type="text" size="14" placeholder="view"/></label>
    <label>fdr_q: <input id="fdrq" type="number" step="0.001" value="0.01"/></label>
    <label>epsilon: <input id="epsilon" type="number" step="0.001" value="0.005"/></label>
    <button class="btn" onclick="runRecompute()">Run recompute</button>
    <div id="legend"></div>
  </div>
  <div id="chart"></div>
  <pre id="audit"></pre>
</body>
</html>
    """
    return Response(
        content=html,
        media_type="text/html",
        headers={
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
        },
    )

