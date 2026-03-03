import React, { useState } from 'react';
import PublicMap from '../components/PublicMap';
import { useTrafik } from '../../../shared/context/TrafikContext';
import { Link } from 'react-router-dom';
import './Home.css';

const statusStyle = {
    free: { icon: '🟢', label: 'Fluide', color: '#2E7D32' },
    slow: { icon: '🟡', label: 'Dense', color: '#F57C00' },
    blocked: { icon: '🔴', label: 'BLOQUÉE', color: '#B71C1C' },
};

export default function Home() {
    const { routesData } = useTrafik();
    const [panelOpen, setPanelOpen] = useState(true);

    // Top 3 routes for the panel
    const panelRoutes = routesData.slice(0, 4);

    return (
        <div className="home-page">
            <div className="home-map-wrap">
                <PublicMap showProximityCircle />
            </div>

            {/* Retractable bottom panel */}
            <div className={`home-panel ${panelOpen ? 'home-panel-open' : ''}`}>
                <button className="home-panel-handle" onClick={() => setPanelOpen(o => !o)}>
                    <div className="home-panel-bar" />
                </button>

                {panelOpen && (
                    <>
                        <div className="home-panel-title">
                            État du trafic maintenant
                        </div>
                        <div className="home-panel-routes">
                            {panelRoutes.map(route => {
                                const s = statusStyle[route.status] || statusStyle.slow;
                                return (
                                    <div key={route.id} className="home-route-row">
                                        <span className="home-route-icon">{s.icon}</span>
                                        <span className="home-route-name">{route.name}</span>
                                        <span className="home-route-status" style={{ color: s.color }}>{s.label}</span>
                                        {route.extra != null && route.extra > 0 && (
                                            <span className="home-route-time">{route.extra} min</span>
                                        )}
                                        {route.status === 'blocked' && (
                                            <span className="home-route-time" style={{ color: '#B71C1C' }}>∞</span>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                        <Link to="/plan" className="home-plan-btn">
                            🗺️ Planifier mon itinéraire →
                        </Link>
                    </>
                )}
            </div>
        </div>
    );
}
