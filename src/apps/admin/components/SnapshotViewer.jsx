import React, { useEffect, useRef } from 'react';
import './SnapshotViewer.css';

export default function SnapshotViewer({ incident, width = 640, height = 360 }) {
    const canvasRef = useRef(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');

        // Draw Snapshot logic
        ctx.fillStyle = '#E8EDF2';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Grid
        ctx.strokeStyle = 'rgba(144, 164, 174, 0.2)';
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        for (let i = 0; i < canvas.width; i += 40) { ctx.moveTo(i, 0); ctx.lineTo(i, canvas.height); }
        for (let i = 0; i < canvas.height; i += 40) { ctx.moveTo(0, i); ctx.lineTo(canvas.width, i); }
        ctx.stroke();
        ctx.setLineDash([]);

        // Vehicles
        const vehiclesArr = incident?.vehicles?.split(' ↔ ') || ['#3', '#7'];

        // Vehicle 1
        ctx.fillStyle = 'rgba(26, 115, 232, 0.2)';
        ctx.fillRect(100, 150, 80, 40);
        ctx.strokeStyle = '#1A73E8';
        ctx.lineWidth = 2;
        ctx.strokeRect(100, 150, 80, 40);
        ctx.fillStyle = '#1A73E8';
        ctx.font = 'bold 12px IBM Plex Mono';
        ctx.fillText(`${vehiclesArr[0]} (12px/s)`, 100, 145);

        // Vehicle 2
        ctx.fillStyle = 'rgba(26, 115, 232, 0.2)';
        ctx.fillRect(170, 160, 80, 40);
        ctx.strokeStyle = '#1A73E8';
        ctx.strokeRect(170, 160, 80, 40);
        ctx.fillStyle = '#1A73E8';
        ctx.fillText(`${vehiclesArr[1] || '#7'} (8px/s)`, 170, 155);

        // Accident Marker
        ctx.strokeStyle = '#E53935';
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.arc(165, 175, 50, 0, Math.PI * 2);
        ctx.stroke();
        ctx.fillStyle = 'rgba(229, 57, 53, 0.1)';
        ctx.fill();

        // Overlay Header
        ctx.fillStyle = '#E53935';
        ctx.fillRect(0, 0, canvas.width, 40);
        ctx.fillStyle = '#fff';
        ctx.font = 'bold 14px Plus Jakarta Sans';
        ctx.fillText(`⚠ ACCIDENT CONFIRMÉ — ${incident?.level || 'L2 HYBRIDE'}`, 20, 26);

        // Bottom Meta
        ctx.fillStyle = 'rgba(15, 28, 46, 0.8)';
        ctx.fillRect(0, canvas.height - 30, canvas.width, 30);
        ctx.fillStyle = '#fff';
        ctx.font = '10px IBM Plex Mono';
        ctx.fillText(`15/01/2025 14:32:05 | Score: ${incident?.score || 78} | conf: ${((incident?.conf || 0.62) * 100).toFixed(0)}%`, 20, canvas.height - 11);

    }, [incident]);

    return (
        <div className="adm-snapshot-viewer">
            <canvas ref={canvasRef} width={width} height={height} className="adm-snapshot-canvas" />
        </div>
    );
}
