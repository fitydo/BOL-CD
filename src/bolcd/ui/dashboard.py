from __future__ import annotations

from fastapi import APIRouter, Response

router = APIRouter()


@router.get("/dashboard")
def dashboard() -> Response:
    # Simple D3 force graph that fetches /api/graph and renders nodes/edges
    html = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>BOL‑CD Dashboard</title>
  <style>
    body { font-family: sans-serif; margin: 0; }
    #toolbar { padding: 8px 12px; background: #f5f5f5; border-bottom: 1px solid #ddd; }
    #chart { width: 100vw; height: calc(100vh - 46px); }
    .node { stroke: #fff; stroke-width: 1.5px; }
    .link { stroke: #999; stroke-opacity: 0.6; }
    .label { font-size: 10px; pointer-events: none; }
  </style>
  <script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
  <script>
    async function render() {
      const res = await fetch('/api/graph');
      const graph = await res.json();
      const nodes = (graph.nodes || []).map(id => ({ id }));
      const links = (graph.edges || []).map(e => ({ source: e.src, target: e.dst, segment: e.segment || '__all__' }));

      const color = d3.scaleOrdinal(d3.schemeTableau10);

      const width = document.getElementById('chart').clientWidth;
      const height = document.getElementById('chart').clientHeight;

      const svg = d3.select('#chart').append('svg')
        .attr('viewBox', [0, 0, width, height])
        .call(d3.zoom().on('zoom', (event) => {
          g.attr('transform', event.transform);
        }));

      const g = svg.append('g');

      const simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(50))
        .force('charge', d3.forceManyBody().strength(-100))
        .force('center', d3.forceCenter(width / 2, height / 2));

      const link = g.append('g')
        .attr('stroke', '#999')
        .attr('stroke-opacity', 0.6)
        .selectAll('line')
        .data(links)
        .join('line')
        .attr('class', 'link')
        .attr('stroke', d => color(d.segment))
        .attr('marker-end', 'url(#arrow)');

      // Arrow marker
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

      const node = g.append('g')
        .attr('stroke', '#fff')
        .attr('stroke-width', 1.5)
        .selectAll('circle')
        .data(nodes)
        .join('circle')
        .attr('r', 5)
        .attr('fill', '#4285f4')
        .call(d3.drag()
          .on('start', dragstarted)
          .on('drag', dragged)
          .on('end', dragended));

      const label = g.append('g')
        .selectAll('text')
        .data(nodes)
        .join('text')
        .attr('class', 'label')
        .attr('dx', 8)
        .attr('dy', '0.35em')
        .text(d => d.id);

      simulation.on('tick', () => {
        link
          .attr('x1', d => d.source.x)
          .attr('y1', d => d.source.y)
          .attr('x2', d => d.target.x)
          .attr('y2', d => d.target.y);
        node
          .attr('cx', d => d.x)
          .attr('cy', d => d.y);
        label
          .attr('x', d => d.x)
          .attr('y', d => d.y);
      });

      function dragstarted(event) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
      }
      function dragged(event) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
      }
      function dragended(event) {
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
      }
    }
    window.addEventListener('load', render);
  </script>
</head>
<body>
  <div id="toolbar">
    <strong>BOL‑CD Dashboard</strong>
    &nbsp;|&nbsp; <a href="/api/graph">/api/graph</a>
    &nbsp;|&nbsp; <a href="/metrics">/metrics</a>
    &nbsp;|&nbsp; <a href="/api/audit">/api/audit</a>
  </div>
  <div id="chart"></div>
</body>
</html>
    """
    return Response(content=html, media_type="text/html")

