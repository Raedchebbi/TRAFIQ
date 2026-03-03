import React from 'react';
import { useTrafik } from '../../../shared/context/TrafikContext';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell, LineChart, Line } from 'recharts';
import './Analytics.jsx.css';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

export default function Analytics() {
    const { events, stats } = useTrafik();

    // Mock data for charts
    const timelineData = [
        { name: '08h', v: 45, a: 1 },
        { name: '10h', v: 120, a: 0 },
        { name: '12h', v: 180, a: 2 },
        { name: '14h', v: 150, a: 1 },
        { name: '16h', v: 210, a: 3 },
        { name: '18h', v: 247, a: 2 },
    ];

    const pieData = [
        { name: 'Level L1', value: stats.levelDist.L1 },
        { name: 'Level L2', value: stats.levelDist.L2 },
        { name: 'Level L3', value: stats.levelDist.L3 },
    ];

    return (
        <div className="adm-analytics-page">
            <div className="adm-analytics-header">
                <h2>Statistiques & Analytics</h2>
                <div className="adm-analytics-range">Dernières 24 heures</div>
            </div>

            <div className="adm-analytics-top-grid">
                <div className="adm-kpi-card">
                    <span>Total événements</span>
                    <strong>1,429</strong>
                </div>
                <div className="adm-kpi-card">
                    <span>Taux précision</span>
                    <strong>{stats.precision}%</strong>
                </div>
                <div className="adm-kpi-card">
                    <span>Nb accidents/jour</span>
                    <strong>8.2</strong>
                </div>
                <div className="adm-kpi-card">
                    <span>Temps moyen réponse</span>
                    <strong>4.5s</strong>
                </div>
            </div>

            <div className="adm-analytics-main-grid">
                <div className="adm-chart-card">
                    <div className="adm-chart-title">Évolution du trafic & accidents</div>
                    <div className="adm-chart-h">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={timelineData}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E0E4E8" />
                                <XAxis dataKey="name" fontSize={10} axisLine={false} tickLine={false} />
                                <YAxis fontSize={10} axisLine={false} tickLine={false} />
                                <Tooltip />
                                <Area type="monotone" dataKey="v" stroke="#0066FF" fill="#0066FF" fillOpacity={0.1} />
                                <Area type="monotone" dataKey="a" stroke="#E53935" fill="#E53935" fillOpacity={0.1} />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                <div className="adm-chart-card">
                    <div className="adm-chart-title">Répartition niveaux décision</div>
                    <div className="adm-chart-h">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value">
                                    {pieData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>
        </div>
    );
}
