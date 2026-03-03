import React from 'react';
import './StatCard.css';

export default function StatCard({ title, value, trend, trendPositive, urgent, gauge }) {
    return (
        <div className={`adm-stat-card ${urgent ? 'urgent' : ''}`}>
            <div className="adm-stat-title">{title}</div>
            <div className="adm-stat-value-row">
                <div className="adm-stat-value">{value}</div>
                {gauge !== undefined && (
                    <div className="adm-stat-gauge">
                        <svg viewBox="0 0 36 36" className="adm-circular-chart">
                            <path className="circle-bg"
                                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                            />
                            <path className="circle"
                                strokeDasharray={`${gauge}, 100`}
                                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                            />
                        </svg>
                    </div>
                )}
            </div>
            {trend && (
                <div className={`adm-stat-trend ${trendPositive ? 'positive' : ''}`}>
                    {trendPositive ? '↑' : ''} {trend}
                </div>
            )}
        </div>
    );
}
