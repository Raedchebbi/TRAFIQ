import React, { useState, useEffect } from 'react';
import { useNotifications } from '../../../shared/hooks/useNotifications';
import './ProximityAlert.css';

export default function ProximityAlert({ accidents }) {
    const [dismissed, setDismissed] = useState([]);
    const [notifBanner, setNotifBanner] = useState(false);
    const { permission, requestPermission, sendNotification } = useNotifications();

    const visible = accidents.filter(a => !dismissed.includes(a.id));

    useEffect(() => {
        if (permission === 'default') setNotifBanner(true);
    }, [permission]);

    useEffect(() => {
        visible.forEach(a => {
            sendNotification(
                a.id,
                '⚠️ TRAFIQ — Accident proche',
                `Un accident a été détecté à ${a.distance}m sur votre route. Des itinéraires alternatifs sont disponibles.`
            );
        });
    }, [visible.length]);

    if (visible.length === 0 && !notifBanner) return null;

    return (
        <>
            {/* Notification permission banner */}
            {notifBanner && (
                <div className="notif-permission-banner">
                    <span>🔔 Activez les notifications pour recevoir des alertes d'accidents en temps réel.</span>
                    <div className="notif-banner-actions">
                        <button onClick={() => { requestPermission(); setNotifBanner(false); }}>
                            Activer les notifications
                        </button>
                        <button className="later-btn" onClick={() => setNotifBanner(false)}>Plus tard</button>
                    </div>
                </div>
            )}

            {/* Toast alerts for each nearby accident */}
            <div className="proximity-alerts-stack">
                {visible.slice(0, 2).map(accident => (
                    <div key={accident.id} className="proximity-toast">
                        <div className="proximity-toast-icon">🚨</div>
                        <div className="proximity-toast-body">
                            <div className="proximity-toast-title">ACCIDENT DÉTECTÉ SUR VOTRE ROUTE</div>
                            <div className="proximity-toast-sub">
                                À environ <strong>{accident.distance} mètres</strong> devant vous
                            </div>
                            <a href="/plan" className="proximity-toast-action">
                                Voir itinéraires alternatifs →
                            </a>
                        </div>
                        <button className="proximity-toast-close" onClick={() => setDismissed(d => [...d, accident.id])}>✕</button>
                    </div>
                ))}
            </div>
        </>
    );
}
