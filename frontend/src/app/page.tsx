"use client";

import { useState, useEffect, useCallback } from "react";
import "./globals.css";
import { VenueMap, nodeCoords, HeatmapNode } from "../components/VenueMap";
import { RouteConfigPanel } from "../components/RouteConfigPanel";
import { AdminPanel } from "../components/AdminPanel";

// ── Strict Type Definitions ────────────────────────────────────────────────

/** Telemetry payload received via the SSE /api/stats/stream endpoint. */
interface TelemetryPayload {
  attendance: number;
  mass_exodus: boolean;
  heatmap: HeatmapNode[];
}

/** Full response shape returned by POST /api/route. */
interface RouteResponse {
  recommended_route: string[];
  estimated_time: string;
  estimated_distance: string;
  confidence_score: number;
  crowd_impact: string;
  reasoning: string;
  departure_time?: string;
  target_relocated?: string;
}

const API_BASE = "https://venue-api-915854891523.us-central1.run.app";
const ADMIN_TOKEN = "Bearer mock-admin-token-123";

// ── Main Page ──────────────────────────────────────────────────────────────

export default function Home() {
  const [view, setView] = useState<"attendee" | "admin">("attendee");

  // Telemetry state — populated by SSE stream
  const [heatmap, setHeatmap]       = useState<HeatmapNode[]>([]);
  const [attendance, setAttendance] = useState<number>(0);
  const [massExodus, setMassExodus] = useState<boolean>(false);

  // Route configuration state
  const [startNode, setStartNode]         = useState<string>("entrance_north");
  const [endNode, setEndNode]             = useState<string>("seating_section_a");
  const [emergency, setEmergency]         = useState<boolean>(false);
  const [accessible, setAccessible]       = useState<boolean>(false);
  const [scenic, setScenic]               = useState<boolean>(false);
  const [smartRestroom, setSmartRestroom] = useState<boolean>(false);
  const [weather, setWeather]             = useState<string>("clear");

  // UI state
  const [routeResult, setRouteResult]       = useState<RouteResponse | null>(null);
  const [loading, setLoading]               = useState<boolean>(false);
  const [showHighlights, setShowHighlights] = useState<boolean>(false);

  // ── SSE Stream: Real-Time Telemetry ───────────────────────────────────────
  // Replaces polling. Reconnects automatically on drop with a 5s backoff.

  useEffect(() => {
    let eventSource: EventSource | null = null;

    const connectTelemetry = () => {
      eventSource = new EventSource(`${API_BASE}/api/stats/stream`);

      eventSource.onmessage = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data) as TelemetryPayload;
          setHeatmap(data.heatmap);
          setAttendance(data.attendance);
          setMassExodus(data.mass_exodus);
        } catch {
          // Silently ignore malformed SSE frames
        }
      };

      eventSource.onerror = () => {
        eventSource?.close();
        setTimeout(connectTelemetry, 5000);
      };
    };

    connectTelemetry();
    return () => { eventSource?.close(); };
  }, []);

  // ── Route Calculation ─────────────────────────────────────────────────────

  const calculateRoute = useCallback(async (endNodeOverride?: string) => {
    setLoading(true);
    setRouteResult(null);
    try {
      const finalEndNode = typeof endNodeOverride === "string" ? endNodeOverride : endNode;
      const res = await fetch(`${API_BASE}/api/route`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          start_node:     startNode,
          end_node:       finalEndNode,
          emergency_mode: emergency,
          accessible_mode: accessible,
          scenic_mode:    scenic,
          smart_restroom: smartRestroom,
        }),
      });
      if (!res.ok) throw new Error("Impossible path given constraints");
      const data = await res.json() as RouteResponse;
      setRouteResult(data);
    } catch {
      alert("System connection error or impossible constraints selected.");
    } finally {
      setLoading(false);
    }
  }, [startNode, endNode, emergency, accessible, scenic, smartRestroom]);

  const syncFoodOrder      = useCallback(() => { setEmergency(false); calculateRoute("food_court_1");  }, [calculateRoute]);
  const promoteMerchandise = useCallback(() => { setEmergency(false); calculateRoute("closest_merch"); }, [calculateRoute]);

  // ── Admin Actions ─────────────────────────────────────────────────────────

  const adminHeaders = { Authorization: ADMIN_TOKEN };

  const triggerCongestion = useCallback(async (node: string) => {
    try {
      await fetch(`${API_BASE}/api/admin/trigger-congestion?node=${node}&severity=3.0`, {
        method: "POST", headers: adminHeaders,
      });
    } catch { /* non-critical */ }
  }, []);

  const toggleWeather = useCallback(async () => {
    const nextStr = weather === "clear" ? "rain" : "clear";
    try {
      await fetch(`${API_BASE}/api/admin/weather?state_val=${nextStr}`, {
        method: "POST", headers: adminHeaders,
      });
      setWeather(nextStr);
    } catch { /* non-critical */ }
  }, [weather]);

  const toggleExodus = useCallback(async () => {
    const nextStr = massExodus ? "inactive" : "active";
    try {
      await fetch(`${API_BASE}/api/admin/exodus?state_val=${nextStr}`, {
        method: "POST", headers: adminHeaders,
      });
    } catch { /* non-critical */ }
  }, [massExodus]);

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <>
      <div className="mesh-bg"></div>
      <main className="container" id="main-content">

        <header className="header animate-enter">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", width: "100%", flexWrap: "wrap", gap: "24px" }}>
            <div style={{ maxWidth: "600px" }}>
              <h1 style={{ fontSize: "2.4rem", letterSpacing: "-0.04em", margin: 0, fontWeight: 800 }}>
                Hope you are enjoying the match!
              </h1>
              <p style={{ color: "var(--text-secondary)", fontSize: "1.1rem", fontWeight: 500, marginTop: "8px" }}>
                Scroll below to view field telemetry or configure custom routing to see precise distance and time estimates.
              </p>
            </div>

            <div className="stat-panel" style={{ alignSelf: "center" }} aria-live="polite" aria-atomic="true">
              <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: "var(--accent-green)" }}>
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                <circle cx="9" cy="7" r="4"></circle>
                <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
              </svg>
              <span style={{ fontSize: "1.1rem", fontWeight: 700 }}>
                {attendance.toLocaleString()}{" "}
                <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)", fontWeight: 500 }}>Active Attendees</span>
              </span>
            </div>
          </div>

          <div style={{ display: "flex", gap: "10px", marginTop: "2rem", width: "100%", alignItems: "center" }}>
            {view === "attendee" && (
              <button
                id="live-highlights-btn"
                onClick={() => setShowHighlights(true)}
                className="btn hover-hop"
                style={{ background: "var(--text-primary)", color: "white", borderRadius: "9999px", padding: "10px 24px", display: "flex", gap: "12px", alignItems: "center", border: "none" }}
                aria-haspopup="dialog"
              >
                <div className="pulse-dot"></div>
                <span style={{ fontWeight: 600, letterSpacing: "0.05em" }}>LIVE HIGHLIGHTS</span>
              </button>
            )}
            {view === "admin" && (
              <AdminPanel massExodus={massExodus} weather={weather} toggleExodus={toggleExodus} toggleWeather={toggleWeather} />
            )}
            <button
              id="toggle-view-btn"
              className="btn"
              style={{ marginLeft: view === "admin" ? "auto" : "0" }}
              onClick={() => { setView(view === "attendee" ? "admin" : "attendee"); setRouteResult(null); }}
              aria-pressed={view === "admin"}
            >
              {view === "attendee" ? "Access Administrator Portal" : "Return to Attendee Portal"}
            </button>
          </div>
        </header>

        <VenueMap
          view={view}
          heatmap={heatmap}
          startNode={startNode}
          endNode={endNode}
          recommendedPath={routeResult?.recommended_route ?? []}
          emergency={emergency}
          weather={weather}
          triggerCongestion={triggerCongestion}
        />

        {view === "attendee" && (
          <RouteConfigPanel
            startNode={startNode}     setStartNode={setStartNode}
            endNode={endNode}         setEndNode={setEndNode}
            accessible={accessible}   setAccessible={setAccessible}
            scenic={scenic}           setScenic={setScenic}
            smartRestroom={smartRestroom} setSmartRestroom={setSmartRestroom}
            emergency={emergency}     setEmergency={setEmergency}
            syncFoodOrder={syncFoodOrder}
            promoteMerchandise={promoteMerchandise}
            calculateRoute={calculateRoute}
            loading={loading}
          />
        )}

        {/* Accessibility: aria-live assertive region for screen reader route announcements */}
        <div aria-live="assertive" aria-atomic="true" id="route-output">
          {routeResult && (
            <div className="animate-enter" style={{ marginTop: "3rem", paddingBottom: "3rem", paddingTop: "2.5rem", borderTop: "1px solid var(--border-light)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "2rem", flexWrap: "wrap", gap: "24px" }}>
                <div>
                  <h3 style={{ fontSize: "1.1rem", color: "var(--text-secondary)", fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase" }}>
                    {massExodus ? "Facility Evacuation" : emergency ? "Nearest Exit Route" : "Your Route Summary"}
                  </h3>
                  <div style={{ display: "flex", gap: "32px", alignItems: "baseline", marginTop: "12px", flexWrap: "wrap" }}>
                    <div>
                      <div style={{ fontSize: "3rem", fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.04em" }}>{routeResult.estimated_time}</div>
                      <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)", fontWeight: 600, textTransform: "uppercase" }}>Estimated Walk Time</div>
                    </div>
                    <div>
                      <div style={{ fontSize: "2rem", fontWeight: 700, color: "var(--accent-blue)" }}>{routeResult.estimated_distance}</div>
                      <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)", fontWeight: 600, textTransform: "uppercase" }}>Distance</div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="timeline-container">
                {routeResult.recommended_route.length > 1 ? (
                  routeResult.recommended_route.map((node: string, idx: number) => (
                    <div key={idx} style={{ display: "contents" }}>
                      <div className="timeline-node">
                        {nodeCoords[node]?.label ?? node}
                      </div>
                      {idx < routeResult.recommended_route.length - 1 && (
                        <span className="timeline-arrow" aria-hidden="true">➔</span>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="timeline-node" style={{ color: "var(--accent-red)", borderColor: "var(--accent-red)", background: "rgba(239,68,68,0.05)" }}>
                    {nodeCoords[routeResult.recommended_route[0]]?.label ?? routeResult.recommended_route[0]}: Optimal Destination Reached
                  </div>
                )}
              </div>

              {routeResult.target_relocated && (
                <div style={{ background: "rgba(59,130,246,0.05)", border: "1px solid var(--border-light)", borderLeft: "4px solid var(--accent-blue)", padding: "20px", borderRadius: "12px", marginTop: "2rem" }}>
                  <h4 style={{ fontSize: "1rem" }}>Route Updated Automatically</h4>
                  <p style={{ margin: 0, fontSize: "0.95rem", color: "var(--text-secondary)", marginTop: "4px" }}>{routeResult.target_relocated}</p>
                </div>
              )}

              {routeResult.departure_time && (
                <div style={{ background: "rgba(245,158,11,0.05)", border: "1px solid var(--border-light)", borderLeft: "4px solid var(--accent-orange)", padding: "20px", borderRadius: "12px", marginTop: "2rem" }}>
                  <h4 style={{ fontSize: "1rem" }}>Beat the Queue Tip</h4>
                  <p style={{ margin: 0, fontSize: "0.95rem", color: "var(--text-secondary)", marginTop: "4px" }}>{routeResult.departure_time}</p>
                </div>
              )}

              <div style={{ marginTop: "2rem", padding: "24px", background: "#f8fafc", borderRadius: "16px", border: "1px solid var(--border-light)" }}>
                <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: "8px", fontWeight: "600", textTransform: "uppercase", letterSpacing: "0.05em" }}>Why this way?</p>
                <p style={{ fontSize: "1rem", color: "var(--text-primary)", margin: 0, fontWeight: 500, lineHeight: 1.6, marginTop: "8px" }}>{routeResult.reasoning}</p>
              </div>
            </div>
          )}
        </div>

        {showHighlights && (
          <div
            style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(0,0,0,0.5)", zIndex: 100 }}
            role="dialog" aria-modal="true" aria-label="Live Highlights Stream"
          >
            <div className="modal-glass animate-enter" style={{ width: "90%", maxWidth: "800px", padding: "16px", display: "flex", flexDirection: "column" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: "16px", borderBottom: "1px solid rgba(255,255,255,0.1)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <div className="pulse-dot"></div>
                  <h3 style={{ margin: 0, color: "white", letterSpacing: "1px" }}>FIELD CAM 4 - HIGHLIGHTS</h3>
                </div>
                <button
                  id="close-highlights-btn"
                  style={{ background: "transparent", border: "none", color: "white", cursor: "pointer", fontSize: "1.5rem" }}
                  onClick={() => setShowHighlights(false)}
                  aria-label="Close highlights"
                >×</button>
              </div>
              <div style={{ background: "rgba(0,0,0,0.6)", width: "100%", height: "400px", borderRadius: "8px", marginTop: "16px", display: "flex", alignItems: "center", justifyContent: "center", position: "relative", overflow: "hidden" }}>
                <div style={{ position: "absolute", inset: 0, opacity: 0.15, backgroundImage: "repeating-linear-gradient(0deg, transparent, transparent 2px, #fff 2px, #fff 4px)" }}></div>
                <div style={{ display: "flex", gap: "4px", alignItems: "flex-end", height: "40px" }}>
                  {[1,2,3,4,5,6,7,8,9,10].map(i => <div key={i} className="eq-bar" style={{ animationDelay: `${i * 0.1}s` }}></div>)}
                </div>
                <div style={{ position: "absolute", bottom: "16px", left: "16px", right: "16px" }}>
                  <div style={{ height: "4px", background: "rgba(255,255,255,0.2)", borderRadius: "2px", width: "100%" }}>
                    <div style={{ width: "35%", height: "100%", background: "var(--accent-red)", borderRadius: "2px", transition: "width 1s linear" }}></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

      </main>
    </>
  );
}
