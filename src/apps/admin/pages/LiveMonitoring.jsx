import React, { useEffect, useRef } from 'react';
import './LiveMonitoring.css';

export default function LiveMonitoring() {
    const canvasRefs = [useRef(null), useRef(null), useRef(null), useRef(null)];

    useEffect(() => {
        canvasRefs.forEach((ref, idx) => {
            const canvas = ref.current;
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            let frame = 0;

            const draw = () => {
                frame++;
                ctx.clearRect(0, 0, canvas.width, canvas.height);

                // Mock Camera View
                ctx.fillStyle = '#E8EDF2';
                ctx.fillRect(0, 0, canvas.width, canvas.height);

                // Grid
                ctx.strokeStyle = 'rgba(0,0,0,0.05)';
                ctx.beginPath();
                for (let i = 0; i < canvas.width; i += 40) { ctx.moveTo(i, 0); ctx.lineTo(i, canvas.height); }
                for (let i = 0; i < canvas.height; i += 40) { ctx.moveTo(0, i); ctx.lineTo(canvas.width, i); }
                ctx.stroke();

                // Moving vehicles mock
                const vPos = (frame * (1 + idx * 0.5)) % canvas.width;
                ctx.fillStyle = idx === 1 ? 'rgba(229, 57, 53, 0.4)' : 'rgba(0, 102, 255, 0.3)'; // Highlight cam 2 as "incident zone"
                ctx.fillRect(vPos, 100, 40, 20);
                ctx.strokeStyle = idx === 1 ? '#E53935' : '#0066FF';
                ctx.strokeRect(vPos, 100, 40, 20);

                ctx.fillStyle = idx === 1 ? '#B71C1C' : '#1A2340';
                ctx.font = '10px IBM Plex Mono';
                ctx.fillText(`#${100 + idx} ${vPos.toFixed(0)}px/s`, vPos, 95);

                // UI Overlay
                ctx.fillStyle = 'rgba(15, 28, 46, 0.7)';
                ctx.fillRect(10, 10, 120, 22);
                ctx.fillStyle = '#fff';
                ctx.fillText(`CAM-0${idx + 1} | 24.3 FPS`, 18, 25);

                if (idx === 1 && frame % 60 < 30) {
                    ctx.fillStyle = 'rgba(229, 57, 53, 0.8)';
                    ctx.fillRect(canvas.width - 90, 10, 80, 22);
                    ctx.fillStyle = '#fff';
                    ctx.fillText(`🚨 ACCIDENT`, canvas.width - 82, 25);
                }

                requestAnimationFrame(draw);
            };

            const animId = requestAnimationFrame(draw);
            return () => cancelAnimationFrame(animId);
        });
    }, []);

    return (
        <div className="adm-live-monitoring">
            <div className="adm-live-header">
                <div className="adm-live-info">
                    <h2>Grille de Caméras Haute-Définition</h2>
                    <p>Analyse IA multi-flux en temps réel · 4 sources actives</p>
                </div>
                <div className="adm-live-controls">
                    <button className="adm-btn-secondary">Grille 2x2</button>
                    <button className="adm-btn-secondary">Plein écran</button>
                </div>
            </div>

            <div className="adm-live-grid">
                {canvasRefs.map((ref, idx) => (
                    <div key={idx} className={`adm-cam-cell ${idx === 1 ? 'incident' : ''}`}>
                        <canvas ref={ref} width={640} height={360} className="adm-cam-canvas" />
                        <div className="adm-cam-overlay">
                            <span className="adm-cam-tag">#TUN-CAM-{idx + 1}</span>
                            <span className="adm-cam-loc">Zone {String.fromCharCode(65 + idx)}</span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
