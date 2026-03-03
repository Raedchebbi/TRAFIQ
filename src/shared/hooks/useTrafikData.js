// ============================================================
// TRAFIQ — Mock Data & useTrafikData Hook
// ============================================================
import { useState, useEffect, useRef } from 'react';

// ── MOCK DATA ────────────────────────────────────────────────

export const ACCIDENTS_GPS = [
    { id: 'pair_3_7', lat: 36.8070, lng: 10.1818, type: 'ACCIDENT_PAIR', severity: 'high', active: true, vehicles: '#3 ↔ #7', score: 78, conf: 0.62, level: 'L2' },
    { id: 'debris_9', lat: 36.8058, lng: 10.1808, type: 'ACCIDENT_DEBRIS', severity: 'medium', active: true, vehicles: '#9', score: 65, conf: 0.55, level: 'L3' },
    { id: 'spec_450', lat: 36.8062, lng: 10.1814, type: 'SPECIALISE', severity: 'high', active: true, vehicles: '#5 ↔ #0', score: 84, conf: 0.88, level: 'L1' },
    { id: 'pair_2_4', lat: 36.8075, lng: 10.1822, type: 'CORRECTED', severity: 'low', active: false, vehicles: '#2 ↔ #4', score: 62, conf: 0.41, level: 'L2' },
];

export const ROUTES_DATA = [
    { id: 'A1', name: 'A1 Tunis - Sfax', status: 'free', extra: 0, color: '#2E7D32', category: 'AUTOROUTES' },
    { id: 'A3', name: 'A3 Tunis - Béja', status: 'slow', extra: 8, color: '#FF8F00', category: 'AUTOROUTES' },
    { id: 'A4', name: 'A4 Tunis - Bizerte', status: 'blocked', extra: null, color: '#B71C1C', category: 'AUTOROUTES', incident: true },
    { id: 'BV1', name: 'Blvd Mohamed V', status: 'free', extra: 0, color: '#2E7D32', category: 'BOULEVARDS' },
    { id: 'AV1', name: 'Avenue Habib Bourguiba', status: 'slow', extra: 6, color: '#FF8F00', category: 'BOULEVARDS' },
    { id: 'AV2', name: 'Avenue de la Liberté', status: 'slow', extra: 4, color: '#FF8F00', category: 'BOULEVARDS' },
    { id: 'RU1', name: 'Rue Ibn Khaldoun', status: 'blocked', extra: null, color: '#B71C1C', category: 'BOULEVARDS', reason: 'travaux' },
];

export const ROAD_POLYLINES = [
    { id: 'A1', coords: [[36.810, 10.175], [36.808, 10.180], [36.806, 10.184]], status: 'free' },
    { id: 'A4', coords: [[36.812, 10.178], [36.809, 10.182], [36.807, 10.186]], status: 'blocked' },
    { id: 'BV1', coords: [[36.807, 10.179], [36.806, 10.182], [36.805, 10.185]], status: 'free' },
    { id: 'AV1', coords: [[36.808, 10.177], [36.807, 10.180], [36.806, 10.183]], status: 'slow' },
];

export const VEHICLE_TRACKS = [
    { id: 3, lat: 36.8071, lng: 10.1817, speed: 12, color: '#1A73E8' },
    { id: 7, lat: 36.8069, lng: 10.1819, speed: 8, color: '#1A73E8' },
    { id: 9, lat: 36.8059, lng: 10.1809, speed: 3, color: '#F57C00' },
    { id: 5, lat: 36.8063, lng: 10.1815, speed: 0, color: '#E53935' },
    { id: 12, lat: 36.8055, lng: 10.1800, speed: 45, color: '#1A73E8' },
];

export const USER_POSITION_MOCK = { lat: 36.8068, lng: 10.1816 };

export const MOCK_EVENTS = [
    { id: 1, time: '14:32:05', type: 'CONFIRM', level: 'L2', pair: '#3↔#7', score: 78, conf: 0.62, dur: 2.1, brake: 3.1, preV: 42.5 },
    { id: 2, time: '14:31:50', type: 'CONFIRM', level: 'L1', pair: '#1↔#5', score: 91, conf: 0.88 },
    { id: 3, time: '14:30:55', type: 'CORRECTION', level: 'L2', pair: '#2↔#4', score: 62, reason: 'reprise_vitesse' },
    { id: 4, time: '14:30:20', type: 'CANDIDAT', level: '?', pair: '#6↔#10', score: 45 },
    { id: 5, time: '14:29:45', type: 'CONFIRM', level: 'L3', pair: '#9', score: 65, conf: 0.55 },
    { id: 6, time: '14:28:10', type: 'CANDIDAT', level: '?', pair: '#11↔#13', score: 38 },
    { id: 7, time: '14:27:30', type: 'CORRECTION', level: 'L1', pair: '#8↔#12', score: 71, reason: 'faux_positif' },
    { id: 8, time: '14:26:00', type: 'CONFIRM', level: 'L2', pair: '#4↔#6', score: 83, conf: 0.74 },
    { id: 9, time: '14:25:15', type: 'CANDIDAT', level: '?', pair: '#14↔#15', score: 52 },
    { id: 10, time: '14:24:00', type: 'CONFIRM', level: 'L1', pair: '#7↔#9', score: 95, conf: 0.91 },
    { id: 11, time: '14:23:10', type: 'CORRECTION', level: 'L3', pair: '#3↔#5', score: 58, reason: 'reprise_vitesse' },
    { id: 12, time: '14:22:45', type: 'CONFIRM', level: 'L2', pair: '#10↔#2', score: 76, conf: 0.67 },
    { id: 13, time: '14:21:30', type: 'CANDIDAT', level: '?', pair: '#16↔#17', score: 41 },
    { id: 14, time: '14:20:00', type: 'CONFIRM', level: 'L1', pair: '#1↔#8', score: 89, conf: 0.85 },
    { id: 15, time: '14:19:10', type: 'CORRECTION', level: 'L2', pair: '#6↔#4', score: 60, reason: 'faux_positif' },
    { id: 16, time: '14:18:30', type: 'CONFIRM', level: 'L3', pair: '#11', score: 70, conf: 0.58 },
    { id: 17, time: '14:17:45', type: 'CANDIDAT', level: '?', pair: '#18↔#20', score: 47 },
    { id: 18, time: '14:16:00', type: 'CONFIRM', level: 'L2', pair: '#2↔#7', score: 80, conf: 0.71 },
    { id: 19, time: '14:15:20', type: 'CORRECTION', level: 'L1', pair: '#5↔#9', score: 55, reason: 'reprise_vitesse' },
    { id: 20, time: '14:14:00', type: 'CONFIRM', level: 'L1', pair: '#3↔#12', score: 92, conf: 0.90 },
];

export const MOCK_MEMORY = [
    { id: 1, type: 'accident', scenario: 'A1↔A2 brake+decel', outcome: 'confirmed', score: 91 },
    { id: 2, type: 'faux_positif', scenario: 'B3↔B4 lane_change', outcome: 'corrected', score: 62 },
    { id: 3, type: 'accident', scenario: 'C5↔C6 sudden_stop', outcome: 'confirmed', score: 88 },
    { id: 4, type: 'faux_positif', scenario: 'D7↔D8 parking', outcome: 'corrected', score: 58 },
    { id: 5, type: 'accident', scenario: 'E9↔E10 rear_impact', outcome: 'confirmed', score: 85 },
    { id: 6, type: 'accident', scenario: 'F11 debris_detected', outcome: 'confirmed', score: 70 },
    { id: 7, type: 'faux_positif', scenario: 'G12↔G13 slow_zone', outcome: 'corrected', score: 55 },
    { id: 8, type: 'accident', scenario: 'H14↔H15 side_impact', outcome: 'confirmed', score: 82 },
    { id: 9, type: 'accident', scenario: 'I16↔I17 chain', outcome: 'confirmed', score: 79 },
    { id: 10, type: 'faux_positif', scenario: 'J18↔J19 merge', outcome: 'corrected', score: 61 },
    { id: 11, type: 'accident', scenario: 'K20↔K21 head_on', outcome: 'confirmed', score: 94 },
    { id: 12, type: 'faux_positif', scenario: 'L22↔L23 stall', outcome: 'corrected', score: 48 },
];

// ── HOOK ────────────────────────────────────────────────────────

export function useTrafikData() {
    const [stats, setStats] = useState({
        vehicles: 247,
        accidents: 3,
        blocked: 1,
        corrections: 2,
        confidence: 74,
        fps: 24.3,
        precision: 87,
        scenarios: 12,
        falsePositivesAvoided: 2,
        levelDist: { L1: 33, L2: 42, L3: 25 },
        pipeline: {
            yolo: { ok: true, value: '247 objets · 24ms' },
            tracking: { ok: true, value: '183 véhicules actifs' },
            speed: { ok: true, value: 'Médiane : 38px/s' },
            pairs: { ok: true, value: '7 paires en contact' },
            deliber: { ok: true, value: '3 candidats en analyse', running: true },
            bestpt: { ok: true, value: 'Conf. moy : 0.71' },
            autocorr: { ok: true, value: '2 corrections appliquées' },
        }
    });

    const tickRef = useRef(0);

    useEffect(() => {
        const interval = setInterval(() => {
            tickRef.current += 1;
            const t = tickRef.current;
            setStats(prev => ({
                ...prev,
                vehicles: 247 + Math.floor(Math.sin(t * 0.3) * 8),
                fps: parseFloat((24.3 + Math.sin(t * 0.5) * 1.5).toFixed(1)),
                confidence: Math.min(99, Math.max(60, prev.confidence + (Math.random() - 0.5) * 2)) | 0,
                pipeline: {
                    ...prev.pipeline,
                    deliber: { ok: true, value: `${2 + (t % 3)} candidats en analyse`, running: true },
                    bestpt: { ok: true, value: `Conf. moy : ${(0.68 + Math.sin(t * 0.4) * 0.06).toFixed(2)}` },
                }
            }));
        }, 2000);
        return () => clearInterval(interval);
    }, []);

    return {
        events: MOCK_EVENTS,
        memory: MOCK_MEMORY,
        stats,
        accidentsGPS: ACCIDENTS_GPS,
        vehicleTracks: VEHICLE_TRACKS,
        routesData: ROUTES_DATA,
        polylines: ROAD_POLYLINES,
    };
}
