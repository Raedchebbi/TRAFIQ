"""
╔══════════════════════════════════════════════════════════════════════╗
║              TRAFIQ AI ENGINE  —  Version 8.0  PROFESSIONAL         ║
║              Objectif : précision ≥ 90%                             ║
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
#  CONFIGURATION — TUNABLE
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

# ── Statique — double condition raw + calibré
STATIC_RAW_MAX        = 8.0
STATIC_MEDIAN_MAX     = 3.5
STATIC_MEDIAN_WINDOW  = 15
STATIC_CONFIRM_S      = 8.0
STATIC_MIN_FRAMES     = 60

# TTL / grille
TRACKER_TTL_S  = 4.0
GRID_CELL_SIZE = 200

# ══════════════════════════════════════════════════════════════════
#  [A] PAIRE — Paramètres
# ══════════════════════════════════════════════════════════════════

PAIR_SCORE_BASE        = 65
PAIR_SCORE_BRAKE_BONUS = 55

W_BRAKE                = 30
W_FAST_PRE             = 25
W_BOTH_STOPPED         = 20
W_CONVERGENCE          = 10
W_IOU                  = 10
W_DURATION             = 10

OVERLAP_IOU_MIN        = 0.10
PROXIMITY_PX           = 55

BRAKE_RATIO_MIN        = 2.5
BRAKE_SHORT            = 3
BRAKE_LONG             = 20

PRE_FRAMES_START       = 10
PRE_FRAMES_END         = 40
PRE_MIN_V              = 18

CRASH_CONFIRM_S        = 1.0
CONVERGENCE_ANGLE_MIN  = 75

# ── Filtre taille asymétrique (FIX 1 — anti-bus)
SIZE_RATIO_MAX         = 2.8

# ── Séparation post-contact normalisée
SEP_WINDOW_S           = 3.5
SEP_RATIO_MIN          = 0.55

# ── Blacklist durée
BLACKLIST_DURATION_S   = 60.0

# ══════════════════════════════════════════════════════════════════
#  [B] DEBRIS — Paramètres (FIX 3)
# ══════════════════════════════════════════════════════════════════

DEBRIS_RATIO_MIN       = 2.0
DEBRIS_AREA_MIN        = 15000
DEBRIS_AREA_MAX        = 85000
DEBRIS_SPEED_RAW_MAX   = 3.0
DEBRIS_SPEED_MED_MAX   = 3.5
DEBRIS_CONFIRM_S       = 4.0

# ══════════════════════════════════════════════════════════════════
#  [C] BOÎTE FUSIONNÉE
# ══════════════════════════════════════════════════════════════════

FUSED_RATIO_MIN        = 1.85
FUSED_AREA_MIN         = 15000
FUSED_AREA_MAX         = 130000
FUSED_CONFIRM_S        = 0.8
FUSED_PRE_V_MIN        = 16

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
#  CLASSES
# ══════════════════════════════════════════════════════════════════

class AdaptiveEMA:
    def __init__(self):
        self.v = None
        self.p = None

    def update(self, raw: float) -> float:
        if self.v is None:
            self.v = raw
            self.p = raw
            return raw
        d     = abs(raw - self.v)
        a     = min(0.65, 0.15 + d / 160.0)
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

    def speed_median(self, n: int = 15) -> float:
        h = list(self.speed_cal)[-n:]
        return median(h) if h else 0.0

    def raw_median(self, n: int = 10) -> float:
        h = list(self.speed_raw_buf)[-n:]
        return median(h) if h else 0.0

    def max_speed_window(self, a: int, b: int) -> float:
        h = list(self.speed_cal)
        n = len(h)
        i0 = max(0, n - 1 - b)
        i1 = max(0, n - 1 - a)
        w  = h[i0:i1+1]
        return max(w) if w else 0.0

    def braking_ratio(self) -> float:
        h = list(self.speed_cal)
        if len(h) < BRAKE_LONG:
            return 0.0
        d_s = max(0.0, h[-BRAKE_SHORT]  - h[-1])  / BRAKE_SHORT
        d_l = max(0.0, h[-BRAKE_LONG]   - h[-1])  / BRAKE_LONG
        return d_s / d_l if d_l > 0.3 else 0.0

    def box_area(self) -> float:
        if self.box is None:
            return 1.0
        return max(1.0, (self.box[2]-self.box[0]) * (self.box[3]-self.box[1]))

    def box_size(self) -> float:
        if self.box is None:
            return 1.0
        return max(1.0, ((self.box[2]-self.box[0]) + (self.box[3]-self.box[1])) / 2.0)

    def update_position(self, box, now: float):
        x1,y1,x2,y2 = map(int, box)
        cx,cy        = (x1+x2)//2, (y1+y2)//2
        self.box     = (x1,y1,x2,y2)
        self.center  = (cx,cy)
        self.last_seen = now
        self.frames_seen += 1
        self.positions.append((cx,cy,now))

    def compute_speed(self, history: int) -> float:
        if len(self.positions) < history:
            return self.speed
        cx_n,cy_n,t_n = self.positions[-1]
        cx_o,cy_o,t_o = self.positions[-history]
        dt = t_n - t_o
        if dt <= 0:
            return self.speed
        raw        = np.hypot(cx_n-cx_o, cy_n-cy_o) / dt
        cal        = raw * depth_factor(cy_n)
        self.speed     = self.ema.update(cal)
        self.speed_raw = raw
        self.speed_cal.append(self.speed)
        self.speed_raw_buf.append(raw)

        dy = cy_n - cy_o
        dx = cx_n - cx_o
        nm = math.hypot(dx, dy)
        if nm > 1:
            self.direction_vec = (dx/nm, dy/nm)
        self.direction_str = (
            ("bas" if dy > 0 else "haut") if abs(dy) >= abs(dx)
            else ("droite" if dx > 0 else "gauche")
        )
        return self.speed

    def trajectory_vector(self, n: int = 30):
        if len(self.positions) < 4:
            return None
        pts  = list(self.positions)[-min(n, len(self.positions)):]
        dx   = pts[-1][0] - pts[0][0]
        dy   = pts[-1][1] - pts[0][1]
        nm   = math.hypot(dx, dy)
        if nm < 4:
            return None
        return (dx/nm, dy/nm)

    def is_alive(self, now: float) -> bool:
        return (now - self.last_seen) <= TRACKER_TTL_S


class PairState:
    def __init__(self, now: float, dist: float, avg_size: float):
        self.since     = now
        self.avg_size  = max(1, avg_size)
        self.max_score = 0
        self.dist_min  = dist
        self.dist_log  = deque(maxlen=300)
        self.dist_log.append((now, dist / self.avg_size))
        self.separated = False
        self.has_brake  = False

    @property
    def duration(self) -> float:
        if not self.dist_log:
            return 0.0
        return self.dist_log[-1][0] - self.since

    def update(self, now: float, dist: float, score: int, has_brake: bool):
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
#  FONCTIONS
# ══════════════════════════════════════════════════════════════════

def depth_factor(cy: int) -> float:
    for y0, y1, f in DEPTH_ZONES:
        if y0 <= cy < y1:
            return f
    return 1.0


def box_iou(a, b) -> float:
    xA,yA = max(a[0],b[0]),max(a[1],b[1])
    xB,yB = min(a[2],b[2]),min(a[3],b[3])
    inter = max(0,xB-xA)*max(0,yB-yA)
    if inter == 0:
        return 0.0
    return inter / max(1,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter)


def cdist(t1: VehicleTrack, t2: VehicleTrack) -> float:
    if t1.center is None or t2.center is None:
        return float("inf")
    return math.hypot(t1.center[0]-t2.center[0], t1.center[1]-t2.center[1])


def angle_between(v1, v2) -> float:
    if v1 is None or v2 is None:
        return 0.0
    dot = max(-1.0, min(1.0, v1[0]*v2[0]+v1[1]*v2[1]))
    return math.degrees(math.acos(dot))


def converging(t1: VehicleTrack, t2: VehicleTrack) -> bool:
    return angle_between(
        t1.trajectory_vector(TRAJ_FRAMES),
        t2.trajectory_vector(TRAJ_FRAMES)
    ) >= CONVERGENCE_ANGLE_MIN


def size_mismatch(t1: VehicleTrack, t2: VehicleTrack) -> bool:
    a1 = t1.box_area()
    a2 = t2.box_area()
    big, small = max(a1, a2), min(a1, a2)
    return (big / small) > SIZE_RATIO_MAX


def compute_pair_score(t1: VehicleTrack, t2: VehicleTrack,
                       iou: float, duration: float) -> tuple:
    s, d = 0, {}
    has_brake = False
    mismatch = size_mismatch(t1, t2)

    br = max(t1.braking_ratio(), t2.braking_ratio())
    if br > BRAKE_RATIO_MIN:
        s += W_BRAKE
        d["brake"] = round(br, 2)
        has_brake  = True

    pre1 = t1.max_speed_window(PRE_FRAMES_START, PRE_FRAMES_END)
    pre2 = t2.max_speed_window(PRE_FRAMES_START, PRE_FRAMES_END)
    if max(pre1, pre2) > PRE_MIN_V:
        s += W_FAST_PRE
        d["pre_v"] = round(max(pre1, pre2), 1)

    if not mismatch and t1.speed < STOP_SPEED and t2.speed < STOP_SPEED:
        s += W_BOTH_STOPPED
        d["both_stopped"] = True

    if not mismatch and converging(t1, t2):
        s += W_CONVERGENCE
        d["converge"] = True

    if iou > OVERLAP_IOU_MIN:
        s += W_IOU
        d["iou"] = round(iou, 3)

    if duration > CRASH_CONFIRM_S:
        s += W_DURATION
        d["dur"] = round(duration, 2)

    if mismatch:
        threshold = 999
    elif has_brake:
        threshold = PAIR_SCORE_BRAKE_BONUS
    else:
        threshold = PAIR_SCORE_BASE

    return min(s, 100), d, has_brake, threshold


def is_debris_box(box, raw_median: float, cal_median: float) -> bool:
    x1,y1,x2,y2 = box
    w,h = x2-x1, y2-y1
    if h == 0 or w == 0:
        return False
    area  = w * h
    ratio = max(w/h, h/w)
    return (ratio >= DEBRIS_RATIO_MIN
            and DEBRIS_AREA_MIN <= area <= DEBRIS_AREA_MAX
            and raw_median < DEBRIS_SPEED_RAW_MAX
            and cal_median < DEBRIS_SPEED_MED_MAX)


def is_fused_box(box) -> bool:
    x1,y1,x2,y2 = box
    w,h = x2-x1, y2-y1
    if h == 0 or w == 0:
        return False
    return (max(w/h,h/w) >= FUSED_RATIO_MIN
            and FUSED_AREA_MIN <= w*h <= FUSED_AREA_MAX)


def spatial_pairs(tracks: dict) -> list:
    grid = defaultdict(list)
    for tid, trk in tracks.items():
        if trk.center is None:
            continue
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
                if id1 >= id2:
                    continue
                p = (id1,id2)
                if p not in seen:
                    seen.add(p)
                    pairs.append(p)
    return pairs


def log_event(evts, etype, data):
    e = {"time": datetime.now().isoformat(), "type": etype, **data}
    evts.append(e)
    log.info(f"[EVENT] {etype} | {data}")


def save_events(evts):
    with open(OUTPUT_LOG,"w",encoding="utf-8") as f:
        json.dump(evts,f,indent=2,ensure_ascii=False)


def draw_alert(frame, x:int, y:int, label:str, score:int,
               bg=(0,0,175), border=(0,0,255)):
    ov = frame.copy()
    cv2.rectangle(ov,(x-190,y-122),(x+190,y-50),bg,-1)
    cv2.rectangle(ov,(x-193,y-125),(x+193,y-47),border,3)
    cv2.addWeighted(ov,0.68,frame,0.32,0,frame)
    cv2.putText(frame,label,(x-180,y-86),
                cv2.FONT_HERSHEY_SIMPLEX,0.75,(255,255,255),2)
    bar = int(score*3.6)
    cv2.rectangle(frame,(x-180,y-75),(x-180+bar,y-62),(0,220,70),-1)
    cv2.putText(frame,f"conf {score}%",(x-180,y-62),
                cv2.FONT_HERSHEY_SIMPLEX,0.46,(255,240,130),1)


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
    log.warning(f"Modèle spécialisé introuvable : {_acc_weights} — détection spécialisée désactivée.")

tracker = sv.ByteTrack()

cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    log.error(f"Impossible : {VIDEO_PATH}"); exit(1)

fps_src = cap.get(cv2.CAP_PROP_FPS) or 25
W       = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
H       = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
log.info(f"Video {W}x{H} @ {fps_src:.1f}fps")

writer = None
if SAVE_VIDEO:
    writer = cv2.VideoWriter(OUTPUT_VIDEO,
                             cv2.VideoWriter_fourcc(*"mp4v"),fps_src,(W,H))

tracks          : dict = {}
count_per_line  : dict = {l["label"]:{"up":0,"down":0,"total":0} for l in COUNT_LINES}
pair_states     : dict = {}
confirmed_pairs : dict = {}
blacklist       : dict = {}
fused_since     : dict = {}
confirmed_fused : dict = {}
confirmed_debris: dict = {}
events_log      : list = []
fps_counter            = deque(maxlen=30)

# ══════════════════════════════════════════════════════════════════
#  BOUCLE PRINCIPALE
# ══════════════════════════════════════════════════════════════════

log.info("Démarrage...")

while True:
    t0  = time.time()
    ret, frame = cap.read()
    if not ret:
        break

    now = time.time()

    # Purger blacklist expirée
    expired = [p for p,t in blacklist.items() if now > t]
    for p in expired:
        del blacklist[p]

    # ── Détection YOLO (modèle général) ───────────────────────────
    results    = model(frame, verbose=False)[0]
    detections = sv.Detections.from_ultralytics(results)
    detections = detections[np.isin(detections.class_id,[2,3,5,7])]
    detections = tracker.update_with_detections(detections)

    # ── Détection accident spécialisée (si modèle disponible) ─────
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

        # ── Statique — double condition raw + calibré (FIX 2)
        med_cal = trk.speed_median(STATIC_MEDIAN_WINDOW)
        med_raw = trk.raw_median(10)
        is_slow = (med_cal < STATIC_MEDIAN_MAX and med_raw < STATIC_RAW_MAX)

        if is_slow:
            if trk.static_since is None and trk.frames_seen >= STATIC_MIN_FRAMES:
                trk.static_since = now
            if (trk.static_since and
                    now - trk.static_since > STATIC_CONFIRM_S and
                    not trk.is_static):
                trk.is_static = True
                log_event(events_log,"STATIC",{"id":tid,"pos":trk.center})
        else:
            if trk.is_static:
                log_event(events_log,"STATIC_CLEARED",{"id":tid})
            trk.is_static    = False
            trk.static_since = None

        # ── [B] Debris strict (FIX 3)
        med_raw_d = trk.raw_median(10)
        med_cal_d = trk.speed_median(10)
        if is_debris_box(trk.box, med_raw_d, med_cal_d):
            if trk.debris_since is None:
                trk.debris_since = now
            dur = now - trk.debris_since
            if dur > DEBRIS_CONFIRM_S and tid not in confirmed_debris:
                confirmed_debris[tid] = 82
                log_event(events_log,"ACCIDENT_DEBRIS",
                          {"id":tid,"dur_s":round(dur,2),
                           "raw_v":round(med_raw_d,1),"pos":trk.center})
        else:
            trk.debris_since = None

        # ── [C] Boîte fusionnée
        if is_fused_box(trk.box):
            if tid not in fused_since:
                fused_since[tid] = now
            dur   = now - fused_since[tid]
            pre_v = trk.max_speed_window(20,50)
            if dur > FUSED_CONFIRM_S and pre_v > FUSED_PRE_V_MIN and tid not in confirmed_fused:
                confirmed_fused[tid] = 85
                log_event(events_log,"ACCIDENT_FUSED",
                          {"id":tid,"dur":round(dur,2),"pre_v":round(pre_v,1),"pos":trk.center})
        else:
            fused_since.pop(tid,None)

    # ── Purge TTL ──────────────────────────────────────────────────
    dead = [tid for tid,trk in tracks.items() if not trk.is_alive(now)]
    for tid in dead:
        del tracks[tid]
        for p in [p for p in pair_states if tid in p]:
            pair_states.pop(p,None)
        fused_since.pop(tid,None)

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
            avg_sz = (t1.box_size()+t2.box_size())/2.0
            if pair not in pair_states:
                pair_states[pair] = PairState(now, dist, avg_sz)

            ps            = pair_states[pair]
            sc,d,hb,thr   = compute_pair_score(t1,t2,iou,ps.duration)
            ps.update(now, dist, sc, hb)

            if ps.separated:
                blacklist[pair] = now + BLACKLIST_DURATION_S
                pair_states.pop(pair,None)
                if pair in confirmed_pairs:
                    del confirmed_pairs[pair]
                    log_event(events_log,"INVALIDATED",
                              {"ids":list(pair),"reason":"separation"})
                continue

            if sc >= thr and pair not in confirmed_pairs:
                confirmed_pairs[pair] = sc
                log_event(events_log,"ACCIDENT_PAIR",{
                    "ids":list(pair),"score":sc,"details":d,
                    "v1":round(t1.speed,1),"v2":round(t2.speed,1)
                })
        else:
            if pair in pair_states:
                ps = pair_states[pair]
                ps.update(now, dist, ps.max_score, ps.has_brake)
                if ps.separated and pair in confirmed_pairs:
                    del confirmed_pairs[pair]
                    blacklist[pair] = now + BLACKLIST_DURATION_S
                    log_event(events_log,"INVALIDATED",
                              {"ids":list(pair),"reason":"post_sep"})
                if now - ps.since > SEP_WINDOW_S + 2:
                    pair_states.pop(pair,None)

    # ══════════════════════════════════════════════════════════════
    #  DESSIN
    # ══════════════════════════════════════════════════════════════

    # Lignes
    for line in COUNT_LINES:
        ly,col = line["y"],line["color"]
        cv2.line(frame,(0,ly),(W,ly),col,2)
        s = count_per_line[line["label"]]
        cv2.putText(frame,f"{line['label']}  ↓{s['down']}  ↑{s['up']}",
                    (10,ly-8),cv2.FONT_HERSHEY_SIMPLEX,0.55,col,2)

    # Zones suspectes orange
    for pair,ps in pair_states.items():
        if pair in confirmed_pairs or pair in blacklist:
            continue
        id1,id2 = pair
        t1,t2 = active.get(id1),active.get(id2)
        if t1 and t2 and t1.box and t2.box:
            if size_mismatch(t1,t2):
                continue
            x1s=min(t1.box[0],t2.box[0])-6
            y1s=min(t1.box[1],t2.box[1])-6
            x2s=max(t1.box[2],t2.box[2])+6
            y2s=max(t1.box[3],t2.box[3])+6
            cv2.rectangle(frame,(x1s,y1s),(x2s,y2s),(0,140,255),2)
            cv2.putText(frame,f"? {ps.max_score}%",(x1s,y1s-6),
                        cv2.FONT_HERSHEY_SIMPLEX,0.44,(0,200,255),1)

    # Boîtes véhicules
    for tid,trk in active.items():
        if trk.box is None: continue
        x1,y1,x2,y2 = trk.box
        spd          = int(trk.speed)
        is_acc = (any(tid in p for p in confirmed_pairs)
                  or tid in confirmed_fused
                  or tid in confirmed_debris)

        if is_acc:
            color=(0,0,255)
            label=f"ACCIDENT #{tid}  {spd}px/s"
            cv2.rectangle(frame,(x1-3,y1-3),(x2+3,y2+3),(0,0,255),4)
        elif trk.is_static:
            color=(160,160,160)
            label=f"STATIQUE #{tid}"
        elif trk.speed > MOVING_SPEED:
            color=(0,255,0)
            label=f"#{tid}  {spd}px/s  {trk.direction_str or ''}"
        else:
            color=(0,200,200)
            label=f"#{tid}  {spd}px/s"

        cv2.rectangle(frame,(x1,y1),(x2,y2),color,2)
        (tw,th),_ = cv2.getTextSize(label,cv2.FONT_HERSHEY_SIMPLEX,0.55,2)
        cv2.rectangle(frame,(x1,y1-th-14),(x1+tw+4,y1-2),(0,0,0),-1)
        cv2.putText(frame,label,(x1+2,y1-8),
                    cv2.FONT_HERSHEY_SIMPLEX,0.55,color,2)

    # Alertes paire
    for pair,sc in confirmed_pairs.items():
        id1,id2=pair
        trk=active.get(id1) or active.get(id2)
        if trk and trk.center:
            draw_alert(frame,*trk.center,f"ACCIDENT  #{id1} <-> #{id2}",sc)

    # Alertes fusionnée
    for tid,sc in confirmed_fused.items():
        trk=active.get(tid)
        if trk and trk.center:
            draw_alert(frame,*trk.center,f"ACCIDENT  #{tid} [fusionne]",sc)

    # Alertes debris
    for tid,sc in confirmed_debris.items():
        trk=active.get(tid)
        if trk and trk.center:
            draw_alert(frame,*trk.center,f"ACCIDENT  #{tid} [epave]",sc,
                       bg=(80,0,160),border=(160,0,255))

    # ── Alertes modèle accident spécialisé ────────────────────────
    if len(acc_detections) > 0:
        for xyxy, conf, cls in zip(acc_detections.xyxy,
                                   acc_detections.confidence,
                                   acc_detections.class_id):
            if conf < 0.50:
                continue
            x1,y1,x2,y2 = map(int, xyxy)
            cx,cy = (x1+x2)//2, (y1+y2)//2
            score = int(conf * 100)
            cv2.rectangle(frame,(x1,y1),(x2,y2),(0,0,255),3)
            draw_alert(frame, cx, cy, f"ACCIDENT [specialise] conf:{score}%", score,
                       bg=(120,0,0), border=(0,0,255))
            log_event(events_log, "ACCIDENT_SPECIALISE",
                      {"conf": round(float(conf),3), "pos": (cx,cy),
                       "box": [x1,y1,x2,y2]})

    # HUD
    fps_counter.append(1.0/max(1e-9,time.time()-t0))
    rfps   = np.mean(fps_counter)
    total  = sum(v["total"] for v in count_per_line.values())
    nb_acc = len(confirmed_pairs)+len(confirmed_fused)+len(confirmed_debris)

    cv2.rectangle(frame,(0,0),(480,62),(15,15,15),-1)
    cv2.putText(frame,
                f"Vehicules: {total}   Accidents: {nb_acc}   FPS: {rfps:.1f}",
                (10,42),cv2.FONT_HERSHEY_SIMPLEX,0.88,(255,255,255),2)

    cv2.imshow("TRAFIQ AI ENGINE v8.0",frame)
    if writer: writer.write(frame)
    if cv2.waitKey(1)==27: break

# ══════════════════════════════════════════════════════════════════
cap.release()
if writer: writer.release()
cv2.destroyAllWindows()
save_events(events_log)
log.info(f"FINAL — paire:{len(confirmed_pairs)} fused:{len(confirmed_fused)} debris:{len(confirmed_debris)}")
for lbl,s in count_per_line.items():
    log.info(f"{lbl} → ↓{s['down']} ↑{s['up']} total={s['total']}")
log.info("Termine.")