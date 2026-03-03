import React from 'react';
import './RouteCard.css';

const statusConfig = {
    free: { label: 'Trafic fluide', color: '#2E7D32', bg: '#E8F5E9', icon: '🟢' },
    slow: { label: 'Trafic modéré', color: '#F57C00', bg: '#FFF3E0', icon: '🟡' },
    blocked: { label: 'ACCIDENT EN COURS', color: '#B71C1C', bg: '#FFEBEE', icon: '🔴', urgent: true },
};

export default function RouteCard({ route, onStart, selected }) {
    const { label, labelColor, labelBg, roads, time, dist, status, incidents, isAccident, extraMin } = route;
    const sc = statusConfig[status] || statusConfig.slow;

    return (
        <div className={`route-card ${selected ? 'route-card-selected' : ''} ${isAccident ? 'route-card-accident' : ''}`}>
            <div className="route-card-header">
                <span className="route-card-label" style={{ color: labelColor, background: labelBg }}>
                    {label}
                </span>
            </div>

            <div className="route-card-roads">
                {roads.join(' — ')}
            </div>

            <div className="route-card-stats">
                <span>⏱ {time} min</span>
                <span>📏 {dist} km</span>
                <span style={{ color: sc.color }}>{sc.icon} {sc.label}</span>
            </div>

            {incidents > 0 ? (
                <div className={`route-card-incident ${sc.urgent ? 'urgent' : ''}`}>
                    {sc.urgent
                        ? `🚨 Accident confirmé par TRAFIQ AI — Voie partiellement bloquée. Temps d'attente estimé : 15-20 min`
                        : `ℹ️ ${incidents} incident(s) signalé(s) sur ce trajet`}
                </div>
            ) : (
                <div className="route-card-clear">⚠️ Aucun incident signalé sur ce trajet</div>
            )}

            <button className="route-card-btn" onClick={() => onStart && onStart(route)}>
                ▶ {isAccident ? 'Quand même utiliser' : 'Démarrer ce trajet'}
            </button>
        </div>
    );
}
