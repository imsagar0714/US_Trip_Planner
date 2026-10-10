import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import { ArrowRight, Clock3, Fuel, MapPin, Navigation, RefreshCw, ShieldCheck, Truck, Utensils, Moon } from "lucide-react";
import "./styles.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000/api";
const initial = { current_location: "Dallas, TX", pickup_location: "Houston, TX", dropoff_location: "Atlanta, GA", current_cycle_used: "20" };

function RouteMap({ data }) {
  const points = data?.points || [];
  const all = data?.geometry?.length ? data.geometry : points;
  if (!all.length) return <div className="empty-map"><Navigation size={30} /><span>Your route will appear here</span></div>;
  const lats = all.map(p => p.lat), lngs = all.map(p => p.lng);
  const minLat = Math.min(...lats), maxLat = Math.max(...lats), minLng = Math.min(...lngs), maxLng = Math.max(...lngs);
  const project = p => ({
    x: 12 + ((p.lng - minLng) / (maxLng - minLng || 1)) * 76,
    y: 86 - ((p.lat - minLat) / (maxLat - minLat || 1)) * 68,
  });
  return <div className="map-canvas">
    <div className="map-grid" />
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="route-line" aria-label="Planned route"><polyline points={all.map(p => { const point = project(p); return `${point.x},${point.y}`; }).join(" ")} /></svg>
    {points.map((p, i) => { const point = project(p); return <div key={p.label} className={`map-pin pin-${i}`} style={{ left: `${point.x}%`, top: `${point.y}%` }}><span>{i === 0 ? "●" : i === 1 ? "▣" : "◆"}</span><label>{p.label}</label></div>; })}
    {data.stops.filter(s => s.type === "fuel").map((s, i) => <div key={s.label} className="map-stop" style={{ left: `${31 + i * 21}%`, top: `${39 + i * 10}%` }}><Fuel size={13} /></div>)}
    <div className="map-legend"><span><i className="legend-route" /> planned route</span><span><i className="legend-fuel" /> fuel</span></div>
  </div>;
}

function LogSheet({ log }) {
  const colors = { driving: "#16a394", sleeper: "#334155", off_duty: "#94a3b8", on_duty: "#f0a33b" };
  const labels = { off_duty: "Off duty", sleeper: "Sleeper berth", driving: "Driving", on_duty: "On duty" };
  return <div className="log-sheet">
    <div className="log-head"><div><b>DRIVER'S DAILY LOG</b><small>{log.date} · Day {log.day}</small></div><span>Property-carrying · 70 hr / 8 day</span></div>
    <div className="log-grid"><div className="log-labels">{Object.keys(labels).map(k => <div key={k}><i style={{ background: colors[k] }} />{labels[k]}</div>)}</div><div className="timeline">{[0,6,12,18,24].map(t => <span key={t} style={{ left: `${(t / 24) * 100}%` }}>{t === 24 ? "24" : `${t}`}</span>)}{Object.entries(labels).map(([status]) => <div className="track" key={status}>{log.segments.filter(s => s.status === status).map((s, i) => <div key={i} className="bar" title={s.label || labels[status]} style={{ left: `${(s.start % 24) / 24 * 100}%`, width: `${Math.max(0.8, (s.end - s.start) / 24 * 100)}%`, background: colors[status] }} />)}</div>)}</div></div>
    <div className="log-footer"><span>Remarks: {log.segments.filter(s => s.label).map(s => s.label).join(" · ") || "No exceptions recorded"}</span><strong>Total: {Math.round(log.segments.reduce((n, s) => n + s.end - s.start, 0) * 10) / 10} hrs</strong></div>
  </div>;
}

function App() {
  const [form, setForm] = useState(initial);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const update = e => setForm({ ...form, [e.target.name]: e.target.value });
  async function submit(e) {
    e.preventDefault(); setLoading(true); setError("");
    try {
      const response = await fetch(`${API}/trip-plan/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(form) });
      const result = await response.json(); if (!response.ok) throw new Error(result.error || "Unable to plan this trip.");
      setData(result);
    } catch (err) { setError(err.message); } finally { setLoading(false); }
  }
  return <div className="app"><header><div className="brand"><div className="brand-mark"><Truck size={20} /></div><div><b>SPOTTER</b><small>Trip intelligence for drivers</small></div></div><div className="header-status"><span className="status-dot" /> HOS rules active <ShieldCheck size={16} /></div></header>
    <main><section className="hero"><div><p className="eyebrow">DRIVER WORKSPACE · HOS PLANNER</p><h1>Move smarter.<br /><em>Arrive ready.</em></h1><p className="hero-copy">Plan a compliant trip with clear driving windows, fuel stops, and printable daily logs in seconds.</p></div><div className="hero-badge"><Clock3 size={20} /><span><strong>70 / 8</strong><small>cycle limit</small></span></div></section>
    <section className="planner-card"><div className="card-intro"><div><h2>Plan a new trip</h2><p>Tell us where you are headed and we’ll map the safest schedule.</p></div><span className="required">All fields required</span></div><form onSubmit={submit}><div className="location-row">{[["current_location","Current location","Where are you now?"],["pickup_location","Pickup location","First stop"],["dropoff_location","Drop-off location","Final destination"]].map(([name,label,placeholder], i) => <label className="field" key={name}><span>{label}</span><div className="input-wrap"><MapPin size={16} /><input aria-label={label} name={name} value={form[name]} onChange={update} placeholder={placeholder} autoComplete="off" required />{i < 2 && <ArrowRight size={15} className="field-arrow" />}</div></label>)}</div><div className="action-row"><label className="field cycle-field"><span>Current cycle used <small>hours</small></span><div className="input-wrap"><Clock3 size={16} /><input aria-label="Current cycle used hours" type="number" min="0" max="70" step="0.5" name="current_cycle_used" value={form.current_cycle_used} onChange={update} required /></div></label><button type="submit" disabled={loading}>{loading ? <><RefreshCw className="spin" size={17} /> Planning route...</> : <><Navigation size={17} /> Plan my trip</>}</button></div></form>{error && <div className="error" role="alert">{error}</div>}</section>
    {data && <><section className="summary-row"><div className="summary-card accent"><span>ROUTE DISTANCE</span><strong>{data.summary.distanceMiles.toLocaleString()} <small>mi</small></strong><p><MapPin size={13} /> {data.summary.routingProvider} route</p></div><div className="summary-card"><span>DRIVING TIME</span><strong>{data.summary.drivingHours} <small>hrs</small></strong><p><Clock3 size={13} /> excludes rest periods</p></div><div className="summary-card"><span>TRIP LENGTH</span><strong>{data.summary.days} <small>{data.summary.days === 1 ? "day" : "days"}</small></strong><p><Moon size={13} /> compliant schedule</p></div><div className="summary-card"><span>CYCLE REMAINING</span><strong>{data.summary.cycleRemaining} <small>hrs</small></strong><p><ShieldCheck size={13} /> after this trip</p></div></section>
    <section className="dashboard-grid"><div className="panel map-panel"><div className="panel-heading"><div><p className="eyebrow">ROUTE OVERVIEW</p><h2>Your planned route</h2></div><span className="pill"><span className="status-dot" /> Compliant</span></div><RouteMap data={data} /></div><div className="panel stops-panel"><div className="panel-heading"><div><p className="eyebrow">MILESTONES</p><h2>Trip stops</h2></div><span className="stop-count">{data.stops.length} planned</span></div><div className="stops-list"><div className="stop-item"><span className="stop-icon origin"><MapPin size={15} /></span><div><b>{data.points[0].label}</b><small>Start · now</small></div></div>{data.stops.map((stop, i) => <div className="stop-item" key={`${stop.label}-${i}`}><span className={`stop-icon ${stop.type}`} >{stop.type === "fuel" ? <Fuel size={15} /> : stop.type === "break" ? <Utensils size={15} /> : <Moon size={15} />}</span><div><b>{stop.label}</b><small>{stop.time} · {stop.type === "fuel" ? "Fuel planned" : "Required rest"}</small></div></div>)}<div className="stop-item"><span className="stop-icon destination"><MapPin size={15} /></span><div><b>{data.points[2].label}</b><small>Drop-off · final destination</small></div></div></div></div></section>
    <section className="logs-section"><div className="section-heading"><div><p className="eyebrow">ELD COMPLIANCE LOGS</p><h2>Daily driver's logs</h2><p>Generated from the FMCSA 11-hour driving, 14-hour window, and 30-minute break rules.</p></div><button className="secondary" onClick={() => window.print()}>Print logs</button></div>{data.dailyLogs.map(log => <LogSheet key={log.day} log={log} />)}</section></>}
    </main><footer><span>SPOTTER / TRIP PLANNER</span><span>Built for safer miles · HOS assumptions shown above</span></footer></div>;
}

createRoot(document.getElementById("root")).render(<App />);
