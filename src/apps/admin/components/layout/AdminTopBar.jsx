import React from 'react';
import { useAuth } from '../../../../shared/context/AuthContext';
import { useTrafik } from '../../../../shared/context/TrafikContext';
import { useLocation } from 'react-router-dom';
import './AdminTopBar.css';

const pageTitles = {
    '/admin/dashboard': 'Vue d\'ensemble',
    '/admin/live': 'Live Monitoring',
    '/admin/incidents': 'Gestion des Incidents',
    '/admin/ai-agent': 'Monitoring Agent IA',
    '/admin/snapshots': 'Snapshots Accidents',
    '/admin/analytics': 'Statistiques & Analytics',
    '/admin/settings': 'Paramètres Système',
};

export default function AdminTopBar() {
    const { user } = useAuth();
    const { stats } = useTrafik();
    const location = useLocation();

    const title = pageTitles[location.pathname] || 'Tableau de Bord';

    return (
        <header className="adm-topbar">
            <div className="adm-tb-left">
                <h1 className="adm-tb-title">{title}</h1>
            </div>

            <div className="adm-tb-center">
                <div className="adm-tb-status">
                    <span className="adm-status-dot green" />
                    <span className="adm-status-text">Système opérationnel · </span>
                    <span className="adm-status-count">{stats.accidents} accidents actifs · </span>
                    <span className="adm-status-count">{stats.vehicles} véhicules</span>
                </div>
            </div>

            <div className="adm-tb-right">
                <button className="adm-tb-notif" title="Notifications">
                    🔔
                    {stats.accidents > 0 && <span className="adm-notif-dot" />}
                </button>
                <div className="adm-tb-user">
                    <span className="adm-tb-user-name">{user?.name}</span>
                    <div className="adm-tb-avatar">{user?.avatar}</div>
                </div>
            </div>
        </header>
    );
}
