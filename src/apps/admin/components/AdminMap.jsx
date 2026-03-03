import React from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, Circle, Rectangle } from 'react-leaflet';
import { useTrafik } from '../../../shared/context/TrafikContext';
import L from 'leaflet';

// Admin specific icons (more technical)
const vehicleIcon = (id, speed) => L.divIcon({
    html: `<div class="adm-v-marker">
           <div class="adm-v-dot"></div>
           <div class="adm-v-label">#${id} ${speed}px/s</div>
         </div>`,
    className: '', iconAnchor: [6, 6]
});

const accidentIcon = L.divIcon({
    html: `<div class="adm-acc-marker">🚨</div>`,
    className: '', iconAnchor: [12, 12]
});

export default function AdminMap() {
    const { accidentsGPS, vehicleTracks, polylines } = useTrafik();

    return (
        <div className="adm-map-container" style={{ height: '100%', width: '100%' }}>
            <style>{`
        .adm-v-marker { position: relative; }
        .adm-v-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--adm-accent); border: 1.5px solid white; }
        .adm-v-label { 
          position: absolute; top: -18px; left: 50%; transform: translateX(-50%);
          background: rgba(15, 28, 46, 0.85); color: #fff; font-size: 0.6rem; 
          padding: 1px 4px; border-radius: 4px; white-space: nowrap; font-family: var(--font-mono);
          border: 1px solid rgba(255,255,255,0.1);
        }
        .adm-acc-marker { 
          font-size: 1.2rem; display: flex; align-items: center; justify-content: center;
          background: #fff; border-radius: 50%; width: 24px; height: 24px;
          box-shadow: 0 0 15px var(--color-accident); border: 2px solid var(--color-accident);
          animation: pulse 1s infinite;
        }
      `}</style>

            <MapContainer
                center={[36.8068, 10.1816]}
                zoom={16}
                style={{ height: '100%', width: '100%' }}
                zoomControl={true}
            >
                <TileLayer
                    url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager_labels_under/{z}/{x}/{y}{r}.png"
                    attribution='&copy; OpenStreetMap &copy; CartoDB'
                />

                {/* Technical Polylines */}
                {polylines.map(p => (
                    <Polyline
                        key={p.id}
                        positions={p.coords}
                        color={p.status === 'blocked' ? '#B71C1C' : '#90A4AE'}
                        weight={1.5}
                        opacity={0.5}
                        dashArray="5,5"
                    />
                ))}

                {/* Vehicles */}
                {vehicleTracks.map(v => (
                    <Marker key={v.id} position={[v.lat, v.lng]} icon={vehicleIcon(v.id, v.speed)}>
                        <Popup>
                            <div className="adm-popup">
                                <b>Véhicule #${v.id}</b><br />
                                Vitesse : {v.speed} px/s
                            </div>
                        </Popup>
                    </Marker>
                ))}

                {/* Accidents & Surveillance Zones */}
                {accidentsGPS.filter(a => a.active).map(acc => (
                    <React.Fragment key={acc.id}>
                        <Marker position={[acc.lat, acc.lng]} icon={accidentIcon}>
                            <Popup>
                                <div className="adm-popup">
                                    <div style={{ color: 'var(--color-accident)', fontWeight: 700 }}>{acc.type}</div>
                                    <div>ID : {acc.id}</div>
                                    <div>Niveau : {acc.level}</div>
                                    <button className="adm-btn-small">Voir Snapshot</button>
                                </div>
                            </Popup>
                        </Marker>
                        <Circle
                            center={[acc.lat, acc.lng]}
                            radius={30}
                            color="var(--color-accident)"
                            fillOpacity={0.1}
                            weight={1}
                        />
                    </React.Fragment>
                ))}

                {/* Surveillance Grid Mock */}
                <Rectangle
                    bounds={[[36.805, 10.180], [36.808, 10.183]]}
                    color="#0066FF"
                    weight={1}
                    fill={false}
                    dashArray="4,4"
                />
            </MapContainer>
        </div>
    );
}
