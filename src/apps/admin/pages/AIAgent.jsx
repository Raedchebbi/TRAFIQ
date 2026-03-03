import React from 'react';
import { useTrafik } from '../../../shared/context/TrafikContext';
import './AIAgent.css';

export default function AIAgent() {
    const { stats, events } = useTrafik();

    return (
        <div className="adm-ai-agent-page">
            <div className="adm-ai-header">
                <h2>Agent IA — Monitoring Décisionnel</h2>
                <p>Surveillance du moteur d'analyse en temps réel (best.pt v9.1)</p>
            </div>

            <div className="adm-ai-grid">
                {/* Column 1: Pipeline */}
                <div className="adm-ai-card pipeline">
                    <div className="adm-ai-card-title">🤖 Pipeline de décision</div>
                    <div className="adm-pipeline-steps">
                        {Object.entries(stats.pipeline).map(([key, data]) => (
                            <div key={key} className={`adm-step-item ${data.running ? 'running' : ''}`}>
                                <div className="adm-step-icon">{data.ok ? '✅' : '🔄'}</div>
                                <div className="adm-step-info">
                                    <div className="adm-step-name">{key.toUpperCase()}</div>
                                    <div className="adm-step-val">{data.value}</div>
                                </div>
                                {data.running && <div className="adm-step-spinner" />}
                            </div>
                        ))}
                    </div>
                </div>

                {/* Column 2: Log */}
                <div className="adm-ai-card logs">
                    <div className="adm-ai-card-title">📋 Journal de décisions</div>
                    <div className="adm-ai-logs-list">
                        {events.slice(0, 15).map((ev, i) => (
                            <div key={i} className={`adm-ai-log-entry ${ev.type.toLowerCase()}`}>
                                <div className="adm-log-time">{ev.time}</div>
                                <div className="adm-log-main">
                                    <span className="adm-log-tag">[{ev.type} {ev.level || ''}]</span>
                                    <span className="adm-log-pair">{ev.pair}</span>
                                </div>
                                <div className="adm-log-meta">
                                    score={ev.score} {ev.conf && `conf=${ev.conf}`} {ev.reason && `rev=${ev.reason}`}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Column 3: Stats */}
                <div className="adm-ai-card stats">
                    <div className="adm-ai-card-title">📊 Performance du moteur</div>
                    <div className="adm-ai-metrics">
                        <div className="adm-metric-row">
                            <span>FPS traitement :</span>
                            <strong>{stats.fps} fps</strong>
                        </div>
                        <div className="adm-metric-row">
                            <span>Précision session :</span>
                            <strong>{stats.precision}%</strong>
                        </div>
                        <div className="adm-metric-row">
                            <span>Accidents confirmés :</span>
                            <strong>{stats.accidents}</strong>
                        </div>
                        <div className="adm-metric-row">
                            <span>Faux positifs évités :</span>
                            <strong>{stats.falsePositivesAvoided}</strong>
                        </div>
                        <div className="adm-metric-row">
                            <span>Scénarios mémorisés :</span>
                            <strong>{stats.scenarios}/300</strong>
                        </div>

                        <div className="adm-ai-dist">
                            <div className="adm-dist-title">Répartition niveaux :</div>
                            {Object.entries(stats.levelDist).map(([lvl, val]) => (
                                <div key={lvl} className="adm-dist-row">
                                    <span className="adm-dist-lvl">{lvl}</span>
                                    <div className="adm-dist-bar-bg">
                                        <div className="adm-dist-bar" style={{ width: `${val}%` }} />
                                    </div>
                                    <span className="adm-dist-val">{val}%</span>
                                </div>
                            ))}
                        </div>

                        <div className="adm-ai-conf">
                            <div className="adm-dist-title">Conf. best.pt moy. :</div>
                            <div className="adm-conf-big-bar">
                                <div className="adm-conf-progress" style={{ width: `${stats.confidence}%` }} />
                                <span className="adm-conf-text">{stats.confidence}%</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
