import React, { useEffect, useState, useRef } from 'react';
import './LiveMonitoring.css';

const API_BASE = 'http://localhost:5000';

const LEVEL_CONFIG = {
    0: { label: 'TRAFFIC FREE',     color: '#00c853', bg: 'rgba(0,200,83,0.12)'   },
    1: { label: 'MODERATE TRAFFIC', color: '#ffab00', bg: 'rgba(255,171,0,0.12)'  },
    2: { label: 'HEAVY CONGESTION', color: '#ff6d00', bg: 'rgba(255,109,0,0.12)'  },
    3: { label: 'SEVERE CONGESTION',color: '#d50000', bg: 'rgba(213,0,0,0.15)'    },
};

export default function LiveMonitoring() {
    const [status, setStatus] = useState(null);
    const [connected, setConnected] = useState(false);
    const [alertFlash, setAlertFlash] = useState(false);
    const alertInterval = useRef(null);

    // Poll /api/status every second
    useEffect(() => {
        const poll = async () => {
            try {
                const res = await fetch(`${API_BASE}/api/status`);
                const data = await res.json();
                setStatus(data);
                setConnected(true);
            } catch {
                setConnected(false);
            }
        };
        poll();
        const interval = setInterval(poll, 1000);
        return () => clearInterval(interval);
    }, []);

    // Alert flash effect
    useEffect(() => {
        if (status?.alert_active) {
            alertInterval.current = setInterval(() => setAlertFlash(f => !f), 600);
        } else {
            clearInterval(alertInterval.current);
            setAlertFlash(false);
        }
        return () => clearInterval(alertInterval.current);
    }, [status?.alert_active]);

    const level = status?.congestion_level ?? 0;
    const cfg = LEVEL_CONFIG[level];

    return (
        <div className="adm-live-monitoring">

            {/* ── Header ── */}
            <div className="adm-live-header">
                <div className="adm-live-info">
                    <h2>Surveillance Live · Détection IA</h2>
                    <p>
                        {connected
                            ? `Flux actif · ${status?.stream_title || 'YouTube Live'}`
                            : 'Connexion au backend...'}
                    </p>
                </div>
                <div className="adm-live-controls">
                    <span className={`lm-conn-badge ${connected ? 'ok' : 'err'}`}>
                        {connected ? '● CONNECTÉ' : '○ DÉCONNECTÉ'}
                    </span>
                    <span className="lm-fps-badge">
                        {status?.fps ?? '--'} FPS
                    </span>
                </div>
            </div>

            {/* ── Congestion Alert Banner ── */}
            {status?.alert_active && (
                <div className={`lm-alert-banner ${alertFlash ? 'flash' : ''}`}>
                    🚨 ALERTE CONGESTION — {status.congestion_label}
                </div>
            )}

            {/* ── Main Grid ── */}
            <div className="lm-main-grid">

                {/* Live Video Stream */}
                <div className="lm-stream-wrap">
                    <div className="lm-stream-header">
                        <span className="adm-live-dot" /> LIVE · Caméra principale
                    </div>
                    <img
                        src={`${API_BASE}/api/stream`}
                        alt="Live stream"
                        className="lm-stream-img"
                        onError={(e) => { e.target.style.display = 'none'; }}
                    />
                    {!connected && (
                        <div className="lm-stream-placeholder">
                            <p>⏳ En attente du backend Python...</p>
                            <code>python api.py</code>
                        </div>
                    )}
                </div>

                {/* Stats Panel */}
                <div className="lm-stats-panel">

                    {/* Congestion Level Card */}
                    <div className="lm-card lm-congestion-card"
                         style={{ background: cfg.bg, borderColor: cfg.color }}>
                        <p className="lm-card-label">Niveau de congestion</p>
                        <p className="lm-congestion-label" style={{ color: cfg.color }}>
                            {cfg.label}
                        </p>
                        {/* Level bar */}
                        <div className="lm-level-bar">
                            {[0, 1, 2, 3].map(i => (
                                <div
                                    key={i}
                                    className="lm-level-seg"
                                    style={{
                                        background: i <= level
                                            ? LEVEL_CONFIG[i].color
                                            : 'rgba(255,255,255,0.1)'
                                    }}
                                />
                            ))}
                        </div>
                    </div>

                    {/* Stat Grid */}
                    <div className="lm-stat-grid">
                        <div className="lm-stat-box">
                            <span className="lm-stat-value">{status?.vehicle_count ?? '--'}</span>
                            <span className="lm-stat-label">Véhicules détectés</span>
                        </div>
                        <div className="lm-stat-box">
                            <span className="lm-stat-value">{status?.avg_speed ?? '--'}</span>
                            <span className="lm-stat-label">Vitesse moy. (px/s)</span>
                        </div>
                        <div className="lm-stat-box">
                            <span className="lm-stat-value"
                                  style={{ color: (status?.slow_ratio ?? 0) > 50 ? '#ff6d00' : '#00c853' }}>
                                {status?.slow_ratio ?? '--'}%
                            </span>
                            <span className="lm-stat-label">Véhicules lents</span>
                        </div>
                        <div className="lm-stat-box">
                            <span className="lm-stat-value">
                                {status ? status.vehicle_count_down + status.vehicle_count_up : '--'}
                            </span>
                            <span className="lm-stat-label">Total comptés</span>
                        </div>
                    </div>

                    {/* Direction counters */}
                    <div className="lm-card lm-direction-card">
                        <p className="lm-card-label">Flux directionnel</p>
                        <div className="lm-direction-row">
                            <div className="lm-dir-box down">
                                <span className="lm-dir-arrow">▼</span>
                                <span className="lm-dir-count">{status?.vehicle_count_down ?? 0}</span>
                                <span className="lm-dir-label">Descend</span>
                            </div>
                            <div className="lm-dir-divider" />
                            <div className="lm-dir-box up">
                                <span className="lm-dir-arrow">▲</span>
                                <span className="lm-dir-count">{status?.vehicle_count_up ?? 0}</span>
                                <span className="lm-dir-label">Monte</span>
                            </div>
                        </div>
                    </div>

                    {/* Backend status */}
                    <div className="lm-card lm-status-card">
                        <p className="lm-card-label">État du backend</p>
                        <div className="lm-status-row">
                            <span>Détection IA</span>
                            <span className={status?.running ? 'lm-dot-green' : 'lm-dot-red'}>
                                {status?.running ? '● Actif' : '○ Arrêté'}
                            </span>
                        </div>
                        <div className="lm-status-row">
                            <span>Alerte congestion</span>
                            <span className={status?.alert_active ? 'lm-dot-red' : 'lm-dot-green'}>
                                {status?.alert_active ? '● Active' : '● Normale'}
                            </span>
                        </div>
                        <div className="lm-status-row">
                            <span>Dernière mise à jour</span>
                            <span className="lm-dot-grey">
                                {status?.last_update
                                    ? new Date(status.last_update * 1000).toLocaleTimeString()
                                    : '--'}
                            </span>
                        </div>
                    </div>

                </div>
            </div>
        </div>
    );
}