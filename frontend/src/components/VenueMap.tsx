import React, { useMemo } from "react";

// ── Strict Types ────────────────────────────────────────────────────────────

/** Real-time telemetry data for one venue node, received over SSE stream. */
export interface HeatmapNode {
  id: string;
  density: number;
  people: number;
  trend: string;
}

export const nodeCoords: Record<string, { x: number; y: number; label: string; iconType?: string }> = {
  entrance_north:       { x: 400, y: 50,  label: "North Gate",    iconType: "gate"    },
  entrance_south:       { x: 400, y: 550, label: "South Gate",    iconType: "gate"    },
  concourse_west:       { x: 180, y: 300, label: "West Concourse"                     },
  concourse_east:       { x: 620, y: 300, label: "East Concourse"                     },
  seating_section_a:    { x: 280, y: 160, label: "Sector A"                           },
  seating_section_b:    { x: 280, y: 440, label: "Sector B"                           },
  seating_section_c:    { x: 520, y: 160, label: "Sector C"                           },
  seating_section_d:    { x: 520, y: 440, label: "Sector D"                           },
  food_court_1:         { x: 80,  y: 200, label: "West Food",     iconType: "food"    },
  restroom_1:           { x: 80,  y: 400, label: "West Rest",     iconType: "restroom"},
  food_court_2:         { x: 720, y: 200, label: "East Food",     iconType: "food"    },
  restroom_2:           { x: 720, y: 400, label: "East Rest",     iconType: "restroom"},
  emergency_exit_west:  { x: 50,  y: 550, label: "West Exit",     iconType: "exit"    },
  emergency_exit_east:  { x: 750, y: 550, label: "East Exit",     iconType: "exit"    },
  trophy_room:          { x: 280, y: 70,  label: "Trophy Room",   iconType: "trophy"  },
  fan_zone:             { x: 520, y: 70,  label: "Fan Zone",      iconType: "fan"     },
  merch_store_1:        { x: 180, y: 200, label: "West Merch",    iconType: "merch"   },
  merch_store_2:        { x: 620, y: 200, label: "East Merch",    iconType: "merch"   },
};

const getIconPath = (type?: string): string => {
  switch (type) {
    case "food":    return "M2 13h20v2H2zM12 2C7 2 3 6 3 11h18c0-5-4-9-9-9zM4 17h16v-2H4v2zm2 2v2h12v-2H6z";
    case "trophy":  return "M6 2h12v5c0 3.3-2.7 6-6 6s-6-2.7-6-6V2zm2 2v3c0 2.2 1.8 4 4 4s4-1.8 4-4V4H8zm3 11v3H8v2h8v-2h-3v-3c2.8-.5 5-3 5-6v-1h2V6h-2V2H4v4H2v2h2v1c0 3 2.2 5.5 5 6z";
    case "restroom":return "M12 2a2 2 0 100 4 2 2 0 000-4zM9 8h6v7h-2v7h-2v-7H9V8z";
    case "gate":    return "M4 4h16v16H4zM2 2v20h20V2H2z M10 10h4v4h-4z";
    case "exit":    return "M14 5l7 7-7 7v-4H3v-6h11V5z";
    case "fan":     return "M12 2L9 9l-7 1 5 5-1 7 8-4 8 4-1-7 5-5-7-1-3-7z";
    case "merch":   return "M20 6h-4V4c0-1.11-.89-2-2-2h-4c-1.11 0-2 .89-2 2v2H4c-1.11 0-1.99.89-1.99 2L2 19c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V8c0-1.11-.89-2-2-2zm-6 0h-4V4h4v2z";
    default:        return "";
  }
};

const edges: [string, string][] = [
  ["entrance_north",    "concourse_west"],
  ["entrance_north",    "concourse_east"],
  ["entrance_south",    "concourse_west"],
  ["entrance_south",    "concourse_east"],
  ["concourse_west",    "food_court_1"],
  ["concourse_west",    "restroom_1"],
  ["concourse_west",    "seating_section_a"],
  ["concourse_west",    "seating_section_b"],
  ["concourse_west",    "emergency_exit_west"],
  ["concourse_west",    "trophy_room"],
  ["concourse_east",    "food_court_2"],
  ["concourse_east",    "restroom_2"],
  ["concourse_east",    "seating_section_c"],
  ["concourse_east",    "seating_section_d"],
  ["concourse_east",    "emergency_exit_east"],
  ["concourse_east",    "fan_zone"],
  ["trophy_room",       "seating_section_a"],
  ["fan_zone",          "seating_section_c"],
  ["concourse_west",    "merch_store_1"],
  ["concourse_east",    "merch_store_2"],
];

export const nodesList = Object.keys(nodeCoords);

// ── Component Props ─────────────────────────────────────────────────────────

interface VenueMapProps {
  view: "attendee" | "admin";
  heatmap: HeatmapNode[];
  startNode: string;
  endNode: string;
  recommendedPath: string[];
  emergency: boolean;
  weather: string;
  triggerCongestion: (node: string) => void;
}

// ── VenueMap Component ───────────────────────────────────────────────────────

export const VenueMap: React.FC<VenueMapProps> = React.memo(({
  view, heatmap, startNode, endNode, recommendedPath, emergency, weather, triggerCongestion,
}) => {

  /** Build a set of highlighted edge strings from the recommended path for O(1) lookup. */
  const pathEdgeSet = useMemo<Set<string>>(() => {
    const s = new Set<string>();
    for (let i = 0; i < recommendedPath.length - 1; i++) {
      s.add(`${recommendedPath[i]}-${recommendedPath[i + 1]}`);
      s.add(`${recommendedPath[i + 1]}-${recommendedPath[i]}`);
    }
    return s;
  }, [recommendedPath]);

  /** Index heatmap array into a Record for O(1) node lookup during rendering. */
  const nodeInsights = useMemo<Record<string, HeatmapNode>>(() => {
    const m: Record<string, HeatmapNode> = {};
    heatmap.forEach(h => { m[h.id] = h; });
    return m;
  }, [heatmap]);

  return (
    <div className="map-container animate-enter" style={{ marginBottom: "2rem" }}>
      <h2 style={{ fontSize: "1.4rem", margin: "0 0 1rem 0", color: "var(--text-primary)" }}>
        {view === "admin" ? "Venue Telemetry" : "Field View"}
      </h2>

      {weather === "rain" && (
        <div style={{
          position: "absolute", top: 24, right: 24,
          background: "rgba(0,0,0,0.8)", color: "white",
          padding: "6px 16px", borderRadius: "20px",
          fontSize: "0.85rem", fontWeight: 600
        }}>
          Active Weather Monitored
        </div>
      )}

      {/* Accessibility: SVG with full ARIA role, title, and desc for screen readers */}
      <svg
        viewBox="0 0 800 600"
        style={{ width: "100%", height: "auto", display: "block" }}
        role="application"
        aria-label="Interactive venue map showing current crowd congestion levels and calculated route."
      >
        <title>Live Venue Telemetry Map</title>
        <desc>Visualization of the stadium showing connection paths between sections, restrooms, and exits.</desc>

        <ellipse cx="400" cy="300" rx="360" ry="290" fill="#f8fafc" stroke="var(--border-light)" strokeWidth="2" />
        <ellipse cx="400" cy="300" rx="140" ry="240" fill="transparent" stroke="#e2e8f0" strokeWidth="2" strokeDasharray="6,6" className="stadium-ring" />

        {edges.map(([a, b], i) => {
          const p1 = nodeCoords[a];
          const p2 = nodeCoords[b];
          const isHighlighted = pathEdgeSet.has(`${a}-${b}`);
          const color = isHighlighted
            ? (emergency ? "var(--accent-red)" : "var(--accent-blue)")
            : "#e2e8f0";

          return (
            <line
              key={i}
              x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
              stroke={color}
              strokeWidth={isHighlighted ? 5 : 2}
              strokeLinecap="round"
              className={isHighlighted ? "path-line" : ""}
              pathLength="1"
              style={isHighlighted ? { filter: "drop-shadow(0 2px 6px rgba(59,130,246,0.3))" } : {}}
            />
          );
        })}

        {Object.entries(nodeCoords).map(([key, point]) => {
          const isStart = key === startNode && view === "attendee";
          const isEnd   = key === endNode   && view === "attendee";
          const inPath  = recommendedPath.includes(key);

          const insight = nodeInsights[key] ?? { density: 1.0, people: 0, trend: "Stable" };
          const density = insight.density;
          let nodeColor = "var(--accent-green)";
          if (density > 2.0)      nodeColor = "var(--accent-red)";
          else if (density > 1.4) nodeColor = "var(--accent-orange)";

          return (
            <g
              key={key}
              role="button"
              aria-pressed={inPath}
              aria-label={`${point.label}: ${insight.people.toLocaleString()} people, ${insight.trend}`}
              aria-live="polite"
              tabIndex={0}
              onMouseEnter={() => {}} // Accessibility hint
              onClick={() => { if (view === "admin") triggerCongestion(key); }}
              onKeyDown={(e) => { 
                if (e.key === "Enter") {
                  if (view === "admin") triggerCongestion(key);
                } 
              }}
              style={{ outline: "none" }}
            >
              {view === "admin" && (
                <circle cx={point.x} cy={point.y} r={16 + density * 6} fill={nodeColor} opacity="0.1">
                  <title>Node: {point.label}. People: {insight.people.toLocaleString()} | Trend: {insight.trend}</title>
                </circle>
              )}

              {point.iconType && (
                <g transform={`translate(${point.x - 10}, ${point.y - 30}) scale(0.8)`}>
                  <path d={getIconPath(point.iconType)} fill={inPath ? "var(--accent-blue)" : "var(--text-muted)"} />
                </g>
              )}

              {(isStart || isEnd) && view === "attendee" && (
                <circle
                  cx={point.x} cy={point.y} r="8"
                  fill={isStart ? "var(--accent-blue)" : "var(--accent-purple)"}
                  className="radar-ring"
                  style={{ transformOrigin: `${point.x}px ${point.y}px` }}
                />
              )}

              <circle
                cx={point.x} cy={point.y}
                r={inPath && view === "attendee" ? 8 : 6}
                fill={isStart || isEnd ? "var(--text-primary)" : "#ffffff"}
                stroke={inPath && view === "attendee"
                  ? (emergency ? "var(--accent-red)" : "var(--accent-blue)")
                  : "var(--border-light)"}
                strokeWidth={inPath ? "3" : "2"}
                style={{ transition: "all 0.2s", cursor: view === "admin" ? "pointer" : "default" }}
              >
                {view === "admin" && <title>Admin: Click to trigger load spike.</title>}
              </circle>

              {(isStart || isEnd) && (
                <g className="bounce-text">
                  <text x={point.x} y={point.y - 14} fill="var(--text-primary)" fontSize="12" fontWeight="800" textAnchor="middle">
                    {isStart ? "START" : "DESTINATION"}
                  </text>
                </g>
              )}
              <text x={point.x} y={point.y + 20} fill="var(--text-primary)" fontSize="12" textAnchor="middle" fontWeight="600">
                {point.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
});

VenueMap.displayName = "VenueMap";
