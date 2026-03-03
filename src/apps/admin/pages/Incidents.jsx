import React from 'react';
import { useTrafik } from '../../../shared/context/TrafikContext';
import IncidentCard from '../components/IncidentCard';
import './Incidents.css';

export default function Incidents() {
    const { accidentsGPS } = useTrafik();
    const activeCount = accidentsGPS.filter(a => a.active).length;

    return (
        <div className="adm-incidents-page">
            <div className="adm-incidents-header">
                <div className="adm-incidents-title">
                    <h2>Gestion des Incidents</h2>
                    <div className="adm-incidents-summary">
                        <span className="adm-badge-red">{activeCount} actifs</span>
                        <span className="adm-badge-gray">24 résolus aujourd'hui</span>
                    </div>
                </div>
                <div className="adm-incidents-filters">
                    <input type="text" placeholder="Filtrer par ID ou Véhicule..." className="adm-input-search" />
                    <select className="adm-select-filter">
                        <option>Tous les niveaux</option>
                        <option>Level L1</option>
                        <option>Level L2</option>
                        <option>Level L3</option>
                    </select>
                    <button className="adm-btn-primary">Exporter Rapport</button>
                </div>
            </div>

            <div className="adm-incidents-list">
                <h3>Incidents Actifs</h3>
                <div className="adm-incidents-grid">
                    {accidentsGPS.filter(a => a.active).map(acc => (
                        <IncidentCard key={acc.id} incident={acc} />
                    ))}
                </div>

                <h3 className="adm-mt-32">Historique Récent (Resolus/Archivés)</h3>
                <div className="adm-incidents-grid archived">
                    {accidentsGPS.filter(a => !a.active).map(acc => (
                        <IncidentCard key={acc.id} incident={acc} />
                    ))}
                </div>
            </div>
        </div>
    );
}
