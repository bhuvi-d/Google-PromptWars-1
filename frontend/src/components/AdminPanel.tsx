import React from "react";

interface AdminPanelProps {
  massExodus: boolean;
  weather: string;
  toggleExodus: () => void;
  toggleWeather: () => void;
}

export const AdminPanel: React.FC<AdminPanelProps> = ({ massExodus, weather, toggleExodus, toggleWeather }) => {
  return (
    <>
      <button 
        onClick={toggleExodus} 
        className={`btn ${massExodus ? 'btn-danger' : ''}`}
        aria-pressed={massExodus}
        aria-label="Toggle Venue Evacuation Protocol"
      >
        {massExodus ? "Clear Evacuation Protocol" : "Trigger Venue Evacuation"}
      </button>
      <button 
        onClick={toggleWeather} 
        className="btn"
        aria-pressed={weather === "rain"}
        aria-label="Toggle Storm Simulator"
      >
        {weather === "rain" ? "Simulate Clear Weather" : "Simulate Storm Protocol"}
      </button>
    </>
  );
};
