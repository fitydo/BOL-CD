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
  </style>
  <script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
  <script>
    let svg, g, simulation, color, width, height, allLinks = [], allNodes = [];

    function setupSvg() {
      width = document.getElementById('chart').clientWidth;
      height = document.getElementById('chart').clientHeight;
      d3.select('#chart').selectAll('*').remove();
      svg = d3.select('#chart').append('svg')
        .attr('viewBox', [0, 0, width, height])
        .call(d3.zoom().on('zoom', (event) => g.attr('transform', event.transform)));
      g = svg.append('g');
      svg.append('defs').append('marker')
        .attr('id', 'arrow')
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 15)
        .attr('refY', 0)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', '#999');
    }

    function updateLegend(links) {
      const segs = Array.from(new Set(links.map(e => e.segment)));
      const legend = d3.select('#legend');
      legend.selectAll('*').remove();
      segs.forEach(seg => {
        const id = `seg_${seg}`;
        const wrap = legend.append('label');
        wrap.append('input').attr('type','checkbox').attr('id', id).property('checked', true)
          .on('change', () => drawGraph());
        wrap.append('span').text(` ${seg}`);
      });
    }

    function allowedSegments() {
      const checks = document.querySelectorAll('#legend input[type=checkbox]');
      const active = new Set();
      checks.forEach(ch => { if (ch.checked) active.add(ch.nextSibling.textContent.trim()); });
      return active;
    }

    async function loadGraph() {
      const res = await fetch('/api/graph');
      const graph = await res.json();
      allNodes = (graph.nodes || []).map(id => ({ id }));
      allLinks = (graph.edges || []).map(e => ({ source: e.src, target: e.dst, segment: e.segment || '__all__' }));
      updateLegend(allLinks);
      drawGraph();
    }

    function drawGraph() {
      setupSvg();
      color = d3.scaleOrdinal(d3.schemeTableau10);
      const activeSegs = allowedSegments();
      const links = allLinks.filter(l => activeSegs.has(l.segment));
      const nodes = allNodes;

      simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(60))
        .force('charge', d3.forceManyBody().strength(-120))
        .force('center', d3.forceCenter(width / 2, height / 2));

      const link = g.append('g').attr('stroke', '#999').attr('stroke-opacity', 0.6)
        .selectAll('line').data(links).join('line').attr('class','link')
        .attr('stroke', d => color(d.segment)).attr('marker-end','url(#arrow)');

      const node = g.append('g').attr('stroke','#fff').attr('stroke-width',1.5)
        .selectAll('circle').data(nodes).join('circle').attr('r',5).attr('fill','#4285f4')
        .call(d3.drag().on('start',dragstarted).on('drag',dragged).on('end',dragended));

      const label = g.append('g').selectAll('text').data(nodes).join('text')
        .attr('class','label').attr('dx',8).attr('dy','0.35em').text(d=>d.id);

      simulation.on('tick', () => {
        link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
        node.attr('cx', d => d.x).attr('cy', d => d.y);
        label.attr('x', d => d.x).attr('y', d => d.y);
      });

      function dragstarted(event){ if(!event.active) simulation.alphaTarget(0.3).restart(); event.subject.fx=event.subject.x; event.subject.fy=event.subject.y; }
      function dragged(event){ event.subject.fx=event.x; event.subject.fy=event.y; }
      function dragended(event){ if(!event.active) simulation.alphaTarget(0); event.subject.fx=null; event.subject.fy=null; }
    }

    async function runRecompute() {
      const key = document.getElementById('apikey').value.trim();
      const fdrq = parseFloat(document.getElementById('fdrq').value);
      const eps = parseFloat(document.getElementById('epsilon').value);
      if (key) localStorage.setItem('bolcd_apikey', key);
      const res = await fetch('/api/edges/recompute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': key || '' },
        body: JSON.stringify({ fdr_q: fdrq, epsilon: eps })
      });
      if (!res.ok) { alert('Recompute failed: ' + res.status); return; }
      await loadGraph();
    }

    function init() {
      const saved = localStorage.getItem('bolcd_apikey');
      if (saved) document.getElementById('apikey').value = saved;
      loadGraph();
    }
    window.addEventListener('load', init);
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
    <a href="/api/audit">/api/audit</a>
    <span>|</span>
    <label>API Key (operator): <input id="apikey" type="text" size="20" placeholder="testop"/></label>
    <label>fdr_q: <input id="fdrq" type="number" step="0.001" value="0.01"/></label>
    <label>epsilon: <input id="epsilon" type="number" step="0.001" value="0.005"/></label>
    <button class="btn" onclick="runRecompute()">Run recompute</button>
    <div id="legend"></div>
  </div>
  <div id="chart"></div>
</body>
</html>
    """
    return Response(content=html, media_type="text/html")

