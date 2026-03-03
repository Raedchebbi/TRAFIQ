import React from 'react';
import { useTrafik } from '../../../shared/context/TrafikContext';
import { Link } from 'react-router-dom';
import './RouteStatus.css';

const statusMeta = {
    free: { icon: '🟢', label: 'Fluide', arrow: '↓', color: '#2E7D32' },
    slow: { icon: '🟡', label: 'Dense', arrow: '↑', color: '#F57C00' },
    blocked: { icon: '🔴', label: 'BLOQUÉ', arrow: '⚠️', color: '#B71C1C' },
};

export default function RouteStatus() {
    const { routesData, stats } = useTrafik();

    const categories = [...new Set(routesData.map(r => r.category))];
    const accidents = routesData.filter(r => r.status !== 'free').length;
    const blocked = routesData.filter(r => r.status === 'blocked').length;
    const slow = routesData.filter(r => r.status === 'slow').length;

    const globalLabel = blocked > 0 ? 'PERTURBÉ' : slow > 0 ? 'MODÉRÉ' : 'FLUIDE';
    const globalColor = blocked > 0 ? '#B71C1C' : slow > 0 ? '#F57C00' : '#2E7D32';
    const globalIcon = blocked > 0 ? '🔴' : slow > 0 ? '🟡' : '🟢';

    return (
        <div className="routes-page">
            <div className="routes-header">
                <h1>🛣️ État des routes — Tunis et environs</h1>
                <div className="routes-update">
                    Mis à jour il y a 30 secondes · Source : TRAFIQ AI Engine
                </div>
            </div>

            {/* Global indicator */}
            <div className="routes-global" style={{ borderLeftColor: globalColor }}>
                <span className="routes-global-icon">{globalIcon}</span>
                <div>
                    <div className="routes-global-label" style={{ color: globalColor }}>
                        Trafic {globalLabel} à Tunis
                    </div>
                    <div className="routes-global-sub">
                        {stats.accidents} accidents actifs · {blocked} route{blocked !== 1 ? 's' : ''} bloquée{blocked !== 1 ? 's' : ''} · {slow} route{slow !== 1 ? 's' : ''} dense{slow !== 1 ? 's' : ''}
                    </div>
                </div>
            </div>

            {/* Route categories */}
            <div className="routes-content">
                {categories.map(cat => (
                    <div key={cat} className="routes-section">
                        <div className="routes-section-title">{cat}</div>
                        {routesData.filter(r => r.category === cat).map(route => {
                            const s = statusMeta[route.status] || statusMeta.slow;
                            return (
                                <div key={route.id} className="routes-row">
                                    <span className="routes-row-icon">{s.icon}</span>
                                    <span className="routes-row-name">{route.name}</span>
                                    <span className="routes-row-status" style={{ color: s.color }}>{s.label}</span>
                                    <span className="routes-row-meta" style={{ color: s.color }}>
                                        {s.arrow}
                                        {route.extra ? ` +${route.extra} min` : ''}
                                        {route.incident ? ' Accident' : ''}
                                        {route.reason ? ` Travaux` : ''}
                                    </span>
                                    {route.status === 'blocked' && (
                                        <Link to="/plan" className="routes-alt-btn">
                                            Itinéraires alternatifs →
                                        </Link>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                ))}
            </div>
        </div>
    );
}
