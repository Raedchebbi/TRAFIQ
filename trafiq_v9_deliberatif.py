"""
╔══════════════════════════════════════════════════════════════════════╗
║         TRAFIQ AI ENGINE  —  Version 9.0  DELIBERATIVE              ║
║         Système de décision réfléchi + auto-correction              ║
║         Validation par modèle spécialisé best.pt                    ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import cv2
import numpy as np
from ultralytics import YOLO
import supervision as sv
import time
import json
import logging
import math
from collections import deque, defaultdict
from datetime import datetime
from statistics import median

# ══════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════════

VIDEO_PATH   = "videos/v10.mov"
OUTPUT_LOG   = "trafiq_events.json"
SAVE_VIDEO   = True
OUTPUT_VIDEO = "output_annotated.mp4"

COUNT_LINES = [
    {"y": 400, "label": "Ligne A", "color": (0, 0, 255)},
    {"y": 600, "label": "Ligne B", "color": (255, 165, 0)},
]

HISTORY_FRAMES = 12
TRAJ_FRAMES    = 35

DEPTH_ZONES = [
    (0,    220,  0.45),
    (220,  420,  0.62),
    (420,  620,  0.82),
    (620,  9999, 1.00),
]

STOP_SPEED   = 5
MOVING_SPEED = 20

# ── Statique
STATIC_RAW_MAX        = 8.0
STATIC_MEDIAN_MAX     = 3.5
STATIC_MEDIAN_WINDOW  = 15
STATIC_CONFIRM_S      = 8.0
STATIC_MIN_FRAMES     = 60

TRACKER_TTL_S  = 4.0
GRID_CELL_SIZE = 200

# ══════════════════════════════════════════════════════════════════
#  [A] PAIRE
# ══════════════════════════════════════════════════════════════════

PAIR_SCORE_BASE        = 65
PAIR_SCORE_BRAKE_BONUS = 55

W_BRAKE         = 30
W_FAST_PRE      = 25
W_BOTH_STOPPED  = 20
W_CONVERGENCE   = 10
W_IOU           = 10
W_DURATION      = 10

OVERLAP_IOU_MIN       = 0.10
PROXIMITY_PX          = 55
BRAKE_RATIO_MIN       = 2.5
BRAKE_SHORT           = 3
BRAKE_LONG            = 20
PRE_FRAMES_START      = 10
PRE_FRAMES_END        = 40
PRE_MIN_V             = 18
CRASH_CONFIRM_S       = 1.0
CONVERGENCE_ANGLE_MIN = 75
SIZE_RATIO_MAX        = 2.8
SEP_WINDOW_S          = 3.5
SEP_RATIO_MIN         = 0.55
BLACKLIST_DURATION_S  = 60.0

# ══════════════════════════════════════════════════════════════════
#  [B] DEBRIS
# ══════════════════════════════════════════════════════════════════

DEBRIS_RATIO_MIN     = 2.0
DEBRIS_AREA_MIN      = 15000
DEBRIS_AREA_MAX      = 85000
DEBRIS_SPEED_RAW_MAX = 3.0
DEBRIS_SPEED_MED_MAX = 3.5
DEBRIS_CONFIRM_S     = 4.0

# ══════════════════════════════════════════════════════════════════
#  [C] BOÎTE FUSIONNÉE
# ══════════════════════════════════════════════════════════════════

FUSED_RATIO_MIN  = 1.85
FUSED_AREA_MIN   = 15000
FUSED_AREA_MAX   = 130000
FUSED_CONFIRM_S  = 0.8
FUSED_PRE_V_MIN  = 16

# ══════════════════════════════════════════════════════════════════
#  MOTEUR DE DÉCISION RÉFLÉCHI — PARAMÈTRES
# ══════════════════════════════════════════════════════════════════

# Délibération : nombre de frames consécutives avant confirmation finale
DELIBERATION_FRAMES      = 8      # doit être confirmé N fois de suite
DELIBERATION_TIMEOUT_S   = 5.0    # fenêtre max de délibération

# Validation croisée best.pt
SPECIALIST_CONF_MIN      = 0.40   # seuil conf spécialiste pour valider
SPECIALIST_VETO_CONF     = 0.20   # en-dessous → veto (annule la décision)
SPECIALIST_REGION_IOU    = 0.15   # IoU région véhicule vs détection spécialiste

# Auto-correction
CORRECTION_WINDOW_S      = 8.0    # fenêtre de révision après confirmation
CORRECTION_SEP_RATIO     = 0.60   # séparation trop rapide → faux positif
CORRECTION_SPEED_RESUME  = 25.0   # reprise vitesse → faux positif
CORRECTION_SPECIALIST_S  = 4.0    # si spécialiste ne confirme plus N secondes → révision

# Mémoire de scénarios appris
SCENARIO_MEMORY_SIZE     = 200    # nb scénarios mémorisés
SCENARIO_MATCH_THRESHOLD = 0.72   # similarité min pour réutiliser un scénario
SCENARIO_BOOST           = 15     # bonus score si scénario similaire trouvé

# ══════════════════════════════════════════════════════════════════
#  LOGGING
# ══════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("trafiq.log"), logging.StreamHandler()]
)
log = logging.getLogger("TRAFIQ")


# ══════════════════════════════════════════════════════════════════
#  CLASSES UTILITAIRES
# ══════════════════════════════════════════════════════════════════

class AdaptiveEMA:
    def __init__(self):
        self.v = None
        self.p = None

    def update(self, raw: float) -> float:
        if self.v is None:
            self.v = raw; self.p = raw; return raw
        d = abs(raw - self.v)
        a = min(0.65, 0.15 + d / 160.0)
        self.p = self.v
        self.v = a * raw + (1 - a) * self.v
        return self.v


class VehicleTrack:
    def __init__(self, tid: int):
        self.tid           = tid
        self.positions     = deque(maxlen=150)
        self.speed_cal     = deque(maxlen=80)
        self.speed_raw_buf = deque(maxlen=80)
        self.ema           = AdaptiveEMA()
        self.speed         = 0.0
        self.speed_raw     = 0.0
        self.box           = None
        self.center        = None
        self.last_seen     = time.time()
        self.frames_seen   = 0
        self.direction_vec = None
        self.direction_str = None
        self.counted_lines : set = set()
        self.static_since  = None
        self.is_static     = False
        self.debris_since  = None
        self.is_debris     = False

    def speed_median(self, n=15):
        h = list(self.speed_cal)[-n:]
        return median(h) if h else 0.0

    def raw_median(self, n=10):
        h = list(self.speed_raw_buf)[-n:]
        return median(h) if h else 0.0

    def max_speed_window(self, a, b):
        h  = list(self.speed_cal)
        n  = len(h)
        i0 = max(0, n - 1 - b)
        i1 = max(0, n - 1 - a)
        w  = h[i0:i1+1]
        return max(w) if w else 0.0

    def braking_ratio(self):
        h = list(self.speed_cal)
        if len(h) < BRAKE_LONG:
            return 0.0
        d_s = max(0.0, h[-BRAKE_SHORT] - h[-1]) / BRAKE_SHORT
        d_l = max(0.0, h[-BRAKE_LONG]  - h[-1]) / BRAKE_LONG
        return d_s / d_l if d_l > 0.3 else 0.0

    def box_area(self):
        if self.box is None: return 1.0
        return max(1.0, (self.box[2]-self.box[0]) * (self.box[3]-self.box[1]))

    def box_size(self):
        if self.box is None: return 1.0
        return max(1.0, ((self.box[2]-self.box[0]) + (self.box[3]-self.box[1])) / 2.0)

    def update_position(self, box, now):
        x1,y1,x2,y2 = map(int, box)
        cx,cy = (x1+x2)//2, (y1+y2)//2
        self.box    = (x1,y1,x2,y2)
        self.center = (cx,cy)
        self.last_seen = now
        self.frames_seen += 1
        self.positions.append((cx,cy,now))

    def compute_speed(self, history):
        if len(self.positions) < history:
            return self.speed
        cx_n,cy_n,t_n = self.positions[-1]
        cx_o,cy_o,t_o = self.positions[-history]
        dt = t_n - t_o
        if dt <= 0: return self.speed
        raw = np.hypot(cx_n-cx_o, cy_n-cy_o) / dt
        cal = raw * depth_factor(cy_n)
        self.speed     = self.ema.update(cal)
        self.speed_raw = raw
        self.speed_cal.append(self.speed)
        self.speed_raw_buf.append(raw)
        dy,dx = cy_n-cy_o, cx_n-cx_o
        nm = math.hypot(dx, dy)
        if nm > 1:
            self.direction_vec = (dx/nm, dy/nm)
        self.direction_str = (
            ("bas" if dy > 0 else "haut") if abs(dy) >= abs(dx)
            else ("droite" if dx > 0 else "gauche")
        )
        return self.speed

    def trajectory_vector(self, n=30):
        if len(self.positions) < 4: return None
        pts = list(self.positions)[-min(n, len(self.positions)):]
        dx  = pts[-1][0] - pts[0][0]
        dy  = pts[-1][1] - pts[0][1]
        nm  = math.hypot(dx, dy)
        if nm < 4: return None
        return (dx/nm, dy/nm)

    def is_alive(self, now):
        return (now - self.last_seen) <= TRACKER_TTL_S

    def snapshot(self):
        """Résumé compact pour la mémoire de scénarios."""
        return {
            "speed":      round(self.speed, 1),
            "braking":    round(self.braking_ratio(), 2),
            "direction":  self.direction_str or "?",
            "area":       round(self.box_area()),
        }


class PairState:
    def __init__(self, now, dist, avg_size):
        self.since    = now
        self.avg_size = max(1, avg_size)
        self.max_score = 0
        self.dist_min  = dist
        self.dist_log  = deque(maxlen=300)
        self.dist_log.append((now, dist / self.avg_size))
        self.separated = False
        self.has_brake = False

    @property
    def duration(self):
        if not self.dist_log: return 0.0
        return self.dist_log[-1][0] - self.since

    def update(self, now, dist, score, has_brake):
        nd = dist / self.avg_size
        self.dist_log.append((now, nd))
        self.dist_min  = min(self.dist_min, dist)
        self.max_score = max(self.max_score, score)
        if has_brake:
            self.has_brake = True
        nm = self.dist_min / self.avg_size
        if nd - nm > SEP_RATIO_MIN:
            for t_o, d_o in self.dist_log:
                if now - t_o <= SEP_WINDOW_S:
                    if nd - d_o > SEP_RATIO_MIN * 0.65:
                        self.separated = True
                        break


# ══════════════════════════════════════════════════════════════════
#  MOTEUR DE DÉCISION RÉFLÉCHI
# ══════════════════════════════════════════════════════════════════

class DecisionEngine:
    """
    Gère la délibération, la validation croisée et l'auto-correction
    pour chaque candidat accident.
    """

    def __init__(self):
        # candidats en délibération  → key: pair/tid, value: dict état
        self.pending    : dict = {}
        # décisions confirmées        → key: pair/tid, value: dict état
        self.confirmed  : dict = {}
        # mémoire de scénarios appris
        self.scenario_memory : deque = deque(maxlen=SCENARIO_MEMORY_SIZE)
        # historique des corrections (pour log)
        self.corrections : list = []

    # ──────────────────────────────────────────────────────────────
    #  SOUMISSION D'UN CANDIDAT
    # ──────────────────────────────────────────────────────────────
    def submit(self, key, score: int, evidence: dict, now: float,
               t1: VehicleTrack = None, t2: VehicleTrack = None):
        """
        Soumet un candidat accident.
        Le système ne confirme PAS immédiatement :
        il ouvre une fenêtre de délibération.
        """
        if key in self.confirmed:
            return  # déjà confirmé

        if key not in self.pending:
            self.pending[key] = {
                "score":         score,
                "evidence":      evidence,
                "since":         now,
                "confirmations": 1,
                "score_history": [score],
                "specialist_ok": False,
                "specialist_last": None,
                "snap1":         t1.snapshot() if t1 else None,
                "snap2":         t2.snapshot() if t2 else None,
            }
        else:
            p = self.pending[key]
            p["confirmations"] += 1
            p["score_history"].append(score)
            p["score"] = max(p["score"], score)

            # Délibération expirée sans confirmation suffisante → abandon
            if now - p["since"] > DELIBERATION_TIMEOUT_S:
                del self.pending[key]
                log.debug(f"[DELIBERATION] {key} abandonné (timeout)")
                return

            # Vérification : le score reste-t-il cohérent ?
            avg_score = sum(p["score_history"]) / len(p["score_history"])
            if avg_score < 30:
                del self.pending[key]
                log.debug(f"[DELIBERATION] {key} abandonné (score instable)")
                return

            # ── Boost si scénario similaire mémorisé
            boost = self._scenario_boost(p["snap1"], p["snap2"])
            effective_score = min(100, p["score"] + boost)

            # ── Confirmation finale si critères atteints
            if (p["confirmations"] >= DELIBERATION_FRAMES
                    and effective_score >= 55
                    and p["specialist_ok"]):
                self._confirm(key, effective_score, p["evidence"],
                              p["snap1"], p["snap2"], now)

    # ──────────────────────────────────────────────────────────────
    #  VALIDATION PAR LE SPÉCIALISTE best.pt
    # ──────────────────────────────────────────────────────────────
    def validate_specialist(self, key, specialist_conf: float, now: float):
        """
        Met à jour le statut de validation du spécialiste pour un candidat.
        """
        if key in self.pending:
            p = self.pending[key]
            if specialist_conf >= SPECIALIST_CONF_MIN:
                p["specialist_ok"]   = True
                p["specialist_last"] = now
            elif specialist_conf < SPECIALIST_VETO_CONF:
                # VETO — le spécialiste est sûr que ce n'est PAS un accident
                log.info(f"[VETO SPECIALISTE] {key} — conf={specialist_conf:.2f}")
                del self.pending[key]

        # Pour les décisions déjà confirmées → surveiller pour correction
        if key in self.confirmed:
            self.confirmed[key]["specialist_last"] = now
            self.confirmed[key]["specialist_conf"] = specialist_conf

    # ──────────────────────────────────────────────────────────────
    #  AUTO-CORRECTION
    # ──────────────────────────────────────────────────────────────
    def check_correction(self, key, now: float,
                         t1: VehicleTrack = None,
                         t2: VehicleTrack = None,
                         dist: float = None):
        """
        Vérifie si une décision confirmée doit être annulée (faux positif).
        Trois triggers de correction :
          1. Séparation trop rapide des véhicules → faux contact
          2. Reprise de vitesse normale → pas d'accident réel
          3. Le spécialiste n'a pas confirmé depuis trop longtemps
        """
        if key not in self.confirmed:
            return

        c        = self.confirmed[key]
        elapsed  = now - c["confirmed_at"]
        if elapsed > CORRECTION_WINDOW_S:
            return  # fenêtre de révision fermée

        reason = None

        # Trigger 1 — séparation trop rapide
        if dist is not None and dist > c.get("dist_at_confirm", 0) * (1 + CORRECTION_SEP_RATIO):
            reason = "separation_rapide"

        # Trigger 2 — reprise de vitesse
        if t1 and t2:
            v_max = max(t1.speed, t2.speed)
            if v_max > CORRECTION_SPEED_RESUME:
                reason = "reprise_vitesse"

        # Trigger 3 — spécialiste silencieux
        spec_last = c.get("specialist_last")
        if spec_last and (now - spec_last) > CORRECTION_SPECIALIST_S:
            spec_conf = c.get("specialist_conf", 1.0)
            if spec_conf < SPECIALIST_CONF_MIN:
                reason = "specialiste_desaccord"

        if reason:
            self._correct(key, reason, now)

    # ──────────────────────────────────────────────────────────────
    #  MÉTHODES INTERNES
    # ──────────────────────────────────────────────────────────────
    def _confirm(self, key, score, evidence, snap1, snap2, now):
        self.confirmed[key] = {
            "score":          score,
            "evidence":       evidence,
            "confirmed_at":   now,
            "specialist_last": None,
            "specialist_conf": 0.0,
            "dist_at_confirm": 0,
        }
        # Mémoriser le scénario
        self._memorize(snap1, snap2, score, outcome="accident")
        log.info(f"[CONFIRM] {key} score={score} preuves={evidence}")
        del self.pending[key]

    def _correct(self, key, reason, now):
        if key not in self.confirmed:
            return
        c = self.confirmed.pop(key)
        self.corrections.append({
            "key":    str(key),
            "reason": reason,
            "at":     now,
            "score":  c["score"],
        })
        # Mémoriser comme faux positif
        self._memorize(c.get("snap1"), c.get("snap2"),
                       c["score"], outcome="faux_positif")
        log.info(f"[CORRECTION] {key} annulé — raison: {reason}")

    def _memorize(self, snap1, snap2, score, outcome):
        if snap1 is None and snap2 is None:
            return
        self.scenario_memory.append({
            "snap1":   snap1,
            "snap2":   snap2,
            "score":   score,
            "outcome": outcome,
        })

    def _scenario_boost(self, snap1, snap2) -> int:
        """
        Cherche dans la mémoire un scénario similaire déjà confirmé.
        Retourne un bonus de score si trouvé.
        """
        if not snap1 and not snap2:
            return 0
        best_sim = 0.0
        for mem in self.scenario_memory:
            if mem["outcome"] != "accident":
                continue
            sim = self._similarity(snap1, mem.get("snap1")) * 0.5 \
                + self._similarity(snap2, mem.get("snap2")) * 0.5
            if sim > best_sim:
                best_sim = sim
        if best_sim >= SCENARIO_MATCH_THRESHOLD:
            log.debug(f"[SCENARIO] scénario similaire trouvé sim={best_sim:.2f}")
            return SCENARIO_BOOST
        return 0

    @staticmethod
    def _similarity(s1: dict, s2: dict) -> float:
        """Similarité entre deux snapshots de véhicule (0.0 → 1.0)."""
        if s1 is None or s2 is None:
            return 0.0
        score = 0.0
        # Vitesse
        v_diff = abs(s1.get("speed", 0) - s2.get("speed", 0))
        score += max(0.0, 1.0 - v_diff / 50.0) * 0.35
        # Freinage
        b_diff = abs(s1.get("braking", 0) - s2.get("braking", 0))
        score += max(0.0, 1.0 - b_diff / 3.0) * 0.30
        # Direction identique
        if s1.get("direction") == s2.get("direction"):
            score += 0.20
        # Taille similaire
        a1 = s1.get("area", 1)
        a2 = s2.get("area", 1)
        ratio = min(a1, a2) / max(a1, a2) if max(a1, a2) > 0 else 0
        score += ratio * 0.15
        return score

    # ──────────────────────────────────────────────────────────────
    #  ACCESSEURS
    # ──────────────────────────────────────────────────────────────
    def is_confirmed(self, key) -> bool:
        return key in self.confirmed

    def get_score(self, key) -> int:
        if key in self.confirmed:
            return self.confirmed[key]["score"]
        return 0

    def is_pending(self, key) -> bool:
        return key in self.pending

    def pending_progress(self, key) -> float:
        """Retourne la progression (0→1) de la délibération."""
        if key not in self.pending:
            return 0.0
        return min(1.0, self.pending[key]["confirmations"] / DELIBERATION_FRAMES)

    def save_memory(self, path="trafiq_memory.json"):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(list(self.scenario_memory), f, indent=2, ensure_ascii=False)

    def load_memory(self, path="trafiq_memory.json"):
        if not os.path.exists(path):
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                self.scenario_memory.append(item)
            log.info(f"[MEMORY] {len(data)} scénarios chargés depuis {path}")
        except Exception as e:
            log.warning(f"[MEMORY] Erreur chargement : {e}")


# ══════════════════════════════════════════════════════════════════
#  FONCTIONS UTILITAIRES
# ══════════════════════════════════════════════════════════════════

def depth_factor(cy: int) -> float:
    for y0, y1, f in DEPTH_ZONES:
        if y0 <= cy < y1:
            return f
    return 1.0


def box_iou(a, b) -> float:
    xA,yA = max(a[0],b[0]), max(a[1],b[1])
    xB,yB = min(a[2],b[2]), min(a[3],b[3])
    inter = max(0, xB-xA) * max(0, yB-yA)
    if inter == 0: return 0.0
    return inter / max(1, (a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter)


def cdist(t1: VehicleTrack, t2: VehicleTrack) -> float:
    if t1.center is None or t2.center is None:
        return float("inf")
    return math.hypot(t1.center[0]-t2.center[0], t1.center[1]-t2.center[1])


def angle_between(v1, v2) -> float:
    if v1 is None or v2 is None: return 0.0
    dot = max(-1.0, min(1.0, v1[0]*v2[0]+v1[1]*v2[1]))
    return math.degrees(math.acos(dot))


def converging(t1, t2) -> bool:
    return angle_between(
        t1.trajectory_vector(TRAJ_FRAMES),
        t2.trajectory_vector(TRAJ_FRAMES)
    ) >= CONVERGENCE_ANGLE_MIN


def size_mismatch(t1, t2) -> bool:
    a1 = t1.box_area(); a2 = t2.box_area()
    big, small = max(a1, a2), min(a1, a2)
    return (big / small) > SIZE_RATIO_MAX


def compute_pair_score(t1, t2, iou, duration) -> tuple:
    s, d = 0, {}
    has_brake = False
    mismatch  = size_mismatch(t1, t2)

    br = max(t1.braking_ratio(), t2.braking_ratio())
    if br > BRAKE_RATIO_MIN:
        s += W_BRAKE; d["brake"] = round(br, 2); has_brake = True

    pre1 = t1.max_speed_window(PRE_FRAMES_START, PRE_FRAMES_END)
    pre2 = t2.max_speed_window(PRE_FRAMES_START, PRE_FRAMES_END)
    if max(pre1, pre2) > PRE_MIN_V:
        s += W_FAST_PRE; d["pre_v"] = round(max(pre1, pre2), 1)

    if not mismatch and t1.speed < STOP_SPEED and t2.speed < STOP_SPEED:
        s += W_BOTH_STOPPED; d["both_stopped"] = True

    if not mismatch and converging(t1, t2):
        s += W_CONVERGENCE; d["converge"] = True

    if iou > OVERLAP_IOU_MIN:
        s += W_IOU; d["iou"] = round(iou, 3)

    if duration > CRASH_CONFIRM_S:
        s += W_DURATION; d["dur"] = round(duration, 2)

    if mismatch:         threshold = 999
    elif has_brake:      threshold = PAIR_SCORE_BRAKE_BONUS
    else:                threshold = PAIR_SCORE_BASE

    return min(s, 100), d, has_brake, threshold


def is_debris_box(box, raw_median, cal_median) -> bool:
    x1,y1,x2,y2 = box
    w,h = x2-x1, y2-y1
    if h == 0 or w == 0: return False
    area  = w * h
    ratio = max(w/h, h/w)
    return (ratio >= DEBRIS_RATIO_MIN
            and DEBRIS_AREA_MIN <= area <= DEBRIS_AREA_MAX
            and raw_median < DEBRIS_SPEED_RAW_MAX
            and cal_median < DEBRIS_SPEED_MED_MAX)


def is_fused_box(box) -> bool:
    x1,y1,x2,y2 = box
    w,h = x2-x1, y2-y1
    if h == 0 or w == 0: return False
    return (max(w/h, h/w) >= FUSED_RATIO_MIN
            and FUSED_AREA_MIN <= w*h <= FUSED_AREA_MAX)


def spatial_pairs(tracks: dict) -> list:
    grid = defaultdict(list)
    for tid, trk in tracks.items():
        if trk.center is None: continue
        cx,cy = trk.center
        grid[(cx//GRID_CELL_SIZE, cy//GRID_CELL_SIZE)].append(tid)
    seen, pairs = set(), []
    for (gx,gy), ids in grid.items():
        pool = []
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                pool.extend(grid.get((gx+dx,gy+dy),[]))
        for id1 in ids:
            for id2 in pool:
                if id1 >= id2: continue
                p = (id1,id2)
                if p not in seen:
                    seen.add(p); pairs.append(p)
    return pairs


def specialist_conf_for_region(acc_detections, box) -> float:
    """
    Retourne la meilleure confiance du modèle spécialisé
    qui chevauche la région du véhicule.
    """
    if box is None or len(acc_detections) == 0:
        return 0.0
    best = 0.0
    for xyxy, conf in zip(acc_detections.xyxy, acc_detections.confidence):
        iou = box_iou(box, tuple(map(int, xyxy)))
        if iou >= SPECIALIST_REGION_IOU:
            best = max(best, float(conf))
    return best


def log_event(evts, etype, data):
    e = {"time": datetime.now().isoformat(), "type": etype, **data}
    evts.append(e)
    log.info(f"[EVENT] {etype} | {data}")


def save_events(evts):
    with open(OUTPUT_LOG, "w", encoding="utf-8") as f:
        json.dump(evts, f, indent=2, ensure_ascii=False)


def draw_alert(frame, x, y, label, score, bg=(0,0,175), border=(0,0,255)):
    ov = frame.copy()
    cv2.rectangle(ov, (x-190,y-122), (x+190,y-50), bg, -1)
    cv2.rectangle(ov, (x-193,y-125), (x+193,y-47), border, 3)
    cv2.addWeighted(ov, 0.68, frame, 0.32, 0, frame)
    cv2.putText(frame, label, (x-180,y-86),
                cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255,255,255), 2)
    bar = int(score * 3.6)
    cv2.rectangle(frame, (x-180,y-75), (x-180+bar,y-62), (0,220,70), -1)
    cv2.putText(frame, f"conf {score}%", (x-180,y-62),
                cv2.FONT_HERSHEY_SIMPLEX, 0.46, (255,240,130), 1)


def draw_pending(frame, x, y, label, progress):
    """Affiche un indicateur de délibération en cours (orange)."""
    ov = frame.copy()
    cv2.rectangle(ov, (x-180,y-100), (x+180,y-55), (0,80,160), -1)
    cv2.addWeighted(ov, 0.55, frame, 0.45, 0, frame)
    cv2.putText(frame, label, (x-170,y-72),
                cv2.FONT_HERSHEY_SIMPLEX, 0.60, (200,220,255), 2)
    bar = int(progress * 340)
    cv2.rectangle(frame, (x-170,y-62), (x-170+bar,y-52), (0,190,255), -1)
    cv2.putText(frame, f"deliberation {int(progress*100)}%", (x-170,y-52),
                cv2.FONT_HERSHEY_SIMPLEX, 0.40, (150,220,255), 1)


# ══════════════════════════════════════════════════════════════════
#  INITIALISATION
# ══════════════════════════════════════════════════════════════════

log.info("Chargement YOLO...")

# MODELE GENERAL
model = YOLO("yolov8n.pt")

# MODELE ACCIDENT SPECIALISE — chargement sécurisé
_acc_weights = r"E:\TRAFIQ-AI-Detection\runs\detect\train\weights\best.pt"
if os.path.exists(_acc_weights):
    accident_model = YOLO(_acc_weights)
    log.info(f"Modèle spécialisé chargé : {_acc_weights}")
else:
    accident_model = None
    log.warning(f"Modèle spécialisé introuvable : {_acc_weights} — validation spécialisée désactivée.")

tracker = sv.ByteTrack()

# Moteur de décision
engine = DecisionEngine()
engine.load_memory("trafiq_memory.json")  # charge scénarios précédents

cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    log.error(f"Impossible d'ouvrir : {VIDEO_PATH}"); exit(1)

fps_src = cap.get(cv2.CAP_PROP_FPS) or 25
W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
log.info(f"Video {W}x{H} @ {fps_src:.1f}fps")

writer = None
if SAVE_VIDEO:
    writer = cv2.VideoWriter(OUTPUT_VIDEO,
                             cv2.VideoWriter_fourcc(*"mp4v"), fps_src, (W,H))

tracks          : dict = {}
count_per_line  : dict = {l["label"]:{"up":0,"down":0,"total":0} for l in COUNT_LINES}
pair_states     : dict = {}
blacklist       : dict = {}
fused_since     : dict = {}
debris_since_d  : dict = {}
events_log      : list = []
fps_counter            = deque(maxlen=30)

# ══════════════════════════════════════════════════════════════════
#  BOUCLE PRINCIPALE
# ══════════════════════════════════════════════════════════════════

log.info("Démarrage moteur délibératif v9.0...")

while True:
    t0 = time.time()
    ret, frame = cap.read()
    if not ret:
        break

    now = time.time()

    # Purger blacklist expirée
    expired = [p for p,t in blacklist.items() if now > t]
    for p in expired:
        del blacklist[p]

    # ── Détection YOLO général ─────────────────────────────────────
    results    = model(frame, verbose=False)[0]
    detections = sv.Detections.from_ultralytics(results)
    detections = detections[np.isin(detections.class_id, [2,3,5,7])]
    detections = tracker.update_with_detections(detections)

    # ── Détection spécialisée best.pt ─────────────────────────────
    if accident_model is not None:
        acc_results    = accident_model(frame, verbose=False)[0]
        acc_detections = sv.Detections.from_ultralytics(acc_results)
    else:
        acc_detections = sv.Detections.empty()

    active_ids = set()

    # ── Mise à jour tracks ─────────────────────────────────────────
    for xyxy, tid in zip(detections.xyxy, detections.tracker_id):
        active_ids.add(tid)
        if tid not in tracks:
            tracks[tid] = VehicleTrack(tid)
        trk = tracks[tid]
        trk.update_position(xyxy, now)
        trk.compute_speed(HISTORY_FRAMES)

        # Comptage lignes
        if len(trk.positions) >= 2:
            _,cy_p,_ = trk.positions[-2]
            _,cy_c,_ = trk.positions[-1]
            for line in COUNT_LINES:
                lbl = line["label"]
                if lbl in trk.counted_lines: continue
                ly = line["y"]
                if cy_p < ly <= cy_c:
                    trk.counted_lines.add(lbl)
                    count_per_line[lbl]["down"]  += 1
                    count_per_line[lbl]["total"] += 1
                    log_event(events_log,"CROSS_DOWN",{"id":tid,"line":lbl,"v":round(trk.speed,1)})
                elif cy_p > ly >= cy_c:
                    trk.counted_lines.add(lbl)
                    count_per_line[lbl]["up"]    += 1
                    count_per_line[lbl]["total"] += 1
                    log_event(events_log,"CROSS_UP",{"id":tid,"line":lbl,"v":round(trk.speed,1)})

        # ── Statique
        med_cal = trk.speed_median(STATIC_MEDIAN_WINDOW)
        med_raw = trk.raw_median(10)
        is_slow = (med_cal < STATIC_MEDIAN_MAX and med_raw < STATIC_RAW_MAX)
        if is_slow:
            if trk.static_since is None and trk.frames_seen >= STATIC_MIN_FRAMES:
                trk.static_since = now
            if (trk.static_since and now - trk.static_since > STATIC_CONFIRM_S
                    and not trk.is_static):
                trk.is_static = True
                log_event(events_log, "STATIC", {"id":tid,"pos":trk.center})
        else:
            if trk.is_static:
                log_event(events_log, "STATIC_CLEARED", {"id":tid})
            trk.is_static    = False
            trk.static_since = None

        # ── [B] Debris
        med_raw_d = trk.raw_median(10)
        med_cal_d = trk.speed_median(10)
        if is_debris_box(trk.box, med_raw_d, med_cal_d):
            key_d = ("debris", tid)
            if tid not in debris_since_d:
                debris_since_d[tid] = now
            dur = now - debris_since_d[tid]
            spec_conf = specialist_conf_for_region(acc_detections, trk.box)
            engine.validate_specialist(key_d, spec_conf, now)
            if dur > DEBRIS_CONFIRM_S:
                engine.submit(key_d, 82, {"debris": True, "dur": round(dur,1)}, now)
            if engine.is_confirmed(key_d) and not any(
                    e.get("type")=="ACCIDENT_DEBRIS" and e.get("id")==tid
                    for e in events_log):
                log_event(events_log, "ACCIDENT_DEBRIS",
                          {"id":tid,"dur_s":round(dur,2),
                           "raw_v":round(med_raw_d,1),"pos":trk.center})
        else:
            debris_since_d.pop(tid, None)

        # ── [C] Boîte fusionnée
        if is_fused_box(trk.box):
            key_f = ("fused", tid)
            if tid not in fused_since:
                fused_since[tid] = now
            dur   = now - fused_since[tid]
            pre_v = trk.max_speed_window(20, 50)
            spec_conf = specialist_conf_for_region(acc_detections, trk.box)
            engine.validate_specialist(key_f, spec_conf, now)
            if dur > FUSED_CONFIRM_S and pre_v > FUSED_PRE_V_MIN:
                engine.submit(key_f, 85, {"fused": True, "pre_v": round(pre_v,1)}, now)
            if engine.is_confirmed(key_f) and not any(
                    e.get("type")=="ACCIDENT_FUSED" and e.get("id")==tid
                    for e in events_log):
                log_event(events_log, "ACCIDENT_FUSED",
                          {"id":tid,"dur":round(dur,2),"pre_v":round(pre_v,1),"pos":trk.center})
        else:
            fused_since.pop(tid, None)

    # ── Purge TTL ──────────────────────────────────────────────────
    dead = [tid for tid,trk in tracks.items() if not trk.is_alive(now)]
    for tid in dead:
        del tracks[tid]
        for p in [p for p in pair_states if tid in p]:
            pair_states.pop(p, None)
        fused_since.pop(tid, None)

    # ── [A] Détecteur paire ────────────────────────────────────────
    active = {tid: tracks[tid] for tid in active_ids if tid in tracks}

    for id1,id2 in spatial_pairs(active):
        t1 = active[id1]
        t2 = active[id2]
        if t1.box is None or t2.box is None:
            continue

        iou  = box_iou(t1.box, t2.box)
        dist = cdist(t1, t2)
        pair = (id1, id2)

        if pair in blacklist:
            continue

        in_contact = iou > OVERLAP_IOU_MIN or dist < PROXIMITY_PX

        if in_contact:
            avg_sz = (t1.box_size() + t2.box_size()) / 2.0
            if pair not in pair_states:
                pair_states[pair] = PairState(now, dist, avg_sz)

            ps          = pair_states[pair]
            sc,d,hb,thr = compute_pair_score(t1, t2, iou, ps.duration)
            ps.update(now, dist, sc, hb)

            # Séparation → blacklist
            if ps.separated:
                blacklist[pair] = now + BLACKLIST_DURATION_S
                pair_states.pop(pair, None)
                if engine.is_confirmed(pair):
                    engine._correct(pair, "separation", now)
                    log_event(events_log, "INVALIDATED",
                              {"ids":list(pair),"reason":"separation"})
                continue

            # Validation spécialiste sur la région fusionnée
            merged_box = (
                min(t1.box[0],t2.box[0]), min(t1.box[1],t2.box[1]),
                max(t1.box[2],t2.box[2]), max(t1.box[3],t2.box[3])
            )
            spec_conf = specialist_conf_for_region(acc_detections, merged_box)
            engine.validate_specialist(pair, spec_conf, now)

            # Soumettre au moteur de décision si score suffisant
            if sc >= thr:
                engine.submit(pair, sc, d, now, t1, t2)

            # Logguer si nouvellement confirmé
            if engine.is_confirmed(pair):
                c = engine.confirmed[pair]
                c["dist_at_confirm"] = dist
                if not any(e.get("type")=="ACCIDENT_PAIR"
                           and e.get("ids")==list(pair) for e in events_log):
                    log_event(events_log, "ACCIDENT_PAIR", {
                        "ids":   list(pair),
                        "score": engine.get_score(pair),
                        "details": d,
                        "v1": round(t1.speed,1),
                        "v2": round(t2.speed,1),
                    })

            # Auto-correction en continu
            engine.check_correction(pair, now, t1, t2, dist)

        else:
            if pair in pair_states:
                ps = pair_states[pair]
                ps.update(now, dist, ps.max_score, ps.has_brake)
                if ps.separated and engine.is_confirmed(pair):
                    engine._correct(pair, "post_sep", now)
                    blacklist[pair] = now + BLACKLIST_DURATION_S
                    log_event(events_log, "INVALIDATED",
                              {"ids":list(pair),"reason":"post_sep"})
                if now - ps.since > SEP_WINDOW_S + 2:
                    pair_states.pop(pair, None)

    # ── Validation globale best.pt sur toute la frame ──────────────
    # Si le spécialiste détecte un accident sans qu'aucune paire ne soit
    # en délibération, on loggue un événement de type SPECIALIST_SEUL.
    if len(acc_detections) > 0:
        for xyxy, conf, cls in zip(acc_detections.xyxy,
                                   acc_detections.confidence,
                                   acc_detections.class_id):
            if float(conf) < SPECIALIST_CONF_MIN:
                continue
            x1,y1,x2,y2 = map(int, xyxy)
            cx,cy = (x1+x2)//2, (y1+y2)//2
            score = int(float(conf) * 100)
            # Vérifier si cette région est déjà couverte par une paire confirmée
            already_covered = False
            for pair in list(engine.confirmed.keys()):
                if not isinstance(pair, tuple) or len(pair) != 2:
                    continue
                id1,id2 = pair
                t1 = active.get(id1); t2 = active.get(id2)
                if t1 and t2 and t1.box and t2.box:
                    mb = (min(t1.box[0],t2.box[0]), min(t1.box[1],t2.box[1]),
                          max(t1.box[2],t2.box[2]), max(t1.box[3],t2.box[3]))
                    if box_iou(mb, (x1,y1,x2,y2)) > 0.20:
                        already_covered = True
                        break
            if not already_covered:
                key_sp = ("specialist", cx, cy)
                engine.submit(key_sp, score,
                              {"specialist_only": True, "conf": round(float(conf),3)},
                              now)
                engine.validate_specialist(key_sp, float(conf), now)
                if engine.is_confirmed(key_sp):
                    cv2.rectangle(frame, (x1,y1), (x2,y2), (0,0,255), 3)
                    draw_alert(frame, cx, cy,
                               f"ACCIDENT [specialise] {score}%", score,
                               bg=(120,0,0), border=(0,0,255))
                    if not any(e.get("type")=="ACCIDENT_SPECIALISE"
                               and e.get("pos")==(cx,cy) for e in events_log):
                        log_event(events_log, "ACCIDENT_SPECIALISE",
                                  {"conf":round(float(conf),3),
                                   "pos":(cx,cy), "box":[x1,y1,x2,y2]})

    # ══════════════════════════════════════════════════════════════
    #  DESSIN
    # ══════════════════════════════════════════════════════════════

    # Lignes de comptage
    for line in COUNT_LINES:
        ly, col = line["y"], line["color"]
        cv2.line(frame, (0,ly), (W,ly), col, 2)
        s = count_per_line[line["label"]]
        cv2.putText(frame, f"{line['label']}  ↓{s['down']}  ↑{s['up']}",
                    (10,ly-8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 2)

    # Zones suspectes orange (délibération en cours)
    for pair, ps in pair_states.items():
        if engine.is_confirmed(pair) or pair in blacklist:
            continue
        id1,id2 = pair
        t1,t2 = active.get(id1), active.get(id2)
        if t1 and t2 and t1.box and t2.box:
            if size_mismatch(t1, t2): continue
            x1s = min(t1.box[0],t2.box[0])-6
            y1s = min(t1.box[1],t2.box[1])-6
            x2s = max(t1.box[2],t2.box[2])+6
            y2s = max(t1.box[3],t2.box[3])+6
            cv2.rectangle(frame, (x1s,y1s), (x2s,y2s), (0,140,255), 2)
            cv2.putText(frame, f"? {ps.max_score}%", (x1s,y1s-6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0,200,255), 1)
            # Barre de délibération
            if engine.is_pending(pair):
                prog = engine.pending_progress(pair)
                cx_d = (x1s+x2s)//2; cy_d = y1s
                draw_pending(frame, cx_d, cy_d,
                             f"Analyse... #{id1}<->{id2}", prog)

    # Boîtes véhicules
    for tid, trk in active.items():
        if trk.box is None: continue
        x1,y1,x2,y2 = trk.box
        spd = int(trk.speed)
        is_acc = (engine.is_confirmed((min(tid,0),max(tid,0))) or
                  any(engine.is_confirmed(p) for p in engine.confirmed
                      if isinstance(p, tuple) and len(p)==2 and tid in p) or
                  engine.is_confirmed(("debris", tid)) or
                  engine.is_confirmed(("fused",  tid)))

        if is_acc:
            color = (0,0,255)
            label = f"ACCIDENT #{tid}  {spd}px/s"
            cv2.rectangle(frame, (x1-3,y1-3), (x2+3,y2+3), (0,0,255), 4)
        elif trk.is_static:
            color = (160,160,160)
            label = f"STATIQUE #{tid}"
        elif trk.speed > MOVING_SPEED:
            color = (0,255,0)
            label = f"#{tid}  {spd}px/s  {trk.direction_str or ''}"
        else:
            color = (0,200,200)
            label = f"#{tid}  {spd}px/s"

        cv2.rectangle(frame, (x1,y1), (x2,y2), color, 2)
        (tw,th),_ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
        cv2.rectangle(frame, (x1,y1-th-14), (x1+tw+4,y1-2), (0,0,0), -1)
        cv2.putText(frame, label, (x1+2,y1-8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

    # Alertes paires confirmées
    for key, c in engine.confirmed.items():
        if not (isinstance(key, tuple) and len(key) == 2
                and isinstance(key[0], int)): continue
        id1,id2 = key
        trk = active.get(id1) or active.get(id2)
        if trk and trk.center:
            draw_alert(frame, *trk.center,
                       f"ACCIDENT  #{id1} <-> #{id2}", c["score"])

    # Alertes fusionnées confirmées
    for key, c in engine.confirmed.items():
        if not (isinstance(key, tuple) and key[0] == "fused"): continue
        tid = key[1]
        trk = active.get(tid)
        if trk and trk.center:
            draw_alert(frame, *trk.center,
                       f"ACCIDENT  #{tid} [fusionne]", c["score"])

    # Alertes débris confirmés
    for key, c in engine.confirmed.items():
        if not (isinstance(key, tuple) and key[0] == "debris"): continue
        tid = key[1]
        trk = active.get(tid)
        if trk and trk.center:
            draw_alert(frame, *trk.center,
                       f"ACCIDENT  #{tid} [epave]", c["score"],
                       bg=(80,0,160), border=(160,0,255))

    # HUD
    fps_counter.append(1.0 / max(1e-9, time.time()-t0))
    rfps   = np.mean(fps_counter)
    total  = sum(v["total"] for v in count_per_line.values())
    nb_acc = len([k for k in engine.confirmed
                  if not (isinstance(k, tuple) and k[0] in ("specialist",))])
    nb_pen = len(engine.pending)
    nb_cor = len(engine.corrections)

    cv2.rectangle(frame, (0,0), (600,68), (15,15,15), -1)
    cv2.putText(frame,
                f"Vehicules:{total}  Accidents:{nb_acc}  "
                f"Analyse:{nb_pen}  Corrections:{nb_cor}  FPS:{rfps:.1f}",
                (10,45), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255,255,255), 2)

    cv2.imshow("TRAFIQ AI ENGINE v9.0 — Deliberatif", frame)
    if writer: writer.write(frame)
    if cv2.waitKey(1) == 27:
        break

# ══════════════════════════════════════════════════════════════════
#  FINALISATION
# ══════════════════════════════════════════════════════════════════
cap.release()
if writer: writer.release()
cv2.destroyAllWindows()

save_events(events_log)
engine.save_memory("trafiq_memory.json")   # sauvegarde scénarios appris

log.info(f"FINAL — confirmés:{len(engine.confirmed)} "
         f"corrections:{len(engine.corrections)}")
for lbl, s in count_per_line.items():
    log.info(f"{lbl} → ↓{s['down']} ↑{s['up']} total={s['total']}")
if engine.corrections:
    log.info(f"AUTO-CORRECTIONS : {engine.corrections}")
log.info("Terminé.")
