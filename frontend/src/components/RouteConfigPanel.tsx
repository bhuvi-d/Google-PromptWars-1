import React from "react";
import { nodesList, nodeCoords } from "./VenueMap";

interface RouteConfigPanelProps {
  startNode: string;
  setStartNode: (v: string) => void;
  endNode: string;
  setEndNode: (v: string) => void;
  accessible: boolean;
  setAccessible: (v: boolean) => void;
  scenic: boolean;
  setScenic: (v: boolean) => void;
  smartRestroom: boolean;
  setSmartRestroom: (v: boolean) => void;
  emergency: boolean;
  setEmergency: (v: boolean) => void;
  syncFoodOrder: () => void;
  promoteMerchandise: () => void;
  calculateRoute: () => void;
  loading: boolean;
}

export const RouteConfigPanel: React.FC<RouteConfigPanelProps> = (props) => {
  return (
    <div className="ultra-panel animate-enter" style={{ animationDelay: "0.1s" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "2rem", flexWrap: "wrap", gap: "16px" }}>
         <h2 style={{ fontSize: "1.5rem", margin: 0 }}>Configure Your Route</h2>
         <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }} role="group" aria-label="Quick Actions">
           <button className="btn hover-hop" onClick={props.syncFoodOrder} style={{ color: "#d97706", borderColor: "#fef3c7", background: "#fffbeb" }} aria-label="Synchronize Food Order to Route">
             <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ transition: "all 0.3s" }}><path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2"></path><path d="M7 2v20"></path><path d="M21 15V2v0a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3Zm0 0v7"></path></svg>
             Synchronize Food Order
           </button>
           <button className="btn hover-hop" onClick={props.promoteMerchandise} style={{ color: "var(--accent-purple)", borderColor: "#f3e8ff", background: "#faf5ff" }} aria-label="Find closest merchandise store">
             <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ transition: "all 0.3s" }}><path d="M20 6h-4V4c0-1.11-.89-2-2-2h-4c-1.11 0-2 .89-2 2v2H4c-1.11 0-1.99.89-1.99 2L2 19c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V8c0-1.11-.89-2-2-2zm-6 0h-4V4h4v2z"></path></svg>
             Buy Official Merch
           </button>
         </div>
      </div>
      
      <div className="grid" style={{ marginBottom: "2.5rem", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
        <div className="input-group">
          <label htmlFor="start-location" className="input-label">Current Node</label>
          <select id="start-location" className="custom-select" value={props.startNode} onChange={e => props.setStartNode(e.target.value)}>
            {nodesList.map(n => <option key={n} value={n}>{nodeCoords[n].label}</option>)}
          </select>
        </div>
        <div className="input-group">
          <label htmlFor="end-location" className="input-label">Destination Node</label>
          <select id="end-location" className="custom-select" value={props.endNode} onChange={e => props.setEndNode(e.target.value)}>
            {nodesList.map(n => <option key={n} value={n}>{nodeCoords[n].label}</option>)}
          </select>
        </div>
      </div>

      <div className="grid" style={{ marginBottom: "2.5rem", gap: "16px", display: "grid", gridTemplateColumns: "1fr 1fr" }} role="group" aria-label="Route Optimization Constraints">
         <label className="toggle-wrapper" title="Avoid all stairs smoothly">
            <input type="checkbox" checked={props.accessible} onChange={e => props.setAccessible(e.target.checked)} aria-checked={props.accessible} />
            <div className="toggle-switch"></div>
            <span className="toggle-label">Avoid Stairs</span>
         </label>
         <label className="toggle-wrapper" title="Walk past attractions like the Trophy Room">
            <input type="checkbox" checked={props.scenic} onChange={e => props.setScenic(e.target.checked)} aria-checked={props.scenic} />
            <div className="toggle-switch"></div>
            <span className="toggle-label">Pass by Attractions</span>
         </label>
         <label className="toggle-wrapper" title="Automatically finds the restroom with the shortest lines">
            <input type="checkbox" checked={props.smartRestroom} onChange={e => props.setSmartRestroom(e.target.checked)} aria-checked={props.smartRestroom} />
            <div className="toggle-switch"></div>
            <span className="toggle-label">Find Fastest Restroom</span>
         </label>
         <label className="toggle-wrapper" style={{ border: props.emergency ? "1px solid var(--accent-red)" : "" }}>
            <input type="checkbox" className="emergency-toggle" checked={props.emergency} onChange={e => props.setEmergency(e.target.checked)} aria-checked={props.emergency} />
            <div className="toggle-switch"></div>
            <span className="toggle-label" style={{ color: props.emergency ? "var(--accent-red)" : "inherit", fontWeight: props.emergency ? 700 : 500 }}>Find Nearest Exit</span>
         </label>
      </div>
      
      <button 
        className={`btn ${props.emergency ? 'btn-danger' : 'btn-primary'}`} 
        style={{ width: "100%", padding: "18px", fontSize: "1.2rem", justifyContent: "center", transition: "all 0.2s" }} 
        onClick={props.calculateRoute} 
        disabled={props.loading}
        aria-busy={props.loading}
      >
        {props.loading ? (
           <span style={{ display: "flex", gap: "8px", alignItems: "center" }}>
              <div className="pulse-dot" style={{ background: "white", boxShadow: "0 0 0 0 rgba(255,255,255,0.7)" }}></div>
              Calculating Optimum Telemetry...
           </span>
        ) : (
           "Generate Optimal Route Estimates"
        )}
      </button>
    </div>
  );
};
