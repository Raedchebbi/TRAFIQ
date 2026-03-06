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
    return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

// ── Lightbox ──────────────────────────────────────────────────
function SnapshotLightbox({ incident, onClose }) {
    useEffect(() => {
        const handler = (e) => { if (e.key === 'Escape') onClose(); };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, [onClose]);

    return (
        <div className="ci-lightbox-overlay" onClick={onClose}>
            <div className="ci-lightbox-box" onClick={e => e.stopPropagation()}>
                <div className="ci-lightbox-header">
                    <div>
                        <span className="ci-lightbox-id">{incident.id}</span>
                        <span className="ci-lightbox-label"
                              style={{ color: LEVEL_CONFIG[incident.level]?.color }}>
                            {incident.label}
                        </span>
                    </div>
                    <div className="ci-lightbox-actions">
                        <a
                            href={`${API_BASE}/api/snapshots/${incident.id}/download`}
                            download={`${incident.id}.jpg`}
                            className="adm-btn-primary ci-dl-btn"
                        >
                            📥 Télécharger
                        </a>
                        <button className="ci-lightbox-close" onClick={onClose}>✕</button>
                    </div>
                </div>
                <img
                    src={`${API_BASE}${incident.snapshot}`}
                    alt={incident.id}
                    className="ci-lightbox-img"
                />
                <div className="ci-lightbox-meta">
                    <span>🕐 {incident.timestamp}</span>
                    <span>🚗 {incident.vehicle_count} véhicules</span>
                    <span>🐢 {incident.slow_ratio}% lents</span>
                    <span>⚡ {incident.avg_speed} px/s</span>
                    <span>⏱ Durée: {formatDuration(incident.duration_seconds)}</span>
                </div>
            </div>
        </div>
    );
}

// ── Congestion Row ────────────────────────────────────────────
function CongestionIncidentRow({ incident, onResolve, onSnapshot }) {
    const cfg = LEVEL_CONFIG[incident.level] || LEVEL_CONFIG[2];
    const hasSnapshot = !!incident.snapshot;

    return (
        <div className={`ci-row ${incident.resolved ? 'resolved' : 'active'}`}>

            {/* Snapshot thumbnail */}
            <div className="ci-thumb-wrap">
                {hasSnapshot ? (
                    <img
                        src={`${API_BASE}${incident.snapshot}`}
                        alt="snapshot"
                        className="ci-thumb"
                        onClick={() => onSnapshot(incident)}
                        title="Cliquer pour agrandir"
                    />
                ) : (
                    <div className="ci-thumb-empty">
                        <span>📷</span>
                        <span>Aucun</span>
                    </div>
                )}
            </div>

            {/* Info */}
            <div className="ci-row-left">
                <span className="ci-dot" style={{ background: cfg.color }} />
                <div className="ci-row-info">
                    <span className="ci-row-id">{incident.id}</span>
                    <span className="ci-row-label" style={{ color: cfg.color }}>
                        {incident.label}
                    </span>
                </div>
            </div>

            {/* Stats */}
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

            {/* Right actions */}
            <div className="ci-row-right">
                <span className="ci-timestamp">{incident.timestamp}</span>
                <div className="ci-row-btns">
                    {hasSnapshot && (
                        <>
                            <button
                                className="adm-btn-secondary ci-snap-btn"
                                onClick={() => onSnapshot(incident)}
                                title="Voir snapshot"
                            >
                                🔍 Snapshot
                            </button>
                            <a
                                href={`${API_BASE}/api/snapshots/${incident.id}/download`}
                                download={`${incident.id}.jpg`}
                                className="adm-btn-secondary ci-snap-btn"
                                title="Télécharger snapshot"
                            >
                                📥
                            </a>
                        </>
                    )}
                    {incident.resolved ? (
                        <span className="ci-badge-resolved">✓ Résolu</span>
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
        </div>
    );
}

// ── Main Page ─────────────────────────────────────────────────
export default function Incidents() {
    const { accidentsGPS } = useTrafik();
    const activeAccidents = accidentsGPS.filter(a => a.active);
    const resolvedAccidents = accidentsGPS.filter(a => !a.active);

    const [congestionIncidents, setCongestionIncidents] = useState([]);
    const [incidentStats, setIncidentStats] = useState(null);
    const [apiConnected, setApiConnected] = useState(false);
    const [filter, setFilter] = useState('all');
    const [levelFilter, setLevelFilter] = useState('all');
    const [search, setSearch] = useState('');
    const [lightboxIncident, setLightboxIncident] = useState(null);

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
        const exportData = congestionIncidents.map(inc => ({
            ...inc,
            snapshot_url: inc.snapshot ? `${API_BASE}${inc.snapshot}` : null,
            snapshot_download: inc.snapshot
                ? `${API_BASE}/api/snapshots/${inc.id}/download`
                : null,
        }));
        const blob = new Blob([JSON.stringify(exportData, null, 2)],
            { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `incidents_${new Date().toISOString().slice(0, 10)}.json`;
        a.click();
    };

    const filtered = congestionIncidents.filter(inc => {
        if (filter === 'active' && inc.resolved) return false;
        if (filter === 'resolved' && !inc.resolved) return false;
        if (levelFilter !== 'all' && inc.level !== parseInt(levelFilter)) return false;
        if (search && !inc.id.toLowerCase().includes(search.toLowerCase()) &&
            !inc.label.toLowerCase().includes(search.toLowerCase())) return false;
        return true;
    });

    const totalActive = activeAccidents.length +
        congestionIncidents.filter(i => !i.resolved).length;

    return (
        <div className="adm-incidents-page">

            {/* Lightbox */}
            {lightboxIncident && (
                <SnapshotLightbox
                    incident={lightboxIncident}
                    onClose={() => setLightboxIncident(null)}
                />
            )}

            {/* Header */}
            <div className="adm-incidents-header">
                <div className="adm-incidents-title">
                    <h2>Gestion des Incidents</h2>
                    <div className="adm-incidents-summary">
                        <span className="adm-badge-red">{totalActive} actifs</span>
                        <span className="adm-badge-gray">
                            {incidentStats?.resolved ?? resolvedAccidents.length} résolus
                        </span>
                        <span className={`ci-api-badge ${apiConnected ? 'ok' : 'err'}`}>
                            {apiConnected ? '● API connectée' : '○ API déconnectée'}
                        </span>
                    </div>
                </div>
                <div className="adm-incidents-filters">
                    <input
                        type="text"
                        placeholder="Rechercher ID ou label..."
                        className="adm-input-search"
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                    />
                    <select className="adm-select-filter" value={levelFilter}
                            onChange={e => setLevelFilter(e.target.value)}>
                        <option value="all">Tous les niveaux</option>
                        <option value="1">Modéré</option>
                        <option value="2">Lourd</option>
                        <option value="3">Sévère</option>
                    </select>
                    <select className="adm-select-filter" value={filter}
                            onChange={e => setFilter(e.target.value)}>
                        <option value="all">Tous</option>
                        <option value="active">Actifs</option>
                        <option value="resolved">Résolus</option>
                    </select>
                    <button className="adm-btn-primary" onClick={handleExport}>
                        📥 Exporter JSON
                    </button>
                </div>
            </div>

            {/* Stats Bar */}
            {incidentStats && (
                <div className="ci-stats-bar">
                    <div className="ci-stats-box">
                        <span className="ci-stats-val">{incidentStats.total}</span>
                        <span className="ci-stats-key">Total</span>
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
                    <div className="ci-stats-box">
                        <span className="ci-stats-val">
                            {congestionIncidents.filter(i => i.snapshot).length}
                        </span>
                        <span className="ci-stats-key">📷 Snapshots</span>
                    </div>
                </div>
            )}

            <div className="adm-incidents-list">

                {/* Congestion Incidents */}
                <div className="ci-section-header">
                    <h3>Incidents Congestion · Détection IA</h3>
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
                                onSnapshot={setLightboxIncident}
                            />
                        ))}
                    </div>
                )}

                {/* Accident Incidents */}
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
                    <h3>Historique Accidents · Archivés</h3>
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