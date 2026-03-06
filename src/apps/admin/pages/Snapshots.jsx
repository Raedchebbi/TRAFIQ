import React, { useState, useEffect, useCallback } from 'react';
import { useTrafik } from '../../../shared/context/TrafikContext';
import SnapshotViewer from '../components/SnapshotViewer';
import './Snapshots.css';

const API_BASE = 'http://localhost:5000';

const LEVEL_CONFIG = {
    0: { color: '#00c853' },
    1: { color: '#ffab00' },
    2: { color: '#ff6d00' },
    3: { color: '#d50000' },
};

// ── Lightbox ──────────────────────────────────────────────────
function Lightbox({ src, title, onClose, downloadHref }) {
    useEffect(() => {
        const fn = e => { if (e.key === 'Escape') onClose(); };
        window.addEventListener('keydown', fn);
        return () => window.removeEventListener('keydown', fn);
    }, [onClose]);

    return (
        <div className="adm-lightbox-overlay" onClick={onClose}>
            <div className="adm-lightbox-box" onClick={e => e.stopPropagation()}>
                <div className="adm-lightbox-header">
                    <span className="adm-lightbox-title">{title}</span>
                    <div style={{ display: 'flex', gap: 10 }}>
                        {downloadHref && (
                            <a href={downloadHref} download className="adm-btn-primary" style={{ fontSize: '0.75rem', padding: '6px 14px' }}>
                                📥 Télécharger
                            </a>
                        )}
                        <button className="adm-lightbox-close" onClick={onClose}>✕</button>
                    </div>
                </div>
                <img src={src} alt={title} className="adm-lightbox-img" />
            </div>
        </div>
    );
}

export default function Snapshots() {
    const { accidentsGPS } = useTrafik();

    // Real congestion snapshots from API
    const [congestionSnaps, setCongestionSnaps] = useState([]);
    const [apiConnected, setApiConnected] = useState(false);
    const [activeTab, setActiveTab] = useState('tous');
    const [lightbox, setLightbox] = useState(null); // { src, title, downloadHref }

    const fetchSnaps = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/incidents`);
            const data = await res.json();
            // Only incidents that have a snapshot
            setCongestionSnaps(data.filter(i => i.snapshot));
            setApiConnected(true);
        } catch {
            setApiConnected(false);
        }
    }, []);

    useEffect(() => {
        fetchSnaps();
        const interval = setInterval(fetchSnaps, 8000);
        return () => clearInterval(interval);
    }, [fetchSnaps]);

    const openLightboxAccident = (acc) => {
        setLightbox({
            src: null,         // canvas-based, handled separately
            accidentInc: acc,
        });
    };

    const openLightboxCongestion = (snap) => {
        setLightbox({
            src: `${API_BASE}${snap.snapshot}`,
            title: `${snap.id} — ${snap.label}`,
            downloadHref: `${API_BASE}/api/snapshots/${snap.id}/download`,
        });
    };

    // Filter
    const filteredAccidents = accidentsGPS.filter(a =>
        activeTab === 'tous' || activeTab === 'accidents'
    );
    const filteredCongestion = congestionSnaps.filter(() =>
        activeTab === 'tous' || activeTab === 'congestion'
    );

    return (
        <div className="adm-snapshots-page">

            {/* Lightbox */}
            {lightbox && !lightbox.accidentInc && (
                <Lightbox
                    src={lightbox.src}
                    title={lightbox.title}
                    downloadHref={lightbox.downloadHref}
                    onClose={() => setLightbox(null)}
                />
            )}

            {/* Header */}
            <div className="adm-snapshots-header">
                <div>
                    <h2>📷 Snapshots des incidents</h2>
                    <p style={{ color: '#667788', fontSize: '0.8rem', margin: '4px 0 0' }}>
                        {congestionSnaps.length} snapshots IA · {accidentsGPS.length} accidents
                        {apiConnected
                            ? <span style={{ color: '#00c853', marginLeft: 10 }}>● API connectée</span>
                            : <span style={{ color: '#ff5252', marginLeft: 10 }}>○ API déconnectée</span>}
                    </p>
                </div>
                <div className="adm-snapshots-filters">
                    <div className="adm-pill-group">
                        {['tous', 'congestion', 'accidents'].map(tab => (
                            <button
                                key={tab}
                                className={`adm-pill-btn ${activeTab === tab ? 'active' : ''}`}
                                onClick={() => setActiveTab(tab)}
                            >
                                {tab.charAt(0).toUpperCase() + tab.slice(1)}
                            </button>
                        ))}
                    </div>
                    <select className="adm-select-sort">
                        <option>Plus récent</option>
                        <option>Score ↓</option>
                    </select>
                </div>
            </div>

            {/* ── Congestion Snapshots (real) ── */}
            {(activeTab === 'tous' || activeTab === 'congestion') && (
                <>
                    <div className="ci-section-header" style={{ margin: '8px 0 14px' }}>
                        <h3>Congestion · Détection IA</h3>
                        <span className="adm-badge-blue">{filteredCongestion.length}</span>
                    </div>

                    {!apiConnected ? (
                        <div className="ci-no-api" style={{ marginBottom: 24 }}>
                            <p>⚠️ Backend Python non connecté</p>
                            <code>python api.py</code>
                        </div>
                    ) : filteredCongestion.length === 0 ? (
                        <div className="ci-empty" style={{ marginBottom: 24 }}>
                            Aucun snapshot de congestion disponible.
                        </div>
                    ) : (
                        <div className="adm-snapshots-grid" style={{ marginBottom: 32 }}>
                            {filteredCongestion.map(snap => {
                                const cfg = LEVEL_CONFIG[snap.level] || LEVEL_CONFIG[2];
                                return (
                                    <div key={snap.id} className={`adm-snapshot-card ${snap.resolved ? '' : 'active-snap'}`}>
                                        <div className="adm-snapshot-media" style={{ position: 'relative', cursor: 'pointer' }}
                                             onClick={() => openLightboxCongestion(snap)}>
                                            <img
                                                src={`${API_BASE}${snap.snapshot}`}
                                                alt={snap.id}
                                                style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: 6 }}
                                            />
                                            <div style={{
                                                position: 'absolute', top: 8, left: 8,
                                                background: 'rgba(0,0,0,0.7)', borderRadius: 4,
                                                padding: '3px 8px', fontSize: '0.65rem',
                                                color: cfg.color, fontWeight: 700,
                                            }}>
                                                {snap.label}
                                            </div>
                                            <div style={{
                                                position: 'absolute', inset: 0,
                                                background: 'rgba(0,0,0,0)',
                                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                opacity: 0, transition: 'all 0.2s',
                                                borderRadius: 6,
                                            }}
                                                className="snap-hover-overlay">
                                                <span style={{ fontSize: '1.5rem' }}>🔍</span>
                                            </div>
                                        </div>
                                        <div className="adm-snapshot-info">
                                            <div className="adm-snapshot-type-row">
                                                <span className="adm-badge-type" style={{ color: cfg.color, borderColor: cfg.color }}>
                                                    ⚠️ CONGESTION
                                                </span>
                                                <span className="adm-badge-lvl">L{snap.level}</span>
                                            </div>
                                            <div className="adm-snapshot-vehicles">
                                                🚗 {snap.vehicle_count} véhicules · {snap.slow_ratio}% lents
                                            </div>
                                            <div className="adm-snapshot-metrics">
                                                Vitesse moy: <strong>{snap.avg_speed} px/s</strong>
                                            </div>
                                            <div className="adm-snapshot-date">{snap.timestamp}</div>
                                            <div className="adm-snapshot-actions">
                                                <button
                                                    className="adm-btn-small-outline"
                                                    onClick={() => openLightboxCongestion(snap)}
                                                >
                                                    🔍 Agrandir
                                                </button>
                                                <a
                                                    href={`${API_BASE}/api/snapshots/${snap.id}/download`}
                                                    download={`${snap.id}.jpg`}
                                                    className="adm-btn-small-outline"
                                                >
                                                    📥 Télécharger
                                                </a>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </>
            )}

            {/* ── Accident Snapshots (existing mock) ── */}
            {(activeTab === 'tous' || activeTab === 'accidents') && (
                <>
                    <div className="ci-section-header" style={{ margin: '8px 0 14px' }}>
                        <h3>Accidents · Données système</h3>
                        <span className="adm-badge-red">{accidentsGPS.length}</span>
                    </div>
                    <div className="adm-snapshots-grid">
                        {accidentsGPS.map(acc => (
                            <div key={acc.id} className="adm-snapshot-card">
                                <div className="adm-snapshot-media">
                                    <SnapshotViewer incident={acc} width={320} height={200} />
                                </div>
                                <div className="adm-snapshot-info">
                                    <div className="adm-snapshot-type-row">
                                        <span className={`adm-badge-type ${acc.severity}`}>
                                            [⚠️ {acc.type}]
                                        </span>
                                        <span className="adm-badge-lvl">{acc.level} ★★</span>
                                    </div>
                                    <div className="adm-snapshot-vehicles">Véhicules {acc.vehicles}</div>
                                    <div className="adm-snapshot-metrics">
                                        Score : <strong>{acc.score}</strong> · Conf. : <strong>{(acc.conf * 100).toFixed(0)}%</strong>
                                    </div>
                                    <div className="adm-snapshot-date">15 Jan 2025 — 14:32:05</div>
                                    <div className="adm-snapshot-actions">
                                        <button className="adm-btn-small-outline">🔍 Agrandir</button>
                                        <button className="adm-btn-small-outline">📥 Télécharger</button>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </>
            )}
        </div>
    );
}