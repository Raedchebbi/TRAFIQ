import React, { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, Circle, useMap } from 'react-leaflet';
import L from 'leaflet';
import { useTrafik } from '../../../shared/context/TrafikContext';
import { useGeolocation } from '../../../shared/hooks/useGeolocation';
import { useProximity } from '../../../shared/hooks/useProximity';

// Custom icons
const createIcon = (color, size = 14) => L.divIcon({
    html: `<div style="width:${size}px;height:${size}px;border-radius:50%;background:${color};border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3)"></div>`,
    className: '', iconAnchor: [size / 2, size / 2]
});

const userIcon = L.divIcon({
    html: `<div class="user-marker"><div class="user-marker-dot"></div><div class="user-marker-ring"></div></div>`,
    className: '', iconAnchor: [14, 14]
});

const accidentIcon = L.divIcon({
    html: `<div style="background:#E53935;color:white;width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;border:2px solid white;box-shadow:0 2px 8px rgba(229,57,53,0.5);animation:pulse 1.5s infinite">🔴</div>`,
    className: '', iconAnchor: [14, 14]
});

const polylineColors = { free: '#2E7D32', blocked: '#B71C1C', slow: '#FF8F00' };

function RecenterMap({ position }) {
    const map = useMap();
    useEffect(() => { if (position) map.setView([position.lat, position.lng], 15); }, []);
    return null;
}

export default function PublicMap({ activeRoute, showProximityCircle }) {
    const { accidentsGPS, polylines } = useTrafik();
    const { position } = useGeolocation();
    const { nearby } = useProximity(position, accidentsGPS, 30);
    const [legendVisible, setLegendVisible] = useState(true);

    const activeAccidents = accidentsGPS.filter(a => a.active);

    return (
        <div className="pub-map-container">
            <style>{`
        .user-marker { position:relative; width:28px; height:28px; }
        .user-marker-dot { position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); width:12px; height:12px; background:#1A73E8; border-radius:50%; border:2px solid white; z-index:2; }
        .user-marker-ring { position:absolute; top:0; left:0; width:28px; height:28px; border:2px solid rgba(26,115,232,0.4); border-radius:50%; animation:ripple 2s ease-out infinite; }
        .leaflet-popup-content-wrapper { border-radius:12px; box-shadow:0 4px 20px rgba(0,0,0,0.15); }
      `}</style>

            <MapContainer
                center={[36.8068, 10.1816]}
                zoom={15}
                style={{ height: '100%', width: '100%' }}
                zoomControl={false}
            >
                <TileLayer
                    url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                    maxZoom={19}
                />
                <RecenterMap position={position} />

                {/* Road polylines */}
                {polylines.map(road => (
                    <Polyline
                        key={road.id}
                        positions={road.coords}
                        color={polylineColors[road.status] || '#888'}
                        weight={road.status === 'blocked' ? 5 : 3}
                        opacity={0.8}
                    >
                        <Popup><b>{road.id}</b> — {road.status}</Popup>
                    </Polyline>
                ))}

                {/* Active route */}
                {activeRoute && (
                    <Polyline
                        positions={activeRoute.coords}
                        color={activeRoute.color}
                        weight={activeRoute.weight}
                        opacity={activeRoute.opacity}
                        dashArray={activeRoute.dashArray}
                    />
                )}

                {/* User position */}
                {position && (
                    <>
                        <Marker position={[position.lat, position.lng]} icon={userIcon}>
                            <Popup>📍 Ma position</Popup>
                        </Marker>
                        {showProximityCircle && nearby.length > 0 && (
                            <Circle
                                center={[position.lat, position.lng]}
                                radius={30}
                                color="#1A73E8"
                                fillColor="#1A73E8"
                                fillOpacity={0.1}
                                weight={2}
                                dashArray="4,4"
                            />
                        )}
                    </>
                )}

                {/* Accidents */}
                {activeAccidents.map(acc => (
                    <React.Fragment key={acc.id}>
                        <Marker position={[acc.lat, acc.lng]} icon={accidentIcon}>
                            <Popup>
                                <div style={{ fontFamily: 'var(--font-body)', minWidth: 180 }}>
                                    <div style={{ fontWeight: 700, color: '#E53935', marginBottom: 4 }}>🚨 {acc.type}</div>
                                    <div style={{ fontSize: '0.8rem', color: '#5A6A7A' }}>Sévérité : <b>{acc.severity}</b></div>
                                    <div style={{ fontSize: '0.8rem', color: '#5A6A7A' }}>Score : {acc.score}</div>
                                </div>
                            </Popup>
                        </Marker>
                        <Circle
                            center={[acc.lat, acc.lng]}
                            radius={15}
                            color="#E53935"
                            fillColor="#E53935"
                            fillOpacity={0.15}
                            weight={2}
                        />
                    </React.Fragment>
                ))}
            </MapContainer>

            {/* Legend */}
            {legendVisible && (
                <div className="pub-map-legend">
                    <span>🔴 Accident</span>
                    <span>🟡 Dense</span>
                    <span style={{ color: '#B71C1C' }}>● Bloqué</span>
                    <span style={{ color: '#2E7D32' }}>● Libre</span>
                    <button onClick={() => setLegendVisible(false)}>Masquer</button>
                </div>
            )}
        </div>
    );
}
