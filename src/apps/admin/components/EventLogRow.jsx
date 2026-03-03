import React from 'react';
import './EventLogRow.css';

export default function EventLogRow({ event }) {
    const { time, type, level, pair, score, conf, reason } = event;

    const typeClass = type.toLowerCase();

    return (
        <div className={`adm-event-row ${typeClass}`}>
            <div className="adm-event-time">{time}</div>
            <div className="adm-event-tag">{type}</div>
            <div className="adm-event-details">
                {pair && <span className="adm-event-pair">{pair}</span>}
                {level && <span className="adm-event-level">Level {level}</span>}
                {reason && <span className="adm-event-reason">({reason})</span>}
            </div>
            <div className="adm-event-metrics">
                {score && <div className="adm-metric-item">sc: {score}</div>}
                {conf && <div className="adm-metric-item">cf: {(conf * 100).toFixed(0)}%</div>}
            </div>
        </div>
    );
}
