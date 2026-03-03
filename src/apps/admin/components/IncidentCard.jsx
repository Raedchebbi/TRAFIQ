import React from 'react';
import './IncidentCard.css';

export default function IncidentCard({ incident, compact }) {
    const { id, type, severity, vehicles, score, conf, level } = incident;

    return (
        <div className={`adm-incident-card s-${severity}`}>
            <div className="adm-incident-header">
                <span className="adm-incident-type">{type}</span>
                <span className="adm-incident-level">{level}</span>
            </div>

            <div className="adm-incident-main">
                <div className="adm-incident-vehicles">Véhicules {vehicles}</div>
                <div className="adm-incident-id">ID Incident : {id}</div>
            </div>

            <div className="adm-incident-meta">
                <div className="adm-meta-pill">Score: {score}</div>
                <div className="adm-meta-pill">Conf: {(conf * 100).toFixed(0)}%</div>
            </div>

            {!compact && (
                <div className="adm-incident-actions">
                    <button className="adm-btn-primary">📷 Snapshot</button>
                    <button className="adm-btn-secondary">📍 Localiser</button>
                </div>
            )}

            {compact && (
                <div className="adm-incident-mini-actions">
                    <button className="adm-icon-btn">🔍</button>
                    <button className="adm-icon-btn">📍</button>
                </div>
            )}
        </div>
    );
}
