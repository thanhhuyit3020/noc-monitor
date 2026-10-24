(() => {
  let chart = null;

  function draw(container, points, metric, unit) {
    if (!window.uPlot || !container) return;
    if (chart) chart.destroy();
    const rows = points.filter(row => row.metric_key === metric && row.value !== null);
    if (!rows.length) {
      container.innerHTML = '<div class="empty-chart">No history collected for this metric yet</div>';
      return;
    }
    const grouped = new Map();
    for (const row of rows) grouped.set(Math.floor(row.ts), Number(row.value));
    const data = [[...grouped.keys()], [...grouped.values()]];
    chart = new uPlot({
      width: Math.max(320, container.clientWidth),
      height: 210,
      scales: {x: {time: true}},
      axes: [{stroke: "#65758b", grid: {stroke: "rgba(130,151,177,.13)"}}, {stroke: "#65758b", grid: {stroke: "rgba(130,151,177,.13)"}, values: (_, vals) => vals.map(v => v.toFixed(1) + unit)}],
      series: [{}, {label: metric, stroke: "#56d5c1", width: 2, fill: "rgba(86,213,193,.12)"}],
      cursor: {drag: {x: false, y: false}},
      legend: {show: false}
    }, data, container);
  }

  window.NocCharts = {draw};
})();
