"use strict";
const source = document.querySelector('#chart-data');
if (source && window.Chart) {
  const charts = JSON.parse(source.dataset.charts);
  const money = value => new Intl.NumberFormat('en-ZM', {maximumFractionDigits: 2}).format(value);
  for (const [id, data] of Object.entries(charts)) {
    const canvas = document.getElementById(id);
    if (!canvas) continue;
    const bar = id === 'bars';
    new Chart(canvas, {type: bar ? 'bar' : 'line', data, options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: {mode: 'index', intersect: false},
      elements: {line: {tension: 0}, point: {radius: 2}},
      plugins: {legend: {position: 'bottom', labels: {boxWidth: 12}}, tooltip: {callbacks: {label: item => item.dataset.label + ': K ' + money(item.parsed.y)}}},
      scales: {x: {stacked: false, ticks: {maxRotation: 0, autoSkip: true, maxTicksLimit: 8}},
        y: {beginAtZero: true, ...(bar ? {min: 0} : {}), stacked: false, ticks: {callback: money}}}
    }});
  }
}
