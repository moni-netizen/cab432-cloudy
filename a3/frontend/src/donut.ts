import { Chart, DoughnutController, ArcElement, Tooltip, Legend } from "chart.js";

Chart.register(DoughnutController, ArcElement, Tooltip, Legend);

const COLORS = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f", "#edc948", "#b07aa1", "#9c755f"];

export function drawDonut(canvasId: string, pair: [string[], number[]]): Chart | null {
  const canvas = document.getElementById(canvasId) as HTMLCanvasElement | null;
  if (!canvas) return null;

  Chart.getChart(canvas)?.destroy();          // avoids "canvas already in use" on redraw

  const [labels, minutes] = pair;
  const items = labels
    .map((label, i) => ({ label, hours: +(minutes[i] / 60).toFixed(1) }))
    .filter((d) => d.hours > 0);              // drops an empty "Other"

  return new Chart(canvas, {
    type: "doughnut",
    data: {
      labels: items.map((d) => d.label),
      datasets: [{
        data: items.map((d) => d.hours),
        backgroundColor: COLORS,
        borderColor: "#fff",
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "60%",                           // size of the hole
      plugins: {
        legend: { position: "bottom", labels: { font: { family: "Outfit" } } },
        tooltip: { callbacks: { label: (c) => ` ${c.label}: ${c.parsed} h` } },
      },
    },
  });
}