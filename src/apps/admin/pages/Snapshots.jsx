import React from 'react';
import { useTrafik } from '../../../shared/context/TrafikContext';
import SnapshotViewer from '../components/SnapshotViewer';
import './Snapshots.css';

export default function Snapshots() {
    const { accidentsGPS } = useTrafik();

    return (
        <div className="adm-snapshots-page">
            <div className="adm-snapshots-header">
                <h2>📷 Snapshots des incidents</h2>
                <div className="adm-snapshots-filters">
                    <div className="adm-pill-group">
                        <button className="adm-pill-btn active">Tous</button>
                        <button className="adm-pill-btn">Accidents</button>
                        <button className="adm-pill-btn">Épaves</button>
                    </div>
                    <select className="adm-select-sort">
                        <option>Plus récent</option>
                        <option>Score ↓</option>
                    </select>
                </div>
            </div>

            <div className="adm-snapshots-grid">
                {accidentsGPS.map(acc => (
                    <div key={acc.id} className="adm-snapshot-card">
                        <div className="adm-snapshot-media">
                            <SnapshotViewer incident={acc} width={320} height={200} />
                        </div>
                        <div className="adm-snapshot-info">
                            <div className="adm-snapshot-type-row">
                                <span className={`adm-badge-type ${acc.severity}`}>[⚠️ {acc.type}]</span>
                                <span className="adm-badge-lvl">{acc.level} ★★</span>
                            </div>
                            <div className="adm-snapshot-vehicles">Véhicules {acc.vehicles}</div>
                            <div className="adm-snapshot-metrics">
                                Score : <strong>{acc.score}</strong> · Conf. : <strong>{(acc.conf * 100).toFixed(0)}%</strong>
                            </div>
                            <div className="adm-snapshot-date">15 Jan 2025 — 14:32:05</div>
                            <div className="adm-snapshot-actions">
                                <button className="adm-btn-small-outline">🔍 Agrandir</button>
                                <button className="adm-btn-small-outline">📥 Télécharger</button>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
