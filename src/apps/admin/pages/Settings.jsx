import React from 'react';
import './Settings.css';

export default function Settings() {
    return (
        <div className="adm-settings-page">
            <div className="adm-settings-header">
                <h2>Paramètres Système</h2>
            </div>

            <div className="adm-settings-content">
                <aside className="adm-settings-sidebar">
                    <button className="adm-set-nav active">Système</button>
                    <button className="adm-set-nav">Caméras</button>
                    <button className="adm-set-nav">Zones & Routes</button>
                    <button className="adm-set-nav">Notifications</button>
                    <button className="adm-set-nav">Compte</button>
                </aside>

                <div className="adm-settings-panel">
                    <section className="adm-set-section">
                        <h3>Configuration du rayon d'alerte</h3>
                        <p>Définit dans quel périmètre les conducteurs reçoivent une notification d'accident.</p>
                        <div className="adm-set-row">
                            <label>Rayon actuel :</label>
                            <div className="adm-input-group">
                                <input type="number" defaultValue={30} className="adm-input-small" />
                                <span>mètres</span>
                            </div>
                            <button className="adm-btn-primary">Modifier</button>
                        </div>
                    </section>

                    <section className="adm-set-section">
                        <h3>Notifications automatiques</h3>
                        <div className="adm-set-row jc-sb">
                            <div>
                                <div className="fw-700">Notifications actives</div>
                                <div className="fs-08 c-gray">Envoyer automatiquement aux conducteurs proches.</div>
                            </div>
                            <div className="adm-toggle active" />
                        </div>
                    </section>

                    <section className="adm-set-section">
                        <h3>Journal des alertes envoyées</h3>
                        <div className="adm-set-log">
                            <div className="adm-log-line">14:32:10 — 3 conducteurs alertés (rayon 30m, accident #3↔#7)</div>
                            <div className="adm-log-line">14:28:45 — 1 conducteur alerté (rayon 30m, accident #9)</div>
                        </div>
                    </section>
                </div>
            </div>
        </div>
    );
}
