import React from 'react';
import { useTrafik } from '../../../shared/context/TrafikContext';
import StatCard from '../components/StatCard';
import AdminMap from '../components/AdminMap';
import EventLogRow from '../components/EventLogRow';
import IncidentCard from '../components/IncidentCard';
import './Dashboard.css';

export default function Dashboard() {
    const { stats, events, accidentsGPS } = useTrafik();

    const activeAccidentsCount = accidentsGPS.filter(a => a.active).length;

    return (
        <div className="adm-dashboard">
            {/* Row 1: Stat Cards */}
            <div className="adm-dash-stats">
                <StatCard
                    title="Véhicules détectés"
                    value={stats.vehicles}
                    trend="+12 vs hier"
                    trendPositive={true}
                />
                <StatCard
                    title="Accidents actifs"
                    value={activeAccidentsCount}
                    urgent={activeAccidentsCount > 0}
                />
                <StatCard
                    title="Routes bloquées"
                    value={stats.blocked}
                    urgent={stats.blocked > 0}
                />
                <StatCard
                    title="Auto-corrections"
                    value={stats.corrections}
                    trend="Précision IA"
                    trendPositive={true}
                />
                <StatCard
                    title="Confiance IA"
                    value={`${stats.confidence}%`}
                    gauge={stats.confidence}
                />
            </div>

            {/* Row 2: Map & Live Feed */}
            <div className="adm-dash-grid">
                <div className="adm-dash-map-wrap">
                    <div className="adm-card-header">
                        <h3>Surveillance Géographique Live</h3>
                        <div className="adm-card-actions">
                            <span className="adm-live-dot" /> LIVE
                        </div>
                    </div>
                    <div className="adm-dash-map-content">
                        <AdminMap />
                    </div>
                </div>

                <div className="adm-dash-feed">
                    <div className="adm-card-header">
                        <h3>Flux événements temps réel</h3>
                        <span className="adm-badge-blue">{events.length} logs</span>
                    </div>
                    <div className="adm-dash-feed-content">
                        {events.slice(0, 10).map((event, idx) => (
                            <EventLogRow key={event.id || idx} event={event} />
                        ))}
                    </div>
                </div>
            </div>

            {/* Row 3: Recent Incidents */}
            <div className="adm-dash-incidents">
                <div className="adm-card-header">
                    <h3>Incidents récents à traiter</h3>
                    <button className="adm-btn-text">Voir tous les incidents →</button>
                </div>
                <div className="adm-dash-incidents-grid">
                    {accidentsGPS.filter(a => a.active).map(acc => (
                        <IncidentCard key={acc.id} incident={acc} compact />
                    ))}
                </div>
            </div>
        </div>
    );
}
