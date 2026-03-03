import React, { useState } from 'react';
import { MapContainer, TileLayer, Polyline, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import RouteCard from '../components/RouteCard';
import { ITINERAIRES_MOCK } from '../../../shared/hooks/useRoutes';
import './RoutePlanner.css';

const startIcon = L.divIcon({ html: `<div style="background:#2E7D32;width:16px;height:16px;border-radius:50%;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3)"></div>`, className: '', iconAnchor: [8, 8] });
const endIcon = L.divIcon({ html: `<div style="background:#E53935;width:16px;height:16px;border-radius:50%;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3)"></div>`, className: '', iconAnchor: [8, 8] });

const PLACES = ['Centre-ville Tunis', 'Lac Tunis', 'Bardo', 'La Marsa', 'Carthage', 'Sousse'];

export default function RoutePlanner() {
    const [from, setFrom] = useState('');
    const [to, setTo] = useState('');
    const [searched, setSearched] = useState(false);
    const [selectedId, setSelectedId] = useState(1);
    const [activeRoute, setActiveRoute] = useState(null);

    const handleSearch = () => {
        if (from && to) setSearched(true);
    };

    const handleStart = route => {
        setSelectedId(route.id);
        setActiveRoute(route);
    };

    const selectedRoute = ITINERAIRES_MOCK.find(r => r.id === selectedId);

    return (
        <div className="planner-page">
            <div className="planner-map">
                <MapContainer center={[36.808, 10.181]} zoom={14} style={{ height: '100%', width: '100%' }} zoomControl={false}>
                    <TileLayer url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png" />
                    {searched && ITINERAIRES_MOCK.map(route => (
                        <Polyline
                            key={route.id}
                            positions={route.coords}
                            color={route.color}
                            weight={route.id === selectedId ? route.weight + 2 : route.weight}
                            opacity={route.id === selectedId ? 1 : route.opacity}
                            dashArray={route.dashArray}
                        />
                    ))}
                    {searched && (
                        <>
                            <Marker position={ITINERAIRES_MOCK[0].coords[0]} icon={startIcon}>
                                <Popup>📍 Départ : {from}</Popup>
                            </Marker>
                            <Marker position={ITINERAIRES_MOCK[0].coords[ITINERAIRES_MOCK[0].coords.length - 1]} icon={endIcon}>
                                <Popup>🏁 Destination : {to}</Popup>
                            </Marker>
                        </>
                    )}
                </MapContainer>
            </div>

            <div className="planner-panel">
                <div className="planner-search-box">
                    <div className="planner-input-row">
                        <span className="planner-input-icon">📍</span>
                        <select value={from} onChange={e => setFrom(e.target.value)} className="planner-select">
                            <option value="">Point de départ...</option>
                            {PLACES.map(p => <option key={p} value={p}>{p}</option>)}
                        </select>
                        <button className="planner-locate-btn" onClick={() => setFrom('Ma position')}>📍 Ma pos</button>
                    </div>
                    <div className="planner-divider" />
                    <div className="planner-input-row">
                        <span className="planner-input-icon">🏁</span>
                        <select value={to} onChange={e => setTo(e.target.value)} className="planner-select">
                            <option value="">Destination...</option>
                            {PLACES.filter(p => p !== from).map(p => <option key={p} value={p}>{p}</option>)}
                        </select>
                    </div>
                    <button className="planner-search-btn" onClick={handleSearch}>
                        Calculer les itinéraires →
                    </button>
                </div>

                {searched && (
                    <div className="planner-results">
                        <div className="planner-results-title">3 itinéraires disponibles</div>
                        {ITINERAIRES_MOCK.map(route => (
                            <RouteCard
                                key={route.id}
                                route={route}
                                selected={route.id === selectedId}
                                onStart={handleStart}
                            />
                        ))}
                    </div>
                )}

                {!searched && (
                    <div className="planner-empty">
                        <div className="planner-empty-icon">🗺️</div>
                        <div className="planner-empty-text">Choisissez un départ et une destination<br />pour calculer les meilleurs itinéraires.</div>
                    </div>
                )}
            </div>
        </div>
    );
}
