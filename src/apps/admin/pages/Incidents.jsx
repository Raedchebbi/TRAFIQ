import React, { useEffect, useState, useCallback } from 'react';
import { useTrafik } from '../../../shared/context/TrafikContext';
import IncidentCard from '../components/IncidentCard';
import './Incidents.css';

const API_BASE = 'http://localhost:5000';

const LEVEL_CONFIG = {
    0: { label: 'FREE',     color: '#00c853' },
    1: { label: 'MODERATE', color: '#ffab00' },
    2: { label: 'HEAVY',    color: '#ff6d00' },
    3: { label: 'SEVERE',   color: '#d50000' },
};

function formatDuration(seconds) {
    if (!seconds || seconds === 0) return '—';
    if (seconds < 60) return `${seconds}s`;
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}m ${s}s`;
}

function CongestionIncidentRow({ incident, onResolve }) {
    const cfg = LEVEL_CONFIG[incident.level] || LEVEL_CONFIG[2];
    return (
        <div className={`ci-row ${incident.resolved ? 'resolved' : 'active'}`}>
            <div className="ci-row-left">
                <span className="ci-dot" style={{ background: cfg.color }} />
                <div className="ci-row-info">
                    <span className="ci-row-id">{incident.id}</span>
                    <span className="ci-row-label" style={{ color: cfg.color }}>
                        {incident.label}
                    </span>
                </div>
            </div>

            <div className="ci-row-stats">
                <div className="ci-stat">
                    <span className="ci-stat-val">{incident.vehicle_count}</span>
                    <span className="ci-stat-key">véhicules</span>
                </div>
                <div className="ci-stat">
                    <span className="ci-stat-val">{incident.slow_ratio}%</span>
                    <span className="ci-stat-key">lents</span>
                </div>
                <div className="ci-stat">
                    <span className="ci-stat-val">{incident.avg_speed}</span>
                    <span className="ci-stat-key">px/s moy</span>
                </div>
                <div className="ci-stat">
                    <span className="ci-stat-val">{formatDuration(incident.duration_seconds)}</span>
                    <span className="ci-stat-key">durée</span>
                </div>
            </div>

            <div className="ci-row-right">
                <span className="ci-timestamp">{incident.timestamp}</span>
                {incident.resolved ? (
                    <span className="ci-badge-resolved">✓ Résolu {incident.resolved_at}</span>
                ) : (
                    <button
                        className="adm-btn-primary ci-resolve-btn"
                        onClick={() => onResolve(incident.id)}
                    >
                        Résoudre
                    </button>
                )}
            </div>
        </div>
    );
}

export default function Incidents() {
    const { accidentsGPS } = useTrafik();
    const activeAccidents = accidentsGPS.filter(a => a.active);
    const resolvedAccidents = accidentsGPS.filter(a => !a.active);

    // Congestion incidents from API
    const [congestionIncidents, setCongestionIncidents] = useState([]);
    const [incidentStats, setIncidentStats] = useState(null);
    const [apiConnected, setApiConnected] = useState(false);
    const [filter, setFilter] = useState('all');   // all | active | resolved
    const [levelFilter, setLevelFilter] = useState('all');
    const [search, setSearch] = useState('');

    const fetchIncidents = useCallback(async () => {
        try {
            const [incRes, statsRes] = await Promise.all([
                fetch(`${API_BASE}/api/incidents`),
                fetch(`${API_BASE}/api/incidents/stats`),
            ]);
            setCongestionIncidents(await incRes.json());
            setIncidentStats(await statsRes.json());
            setApiConnected(true);
        } catch {
            setApiConnected(false);
        }
    }, []);

    useEffect(() => {
        fetchIncidents();
        const interval = setInterval(fetchIncidents, 5000);
        return () => clearInterval(interval);
    }, [fetchIncidents]);

    const handleResolve = async (id) => {
        try {
            await fetch(`${API_BASE}/api/incidents/${id}/resolve`, { method: 'POST' });
            fetchIncidents();
        } catch (e) {
            console.error('Resolve failed', e);
        }
    };

    const handleExport = () => {
        const blob = new Blob([JSON.stringify(congestionIncidents, null, 2)],
            { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `incidents_${new Date().toISOString().slice(0, 10)}.json`;
        a.click();
    };

    // Filter congestion incidents
    const filtered = congestionIncidents.filter(inc => {
        if (filter === 'active' && inc.resolved) return false;
        if (filter === 'resolved' && !inc.resolved) return false;
        if (levelFilter !== 'all' && inc.level !== parseInt(levelFilter)) return false;
        if (search && !inc.id.toLowerCase().includes(search.toLowerCase()) &&
            !inc.label.toLowerCase().includes(search.toLowerCase())) return false;
        return true;
    });

    const activeCount = accidentsGPS.filter(a => a.active).length +
        congestionIncidents.filter(i => !i.resolved).length;

    return (
        <div className="adm-incidents-page">

            {/* ── Header ── */}
            <div className="adm-incidents-header">
                <div className="adm-incidents-title">
                    <h2>Gestion des Incidents</h2>
                    <div className="adm-incidents-summary">
                        <span className="adm-badge-red">{activeCount} actifs</span>
                        <span className="adm-badge-gray">
                            {incidentStats?.resolved ?? resolvedAccidents.length} résolus
                        </span>
                        {apiConnected
                            ? <span className="ci-api-badge ok">● API connectée</span>
                            : <span className="ci-api-badge err">○ API déconnectée</span>}
                    </div>
                </div>
                <div className="adm-incidents-filters">
                    <input
                        type="text"
                        placeholder="Rechercher par ID ou label..."
                        className="adm-input-search"
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                    />
                    <select
                        className="adm-select-filter"
                        value={levelFilter}
                        onChange={e => setLevelFilter(e.target.value)}
                    >
                        <option value="all">Tous les niveaux</option>
                        <option value="1">Modéré (1)</option>
                        <option value="2">Lourd (2)</option>
                        <option value="3">Sévère (3)</option>
                    </select>
                    <select
                        className="adm-select-filter"
                        value={filter}
                        onChange={e => setFilter(e.target.value)}
                    >
                        <option value="all">Tous</option>
                        <option value="active">Actifs</option>
                        <option value="resolved">Résolus</option>
                    </select>
                    <button className="adm-btn-primary" onClick={handleExport}>
                        Exporter JSON
                    </button>
                </div>
            </div>

            {/* ── Stats Bar (from API) ── */}
            {incidentStats && (
                <div className="ci-stats-bar">
                    <div className="ci-stats-box">
                        <span className="ci-stats-val">{incidentStats.total}</span>
                        <span className="ci-stats-key">Total congestions</span>
                    </div>
                    <div className="ci-stats-box active">
                        <span className="ci-stats-val">{incidentStats.active}</span>
                        <span className="ci-stats-key">En cours</span>
                    </div>
                    <div className="ci-stats-box resolved">
                        <span className="ci-stats-val">{incidentStats.resolved}</span>
                        <span className="ci-stats-key">Résolus</span>
                    </div>
                    <div className="ci-stats-box severe">
                        <span className="ci-stats-val">{incidentStats.severe}</span>
                        <span className="ci-stats-key">Sévères</span>
                    </div>
                    <div className="ci-stats-box">
                        <span className="ci-stats-val">
                            {formatDuration(incidentStats.avg_duration_seconds)}
                        </span>
                        <span className="ci-stats-key">Durée moy.</span>
                    </div>
                </div>
            )}

            <div className="adm-incidents-list">

                {/* ── Congestion Incidents (from Python API) ── */}
                <div className="ci-section-header">
                    <h3>Incidents de Congestion · Détection IA</h3>
                    <span className="adm-badge-blue">{filtered.length} entrées</span>
                </div>

                {!apiConnected ? (
                    <div className="ci-no-api">
                        <p>⚠️ Backend Python non connecté</p>
                        <code>python api.py</code>
                    </div>
                ) : filtered.length === 0 ? (
                    <div className="ci-empty">
                        Aucun incident de congestion enregistré pour le moment.
                    </div>
                ) : (
                    <div className="ci-list">
                        {filtered.map(inc => (
                            <CongestionIncidentRow
                                key={inc.id}
                                incident={inc}
                                onResolve={handleResolve}
                            />
                        ))}
                    </div>
                )}

                {/* ── Accident Incidents (existing mock data) ── */}
                <div className="ci-section-header adm-mt-32">
                    <h3>Incidents Accidents · Actifs</h3>
                    <span className="adm-badge-red">{activeAccidents.length} actifs</span>
                </div>
                <div className="adm-incidents-grid">
                    {activeAccidents.map(acc => (
                        <IncidentCard key={acc.id} incident={acc} />
                    ))}
                </div>

                <div className="ci-section-header adm-mt-32">
                    <h3>Historique Accidents · Résolus</h3>
                    <span className="adm-badge-gray">{resolvedAccidents.length} archivés</span>
                </div>
                <div className="adm-incidents-grid archived">
                    {resolvedAccidents.map(acc => (
                        <IncidentCard key={acc.id} incident={acc} />
                    ))}
                </div>
            </div>
        </div>
    );
}