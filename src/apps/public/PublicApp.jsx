import React, { useState, useEffect } from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { MapIcon, NavigationIcon, RouteIcon, BellIcon } from 'lucide-react';
import Home from './pages/Home';
import RoutePlanner from './pages/RoutePlanner';
import RouteStatus from './pages/RouteStatus';
import { useTrafik } from '../../shared/context/TrafikContext';
import { useProximity } from '../../shared/hooks/useProximity';
import { useGeolocation } from '../../shared/hooks/useGeolocation';
import ProximityAlert from './components/ProximityAlert';
import './PublicApp.css';

export default function PublicApp() {
    const location = useLocation();
    const { accidentsGPS } = useTrafik();
    const { position } = useGeolocation();
    const { nearby, hasNearby } = useProximity(position, accidentsGPS, 30);

    const navItems = [
        { path: '/', icon: MapIcon, label: 'Carte' },
        { path: '/plan', icon: NavigationIcon, label: 'Itinéraire' },
        { path: '/routes', icon: RouteIcon, label: 'Routes' },
        { path: '#alertes', icon: BellIcon, label: 'Alertes' },
    ];

    return (
        <div className="pub-app">
            {/* Top Bar */}
            <header className="pub-topbar">
                <Link to="/" className="pub-logo">
                    <span className="pub-logo-text">TRAFIQ</span>
                    <span className="pub-logo-tag">Trafic en temps réel</span>
                </Link>

                <div className="pub-topbar-search">
                    <Link to="/plan" className="pub-search-btn">
                        <span className="pub-search-icon">📍</span>
                        <span className="pub-search-placeholder">De... → Vers...</span>
                        <span className="pub-search-icon">📍</span>
                    </Link>
                </div>

                <div className="pub-topbar-right">
                    <button className="pub-icon-btn" title="Notifications">
                        <BellIcon size={20} />
                        {hasNearby && <span className="pub-notif-badge">{nearby.length}</span>}
                    </button>
                    <button className="pub-icon-btn" title="Ma position">
                        <NavigationIcon size={20} />
                    </button>
                    <a href="/admin/login" className="pub-admin-link">Admin ↗</a>
                </div>
            </header>

            {/* Proximity Alert */}
            {hasNearby && <ProximityAlert accidents={nearby} />}

            {/* Main Content */}
            <main className="pub-main">
                <Routes>
                    <Route path="/" element={<Home />} />
                    <Route path="/plan" element={<RoutePlanner />} />
                    <Route path="/routes" element={<RouteStatus />} />
                </Routes>
            </main>

            {/* Bottom Nav (mobile) */}
            <nav className="pub-bottom-nav">
                {navItems.map(item => (
                    <Link
                        key={item.path}
                        to={item.path}
                        className={`pub-nav-item ${location.pathname === item.path ? 'pub-nav-active' : ''}`}
                    >
                        <item.icon size={22} />
                        <span>{item.label}</span>
                    </Link>
                ))}
            </nav>
        </div>
    );
}
