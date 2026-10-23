import * as go from "gojs";

const COLORS = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f", "#edc948", "#b07aa1", "#9c755f"];
const R = 100;  // outer radius
const r = 60;   // inner radius (the hole)

function sliceGeometry(start: number, sweep: number): go.Geometry {
  const rad = (a: number) => (a * Math.PI) / 180;
  const pt = (a: number, rr: number) => [R + rr * Math.cos(rad(a)), R + rr * Math.sin(rad(a))];
  const [x0, y0] = pt(start, R);
  const [x1, y1] = pt(start + sweep, r);
  const fig = new go.PathFigure(x0, y0, true);
  fig.add(new go.PathSegment(go.SegmentType.Arc, start, sweep, R, R, R, R));      // outer arc
  fig.add(new go.PathSegment(go.SegmentType.Line, x1, y1));                      // to inner edge
  fig.add(new go.PathSegment(go.SegmentType.Arc, start + sweep, -sweep, R, R, r, r).close()); // inner arc back
  return new go.Geometry().add(fig);
}

function buildSlices(pair: [string[], number[]]) {
  const [labels, minutes] = pair;
  const items = labels
    .map((label, i) => ({ label, minutes: minutes[i] }))
    .filter((d) => d.minutes > 0);                       // drops an empty "Other"
  const total = items.reduce((s, d) => s + d.minutes, 0);
  let angle = -90;                                       // start at 12 o'clock
  return items.map((d, i) => {
    const sweep = Math.min((d.minutes / total) * 360, 359.99);
    const slice = {
      geo: sliceGeometry(angle, sweep),
      color: COLORS[i % COLORS.length],
      legend: `${d.label}: ${(d.minutes / 60).toFixed(1)} h (${Math.round((d.minutes / total) * 100)}%)`,
    };
    angle += sweep;
    return slice;
  });
}

export function drawDonut(divId: string, pair: [string[], number[]]): go.Diagram {
  const diagram = new go.Diagram(divId, {
    isReadOnly: true,
    allowSelect: false,
    contentAlignment: go.Spot.Center,
    "animationManager.isEnabled": false,
  });

  diagram.nodeTemplate = new go.Node("Vertical", { selectable: false })
    .add(
      new go.Panel("Position", {
        itemTemplate: new go.Panel("Position").add(
          new go.Shape({ strokeWidth: 2, stroke: "white" })
            .bind("geometry", "geo")
            .bind("fill", "color")
        ),
      }).bind("itemArray", "slices"),
      new go.Panel("Vertical", {
        margin: new go.Margin(12, 0, 0, 0),
        defaultAlignment: go.Spot.Left,
        itemTemplate: new go.Panel("Horizontal").add(
          new go.Shape("Rectangle", { width: 10, height: 10, strokeWidth: 0, margin: new go.Margin(2, 6, 2, 0) })
            .bind("fill", "color"),
          new go.TextBlock({ font: "12px Outfit, sans-serif" }).bind("text", "legend")
        ),
      }).bind("itemArray", "slices")
    );

  diagram.model = new go.Model({ nodeDataArray: [{ key: 1, slices: buildSlices(pair) }] });
  return diagram;
}