"""
╔══════════════════════════════════════════════════════════════════════╗
║         TRAFIQ AI ENGINE  —  Version 9.2  PROFESSIONNEL             ║
║                                                                      ║
║  CORRECTIFS v9.2 :                                                   ║
║  - Détection voiture renversée / accidentée (ratio boîte + immobile) ║
║  - Exclusion bus/camion des alertes accident                         ║
║  - Correction affichage compteurs lignes                             ║
║  - Seuils paire assouplis pour détecter l'impact réel               ║
║  - best.pt comme validateur (pas bloquant)                           ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os, cv2, numpy as np, time, json, logging, math
from ultralytics import YOLO
import supervision as sv
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
ACC_WEIGHTS  = r"E:\TRAFIQ-AI-Detection\runs\detect\train\weights\best.pt"

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

# Statique
STATIC_RAW_MAX       = 8.0
STATIC_MEDIAN_MAX    = 3.5
STATIC_MEDIAN_WINDOW = 15
STATIC_CONFIRM_S     = 8.0
STATIC_MIN_FRAMES    = 60

TRACKER_TTL_S  = 4.0
GRID_CELL_SIZE = 200

# ── Classes YOLO à inclure (voiture=2, moto=3, bus=5, camion=7)
VEHICLE_CLASSES   = [2, 3, 5, 7]
# Classes exclues des alertes accident (bus et camion trop grands)
LARGE_VEHICLE_CLS = [5, 7]

# ══════════════════════════════════════════════════════════════════
#  HEURISTIQUE PAIRE
# ══════════════════════════════════════════════════════════════════

PAIR_SCORE_BASE        = 55   # abaissé v9.2 (était 65)
PAIR_SCORE_BRAKE_BONUS = 45   # abaissé v9.2

W_BRAKE        = 30
W_FAST_PRE     = 25
W_BOTH_STOPPED = 20
W_CONVERGENCE  = 10
W_IOU          = 10
W_DURATION     = 10

OVERLAP_IOU_MIN       = 0.08  # abaissé v9.2
PROXIMITY_PX          = 65    # élargi v9.2
BRAKE_RATIO_MIN       = 2.0   # abaissé v9.2
BRAKE_SHORT           = 3
BRAKE_LONG            = 20
PRE_FRAMES_START      = 10
PRE_FRAMES_END        = 40
PRE_MIN_V             = 15    # abaissé v9.2
CRASH_CONFIRM_S       = 0.8   # abaissé v9.2
CONVERGENCE_ANGLE_MIN = 70
SEP_WINDOW_S          = 3.5
SEP_RATIO_MIN         = 0.55
BLACKLIST_DURATION_S  = 60.0

# ── Anti-bus : ratio max autorisé entre les deux boîtes
SIZE_RATIO_MAX = 2.5   # si grand/petit > 2.5 → probablement bus → pas une paire

# ══════════════════════════════════════════════════════════════════
#  DÉTECTION VOITURE RENVERSÉE / ACCIDENTÉE  ← NOUVEAU v9.2
# ══════════════════════════════════════════════════════════════════

# Une voiture renversée a une boîte LARGE (largeur >> hauteur) et est immobile
OVERTURN_RATIO_MIN    = 1.6   # w/h > 1.6 → possible renversement
OVERTURN_AREA_MIN     = 8000
OVERTURN_AREA_MAX     = 120000
OVERTURN_SPEED_MAX    = 6.0   # px/s calibré max (quasi immobile)
OVERTURN_CONFIRM_S    = 2.5   # doit durer N secondes
OVERTURN_MIN_FRAMES   = 20    # doit avoir été vu N frames
# Exclure les bus (trop larges par nature)
OVERTURN_BUS_AREA_MAX = 60000 # au-dessus → probablement bus/camion

# ══════════════════════════════════════════════════════════════════
#  DÉBRIS
# ══════════════════════════════════════════════════════════════════

DEBRIS_RATIO_MIN     = 1.8
DEBRIS_AREA_MIN      = 6000
DEBRIS_AREA_MAX      = 90000
DEBRIS_SPEED_RAW_MAX = 4.0
DEBRIS_SPEED_MED_MAX = 4.0
DEBRIS_CONFIRM_S     = 3.0

# ══════════════════════════════════════════════════════════════════
#  FUSIONNÉ
# ══════════════════════════════════════════════════════════════════

FUSED_RATIO_MIN = 1.85
FUSED_AREA_MIN  = 15000
FUSED_AREA_MAX  = 130000
FUSED_CONFIRM_S = 0.8
FUSED_PRE_V_MIN = 14

# ══════════════════════════════════════════════════════════════════
#  DÉCISION HYBRIDE
# ══════════════════════════════════════════════════════════════════

SPEC_CONF_STRONG  = 0.50
SPEC_CONF_SUPPORT = 0.30
SPEC_CONF_VETO    = 0.12
SPEC_IOU_REGION   = 0.10

HYBRID_HEUR_MIN   = 50
HYBRID_CONFIRM_S  = 0.8

CORRECT_SEP_MULT    = 2.0
CORRECT_SPEED_RES   = 30.0
CORRECT_WINDOW_S    = 10.0
CORRECT_SPEC_LOSS_S = 6.0

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
        self.v = self.p = None

    def update(self, raw):
        if self.v is None:
            self.v = self.p = raw; return raw
        d = abs(raw - self.v)
        a = min(0.65, 0.15 + d / 160.0)
        self.p = self.v
        self.v = a * raw + (1 - a) * self.v
        return self.v


class VehicleTrack:
    def __init__(self, tid):
        self.tid            = tid
        self.positions      = deque(maxlen=150)
        self.speed_cal      = deque(maxlen=80)
        self.speed_raw_buf  = deque(maxlen=80)
        self.ema            = AdaptiveEMA()
        self.speed          = 0.0
        self.speed_raw      = 0.0
        self.box            = None
        self.center         = None
        self.cls_id         = None   # classe YOLO (2=car,3=moto,5=bus,7=truck)
        self.last_seen      = time.time()
        self.frames_seen    = 0
        self.direction_vec  = None
        self.direction_str  = None
        self.counted_lines  : set = set()
        self.static_since   = None
        self.is_static      = False
        self.debris_since   = None
        self.overturn_since = None   # ← NOUVEAU

    def is_large_vehicle(self):
        return self.cls_id in LARGE_VEHICLE_CLS

    def speed_median(self, n=15):
        h = list(self.speed_cal)[-n:]
        return median(h) if h else 0.0

    def raw_median(self, n=10):
        h = list(self.speed_raw_buf)[-n:]
        return median(h) if h else 0.0

    def max_speed_window(self, a, b):
        h = list(self.speed_cal)
        n = len(h)
        w = h[max(0, n-1-b):max(0, n-1-a)+1]
        return max(w) if w else 0.0

    def braking_ratio(self):
        h = list(self.speed_cal)
        if len(h) < BRAKE_LONG: return 0.0
        d_s = max(0.0, h[-BRAKE_SHORT] - h[-1]) / BRAKE_SHORT
        d_l = max(0.0, h[-BRAKE_LONG]  - h[-1]) / BRAKE_LONG
        return d_s / d_l if d_l > 0.3 else 0.0

    def box_area(self):
        if self.box is None: return 1.0
        return max(1.0, (self.box[2]-self.box[0]) * (self.box[3]-self.box[1]))

    def box_size(self):
        if self.box is None: return 1.0
        return max(1.0, ((self.box[2]-self.box[0]) + (self.box[3]-self.box[1])) / 2.0)

    def box_wh_ratio(self):
        """Retourne w/h — ratio > 1 = large, < 1 = haut."""
        if self.box is None: return 1.0
        w = max(1, self.box[2]-self.box[0])
        h = max(1, self.box[3]-self.box[1])
        return w / h

    def update_position(self, box, now, cls_id=None):
        x1,y1,x2,y2 = map(int, box)
        cx,cy = (x1+x2)//2, (y1+y2)//2
        self.box       = (x1,y1,x2,y2)
        self.center    = (cx,cy)
        self.last_seen = now
        self.frames_seen += 1
        if cls_id is not None: self.cls_id = int(cls_id)
        self.positions.append((cx,cy,now))

    def compute_speed(self, history):
        if len(self.positions) < history: return self.speed
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
        dy, dx = cy_n-cy_o, cx_n-cx_o
        nm = math.hypot(dx, dy)
        if nm > 1: self.direction_vec = (dx/nm, dy/nm)
        self.direction_str = (
            ("bas" if dy > 0 else "haut") if abs(dy) >= abs(dx)
            else ("droite" if dx > 0 else "gauche")
        )
        return self.speed

    def trajectory_vector(self, n=30):
        if len(self.positions) < 4: return None
        pts = list(self.positions)[-min(n, len(self.positions)):]
        dx, dy = pts[-1][0]-pts[0][0], pts[-1][1]-pts[0][1]
        nm = math.hypot(dx, dy)
        return (dx/nm, dy/nm) if nm >= 4 else None

    def is_alive(self, now):
        return (now - self.last_seen) <= TRACKER_TTL_S


class PairState:
    def __init__(self, now, dist, avg_size):
        self.since     = now
        self.avg_size  = max(1, avg_size)
        self.max_score = 0
        self.dist_min  = dist
        self.dist_log  = deque(maxlen=300)
        self.dist_log.append((now, dist / self.avg_size))
        self.separated = False
        self.has_brake = False

    @property
    def duration(self):
        return (self.dist_log[-1][0] - self.since) if self.dist_log else 0.0

    def update(self, now, dist, score, has_brake):
        nd = dist / self.avg_size
        self.dist_log.append((now, nd))
        self.dist_min  = min(self.dist_min, dist)
        self.max_score = max(self.max_score, score)
        if has_brake: self.has_brake = True
        nm = self.dist_min / self.avg_size
        if nd - nm > SEP_RATIO_MIN:
            for t_o, d_o in self.dist_log:
                if now - t_o <= SEP_WINDOW_S:
                    if nd - d_o > SEP_RATIO_MIN * 0.65:
                        self.separated = True; break


# ══════════════════════════════════════════════════════════════════
#  MOTEUR DÉCISION HYBRIDE
# ══════════════════════════════════════════════════════════════════

class HybridDecision:
    def __init__(self):
        self.confirmed   : dict = {}
        self.corrections : list = []
        self.memory      : deque = deque(maxlen=300)

    def evaluate(self, key, heur_score, heur_thr, duration,
                 spec_conf, dist, now, evidence):
        if key in self.confirmed: return False

        # Veto spécialiste fort
        if 0 < spec_conf < SPEC_CONF_VETO: return False

        confirmed, level = False, 0

        # Niveau 1 — best.pt très confiant seul
        if spec_conf >= SPEC_CONF_STRONG:
            confirmed, level = True, 1

        # Niveau 2 — best.pt + heuristique ensemble
        elif (spec_conf >= SPEC_CONF_SUPPORT
              and heur_score >= HYBRID_HEUR_MIN
              and duration   >= HYBRID_CONFIRM_S):
            confirmed, level = True, 2

        # Niveau 3 — heuristique seule (best.pt absent ou faible)
        elif (spec_conf < SPEC_CONF_SUPPORT
              and heur_score >= heur_thr
              and duration   >= HYBRID_CONFIRM_S):
            confirmed, level = True, 3

        if confirmed:
            self.confirmed[key] = {
                "score": heur_score, "spec_conf": spec_conf,
                "level": level, "confirmed_at": now,
                "dist_init": dist, "spec_last": now if spec_conf > 0 else None,
                "evidence": evidence,
            }
            self.memory.append({
                "key": str(key), "score": heur_score,
                "spec": round(spec_conf,3), "level": level, "outcome": "accident"
            })
            log.info(f"[CONFIRM L{level}] {key} | score={heur_score} "
                     f"spec={spec_conf:.2f} dur={duration:.1f}s ev={evidence}")
            return True
        return False

    def update_spec(self, key, spec_conf, now):
        if key in self.confirmed and spec_conf > 0:
            self.confirmed[key]["spec_last"] = now
            self.confirmed[key]["spec_conf"] = spec_conf

    def check_correction(self, key, now, t1=None, t2=None, dist=None):
        if key not in self.confirmed: return False
        c = self.confirmed[key]
        if now - c["confirmed_at"] > CORRECT_WINDOW_S: return False

        reason = None
        if dist and dist > c["dist_init"] * CORRECT_SEP_MULT:
            reason = "separation_rapide"
        if t1 and t2 and max(t1.speed, t2.speed) > CORRECT_SPEED_RES:
            reason = "reprise_vitesse"
        if c["level"] in (1,2):
            sl = c.get("spec_last")
            if sl and now - sl > CORRECT_SPEC_LOSS_S and c.get("spec_conf",1)<SPEC_CONF_SUPPORT:
                reason = "specialiste_desaccord"

        if reason:
            p = self.confirmed.pop(key)
            self.corrections.append({"key":str(key),"reason":reason,"score":p["score"],"at":now})
            self.memory.append({"key":str(key),"score":p["score"],
                                "spec":p.get("spec_conf",0),"level":p["level"],"outcome":"faux_positif"})
            log.info(f"[CORRECTION] {key} annulé — {reason}")
            return True
        return False

    def is_confirmed(self, key): return key in self.confirmed
    def get_score(self, key):   return self.confirmed[key]["score"] if key in self.confirmed else 0
    def get_level(self, key):   return self.confirmed[key]["level"] if key in self.confirmed else 0

    def save(self, path="trafiq_memory.json"):
        with open(path,"w",encoding="utf-8") as f:
            json.dump(list(self.memory),f,indent=2,ensure_ascii=False)

    def load(self, path="trafiq_memory.json"):
        if not os.path.exists(path): return
        try:
            with open(path,encoding="utf-8") as f:
                for item in json.load(f): self.memory.append(item)
            log.info(f"[MEMORY] {len(self.memory)} scénarios chargés.")
        except Exception as e:
            log.warning(f"[MEMORY] Erreur : {e}")


# ══════════════════════════════════════════════════════════════════
#  FONCTIONS
# ══════════════════════════════════════════════════════════════════

def depth_factor(cy):
    for y0,y1,f in DEPTH_ZONES:
        if y0 <= cy < y1: return f
    return 1.0

def box_iou(a, b):
    xA,yA = max(a[0],b[0]), max(a[1],b[1])
    xB,yB = min(a[2],b[2]), min(a[3],b[3])
    inter = max(0,xB-xA)*max(0,yB-yA)
    if inter==0: return 0.0
    return inter/max(1,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter)

def cdist(t1, t2):
    if t1.center is None or t2.center is None: return float("inf")
    return math.hypot(t1.center[0]-t2.center[0], t1.center[1]-t2.center[1])

def angle_between(v1, v2):
    if v1 is None or v2 is None: return 0.0
    dot = max(-1.0, min(1.0, v1[0]*v2[0]+v1[1]*v2[1]))
    return math.degrees(math.acos(dot))

def converging(t1, t2):
    return angle_between(t1.trajectory_vector(TRAJ_FRAMES),
                         t2.trajectory_vector(TRAJ_FRAMES)) >= CONVERGENCE_ANGLE_MIN

def size_mismatch(t1, t2):
    """Retourne True si les boîtes sont trop différentes → bus/camion + voiture."""
    a1,a2 = t1.box_area(), t2.box_area()
    return (max(a1,a2)/min(a1,a2)) > SIZE_RATIO_MAX

def pair_has_large_vehicle(t1, t2):
    """Retourne True si l'une des deux est un bus ou camion."""
    return t1.is_large_vehicle() or t2.is_large_vehicle()

def compute_pair_score(t1, t2, iou, duration):
    s, d = 0, {}
    has_brake = False

    # Exclure totalement si bus/camion impliqué
    if pair_has_large_vehicle(t1, t2):
        return 0, {}, False, 999

    mismatch = size_mismatch(t1, t2)

    br = max(t1.braking_ratio(), t2.braking_ratio())
    if br > BRAKE_RATIO_MIN:
        s += W_BRAKE; d["brake"] = round(br,2); has_brake = True

    pre1 = t1.max_speed_window(PRE_FRAMES_START, PRE_FRAMES_END)
    pre2 = t2.max_speed_window(PRE_FRAMES_START, PRE_FRAMES_END)
    if max(pre1,pre2) > PRE_MIN_V:
        s += W_FAST_PRE; d["pre_v"] = round(max(pre1,pre2),1)

    if not mismatch and t1.speed < STOP_SPEED and t2.speed < STOP_SPEED:
        s += W_BOTH_STOPPED; d["both_stopped"] = True

    if not mismatch and converging(t1, t2):
        s += W_CONVERGENCE; d["converge"] = True

    if iou > OVERLAP_IOU_MIN:
        s += W_IOU; d["iou"] = round(iou,3)

    if duration > CRASH_CONFIRM_S:
        s += W_DURATION; d["dur"] = round(duration,2)

    threshold = 999 if mismatch else (PAIR_SCORE_BRAKE_BONUS if has_brake else PAIR_SCORE_BASE)
    return min(s,100), d, has_brake, threshold


def is_overturned_vehicle(trk: VehicleTrack) -> bool:
    """
    Détecte une voiture renversée ou gravement accidentée.
    Critères :
      - Boîte très large (w >> h) → véhicule couché
      - Quasi immobile (vitesse calibrée faible)
      - Taille cohérente avec une voiture (pas un bus)
      - Pas un grand véhicule (bus/camion)
    """
    if trk.box is None: return False
    if trk.is_large_vehicle(): return False
    if trk.frames_seen < OVERTURN_MIN_FRAMES: return False

    x1,y1,x2,y2 = trk.box
    w, h = x2-x1, y2-y1
    if h == 0: return False

    area  = w * h
    ratio = w / h   # large si > 1.6

    speed_ok = trk.speed_median(10) < OVERTURN_SPEED_MAX

    return (ratio >= OVERTURN_RATIO_MIN
            and OVERTURN_AREA_MIN <= area <= OVERTURN_BUS_AREA_MAX
            and speed_ok)


def is_debris_box(box, raw_med, cal_med):
    x1,y1,x2,y2 = box
    w,h = x2-x1, y2-y1
    if h==0 or w==0: return False
    return (max(w/h,h/w) >= DEBRIS_RATIO_MIN
            and DEBRIS_AREA_MIN <= w*h <= DEBRIS_AREA_MAX
            and raw_med < DEBRIS_SPEED_RAW_MAX
            and cal_med < DEBRIS_SPEED_MED_MAX)


def is_fused_box(box):
    x1,y1,x2,y2 = box
    w,h = x2-x1, y2-y1
    if h==0 or w==0: return False
    return (max(w/h,h/w) >= FUSED_RATIO_MIN
            and FUSED_AREA_MIN <= w*h <= FUSED_AREA_MAX)


def spatial_pairs(tracks):
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


def best_spec_conf(acc_det, box):
    if box is None or len(acc_det) == 0: return 0.0
    best = 0.0
    for xyxy, conf in zip(acc_det.xyxy, acc_det.confidence):
        if box_iou(box, tuple(map(int,xyxy))) >= SPEC_IOU_REGION:
            best = max(best, float(conf))
    return best


def log_event(evts, etype, data):
    e = {"time": datetime.now().isoformat(), "type": etype, **data}
    evts.append(e)
    log.info(f"[EVENT] {etype} | {data}")


def save_events(evts):
    with open(OUTPUT_LOG,"w",encoding="utf-8") as f:
        json.dump(evts,f,indent=2,ensure_ascii=False)


def draw_alert(frame, x, y, label, score, level=3,
               bg=(0,0,175), border=(0,0,255)):
    colors  = {1:(0,0,140),  2:(0,60,160),  3:(0,0,175)}
    borders = {1:(0,255,255),2:(0,200,255),3:(0,0,255)}
    bg     = colors.get(level, bg)
    border = borders.get(level, border)
    lvl_txt = {1:"best.pt", 2:"hybride", 3:"heuristique"}.get(level,"")

    ov = frame.copy()
    cv2.rectangle(ov,(x-195,y-138),(x+195,y-50),bg,-1)
    cv2.rectangle(ov,(x-198,y-141),(x+198,y-47),border,3)
    cv2.addWeighted(ov,0.68,frame,0.32,0,frame)
    cv2.putText(frame,label,(x-185,y-100),
                cv2.FONT_HERSHEY_SIMPLEX,0.70,(255,255,255),2)
    bar = int(score*3.6)
    cv2.rectangle(frame,(x-185,y-88),(x-185+bar,y-75),(0,220,70),-1)
    cv2.putText(frame,f"conf {score}%  [{lvl_txt}]",
                (x-185,y-62),cv2.FONT_HERSHEY_SIMPLEX,0.40,(255,240,130),1)

# ══════════════════════════════════════════════════════════════════
#  INITIALISATION
# ══════════════════════════════════════════════════════════════════

log.info("═" * 60)
log.info("TRAFIQ AI ENGINE v9.2 — démarrage")

model = YOLO("yolov8n.pt")

if os.path.exists(ACC_WEIGHTS):
    accident_model = YOLO(ACC_WEIGHTS)
    try:
        log.info(f"✓ best.pt chargé — classes : {accident_model.names}")
    except:
        log.info("✓ best.pt chargé")
else:
    accident_model = None
    log.warning("✗ best.pt absent → mode heuristique seul (L3)")

tracker  = sv.ByteTrack()
decision = HybridDecision()
decision.load("trafiq_memory.json")

cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    log.error(f"Impossible d'ouvrir : {VIDEO_PATH}"); exit(1)

fps_src = cap.get(cv2.CAP_PROP_FPS) or 25
W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
log.info(f"Vidéo {W}×{H} @ {fps_src:.1f} fps")

writer = None
if SAVE_VIDEO:
    writer = cv2.VideoWriter(OUTPUT_VIDEO,
                             cv2.VideoWriter_fourcc(*"mp4v"),fps_src,(W,H))

tracks         : dict = {}
# Compteurs corrigés — clé = label de la ligne
count_per_line : dict = {l["label"]: {"up":0,"down":0,"total":0} for l in COUNT_LINES}
pair_states    : dict = {}
blacklist      : dict = {}
fused_since    : dict = {}
confirmed_debris : dict = {}   # tid → score
confirmed_fused  : dict = {}   # tid → score
confirmed_overturn: dict = {}  # tid → score  ← NOUVEAU
events_log     : list = []
fps_counter          = deque(maxlen=30)

log.info("Boucle principale démarrée...")

# ══════════════════════════════════════════════════════════════════
#  BOUCLE PRINCIPALE
# ══════════════════════════════════════════════════════════════════

while True:
    t0 = time.time()
    ret, frame = cap.read()
    if not ret: break

    now = time.time()

    # Purge blacklist expirée
    for p in [p for p,t in blacklist.items() if now > t]:
        del blacklist[p]

    # ── Détection générale ─────────────────────────────────────────
    results    = model(frame, verbose=False)[0]
    detections = sv.Detections.from_ultralytics(results)
    detections = detections[np.isin(detections.class_id, VEHICLE_CLASSES)]
    detections = tracker.update_with_detections(detections)

    # ── Détection spécialisée ─────────────────────────────────────
    if accident_model is not None:
        acc_results = accident_model(frame, verbose=False)[0]
        acc_det     = sv.Detections.from_ultralytics(acc_results)
    else:
        acc_det = sv.Detections.empty()

    active_ids = set()

    # ── Mise à jour tracks ─────────────────────────────────────────
    for i, (xyxy, tid) in enumerate(zip(detections.xyxy, detections.tracker_id)):
        active_ids.add(tid)
        if tid not in tracks:
            tracks[tid] = VehicleTrack(tid)
        trk = tracks[tid]

        # Récupérer la classe YOLO
        cls_id = int(detections.class_id[i]) if detections.class_id is not None else None
        trk.update_position(xyxy, now, cls_id)
        trk.compute_speed(HISTORY_FRAMES)

        # ── Comptage lignes (FIX affichage ???)
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
                    log_event(events_log,"CROSS_DOWN",
                              {"id":tid,"line":lbl,"v":round(trk.speed,1)})
                elif cy_p > ly >= cy_c:
                    trk.counted_lines.add(lbl)
                    count_per_line[lbl]["up"]    += 1
                    count_per_line[lbl]["total"] += 1
                    log_event(events_log,"CROSS_UP",
                              {"id":tid,"line":lbl,"v":round(trk.speed,1)})

        # ── Statique
        med_cal = trk.speed_median(STATIC_MEDIAN_WINDOW)
        med_raw = trk.raw_median(10)
        is_slow = med_cal < STATIC_MEDIAN_MAX and med_raw < STATIC_RAW_MAX
        if is_slow:
            if trk.static_since is None and trk.frames_seen >= STATIC_MIN_FRAMES:
                trk.static_since = now
            if (trk.static_since and now - trk.static_since > STATIC_CONFIRM_S
                    and not trk.is_static):
                trk.is_static = True
                log_event(events_log,"STATIC",{"id":tid,"pos":trk.center})
        else:
            if trk.is_static:
                log_event(events_log,"STATIC_CLEARED",{"id":tid})
            trk.is_static = False; trk.static_since = None

        # ── [NOUVEAU] Voiture renversée / accidentée
        if is_overturned_vehicle(trk):
            if trk.overturn_since is None:
                trk.overturn_since = now
            dur  = now - trk.overturn_since
            spec = best_spec_conf(acc_det, trk.box)
            key_o = ("overturn", tid)
            if decision.evaluate(key_o, 78, 70, dur, spec, 0, now,
                                 {"overturn":True, "ratio":round(trk.box_wh_ratio(),2),
                                  "dur":round(dur,1)}):
                confirmed_overturn[tid] = decision.get_score(key_o)
                log_event(events_log,"ACCIDENT_OVERTURN",{
                    "id":tid,"dur_s":round(dur,2),
                    "wh_ratio":round(trk.box_wh_ratio(),2),
                    "pos":trk.center,
                    "level":decision.get_level(key_o)
                })
        else:
            if trk.overturn_since and tid not in confirmed_overturn:
                trk.overturn_since = None

        # ── [B] Débris
        m_raw = trk.raw_median(10)
        m_cal = trk.speed_median(10)
        if is_debris_box(trk.box, m_raw, m_cal) and not trk.is_large_vehicle():
            if trk.debris_since is None: trk.debris_since = now
            dur  = now - trk.debris_since
            spec = best_spec_conf(acc_det, trk.box)
            key_d = ("debris", tid)
            if decision.evaluate(key_d, 82, 75, dur, spec, 0, now,
                                 {"debris":True,"dur":round(dur,1)}):
                confirmed_debris[tid] = decision.get_score(key_d)
                log_event(events_log,"ACCIDENT_DEBRIS",{
                    "id":tid,"dur_s":round(dur,2),
                    "raw_v":round(m_raw,1),"pos":trk.center,
                    "level":decision.get_level(key_d)
                })
        else:
            trk.debris_since = None

        # ── [C] Fusionné
        if is_fused_box(trk.box) and not trk.is_large_vehicle():
            if tid not in fused_since: fused_since[tid] = now
            dur   = now - fused_since[tid]
            pre_v = trk.max_speed_window(20,50)
            spec  = best_spec_conf(acc_det, trk.box)
            key_f = ("fused", tid)
            if pre_v > FUSED_PRE_V_MIN:
                if decision.evaluate(key_f, 85, 80, dur, spec, 0, now,
                                     {"fused":True,"pre_v":round(pre_v,1)}):
                    confirmed_fused[tid] = decision.get_score(key_f)
                    log_event(events_log,"ACCIDENT_FUSED",{
                        "id":tid,"dur":round(dur,2),"pre_v":round(pre_v,1),
                        "pos":trk.center,"level":decision.get_level(key_f)
                    })
        else:
            fused_since.pop(tid, None)

    # Purge TTL
    for tid in [tid for tid,trk in tracks.items() if not trk.is_alive(now)]:
        del tracks[tid]
        for p in [p for p in pair_states if tid in p]:
            pair_states.pop(p,None)
        fused_since.pop(tid, None)

    # ── [A] Paires ────────────────────────────────────────────────
    active = {tid: tracks[tid] for tid in active_ids if tid in tracks}

    for id1,id2 in spatial_pairs(active):
        t1, t2 = active[id1], active[id2]
        if t1.box is None or t2.box is None: continue

        # Exclure paires impliquant un bus/camion
        if pair_has_large_vehicle(t1, t2): continue

        iou  = box_iou(t1.box, t2.box)
        dist = cdist(t1, t2)
        pair = (id1, id2)

        if pair in blacklist: continue

        in_contact = iou > OVERLAP_IOU_MIN or dist < PROXIMITY_PX

        if in_contact:
            avg_sz = (t1.box_size()+t2.box_size())/2.0
            if pair not in pair_states:
                pair_states[pair] = PairState(now, dist, avg_sz)

            ps          = pair_states[pair]
            sc,d,hb,thr = compute_pair_score(t1,t2,iou,ps.duration)
            ps.update(now, dist, sc, hb)

            if ps.separated:
                blacklist[pair] = now + BLACKLIST_DURATION_S
                pair_states.pop(pair, None)
                if decision.is_confirmed(pair):
                    decision.check_correction(pair, now, t1, t2, dist*3)
                    log_event(events_log,"INVALIDATED",
                              {"ids":list(pair),"reason":"separation"})
                continue

            merged = (min(t1.box[0],t2.box[0]), min(t1.box[1],t2.box[1]),
                      max(t1.box[2],t2.box[2]), max(t1.box[3],t2.box[3]))
            spec_conf = best_spec_conf(acc_det, merged)

            if decision.is_confirmed(pair):
                decision.update_spec(pair, spec_conf, now)

            newly = decision.evaluate(pair, sc, thr, ps.duration,
                                      spec_conf, dist, now, d)
            if newly:
                log_event(events_log,"ACCIDENT_PAIR",{
                    "ids":list(pair),"score":decision.get_score(pair),
                    "level":decision.get_level(pair),
                    "details":d,
                    "v1":round(t1.speed,1),"v2":round(t2.speed,1),
                })

            decision.check_correction(pair, now, t1, t2, dist)

        else:
            if pair in pair_states:
                ps = pair_states[pair]
                ps.update(now, dist, ps.max_score, ps.has_brake)
                if ps.separated and decision.is_confirmed(pair):
                    decision.check_correction(pair, now, t1, t2, dist*3)
                    blacklist[pair] = now + BLACKLIST_DURATION_S
                    log_event(events_log,"INVALIDATED",
                              {"ids":list(pair),"reason":"post_sep"})
                if now - ps.since > SEP_WINDOW_S + 2:
                    pair_states.pop(pair, None)

    # ── best.pt détections indépendantes (haute confiance seulement)
    if len(acc_det) > 0:
        for xyxy, conf, cls_id in zip(acc_det.xyxy,
                                      acc_det.confidence,
                                      acc_det.class_id):
            conf_f = float(conf)
            if conf_f < SPEC_CONF_STRONG: continue

            x1,y1,x2,y2 = map(int, xyxy)
            cx,cy = (x1+x2)//2, (y1+y2)//2
            score = int(conf_f * 100)

            # Pas déjà couverte
            covered = any(
                decision.is_confirmed(p) and
                isinstance(p, tuple) and len(p)==2 and isinstance(p[0],int) and
                (ta:=active.get(p[0])) is not None and
                (tb:=active.get(p[1])) is not None and
                ta.box and tb.box and
                box_iou(
                    (min(ta.box[0],tb.box[0]),min(ta.box[1],tb.box[1]),
                     max(ta.box[2],tb.box[2]),max(ta.box[3],tb.box[3])),
                    (x1,y1,x2,y2)
                ) > 0.20
                for p in list(decision.confirmed.keys())
            )
            if covered: continue

            key_s = ("spec_alone", cx//50, cy//50)
            if decision.evaluate(key_s, score, score, 0.0,
                                 conf_f, 0, now,
                                 {"spec_only":True,"conf":round(conf_f,3)}):
                cv2.rectangle(frame,(x1,y1),(x2,y2),(0,200,255),3)
                draw_alert(frame, cx, cy, f"ACCIDENT [best.pt] {score}%",
                           score, level=1, bg=(100,0,0), border=(0,200,255))
                log_event(events_log,"ACCIDENT_SPECIALISE",{
                    "conf":round(conf_f,3),"pos":(cx,cy),"box":[x1,y1,x2,y2]
                })

    # ══════════════════════════════════════════════════════════════
    #  DESSIN
    # ══════════════════════════════════════════════════════════════

    # Lignes de comptage — FIX affichage
    for line in COUNT_LINES:
        ly, col = line["y"], line["color"]
        cv2.line(frame,(0,ly),(W,ly),col,2)
        s = count_per_line[line["label"]]
        label_txt = f"{line['label']}  ↓{s['down']}  ↑{s['up']}"
        cv2.putText(frame, label_txt,
                    (10,ly-8), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, col, 2, cv2.LINE_AA)

    # Zones candidates (orange) — exclure bus
    for pair, ps in pair_states.items():
        if decision.is_confirmed(pair) or pair in blacklist: continue
        id1,id2 = pair
        t1,t2 = active.get(id1), active.get(id2)
        if t1 and t2 and t1.box and t2.box:
            if pair_has_large_vehicle(t1,t2): continue  # ← exclut bus
            if size_mismatch(t1,t2): continue
            x1s=min(t1.box[0],t2.box[0])-6; y1s=min(t1.box[1],t2.box[1])-6
            x2s=max(t1.box[2],t2.box[2])+6; y2s=max(t1.box[3],t2.box[3])+6
            cv2.rectangle(frame,(x1s,y1s),(x2s,y2s),(0,140,255),2)
            cv2.putText(frame,f"? {ps.max_score}%",(x1s,y1s-6),
                        cv2.FONT_HERSHEY_SIMPLEX,0.44,(0,200,255),1)

    # Boîtes véhicules
    for tid, trk in active.items():
        if trk.box is None: continue
        x1,y1,x2,y2 = trk.box
        spd = int(trk.speed)

        is_acc = (
            any(decision.is_confirmed(p)
                for p in decision.confirmed
                if isinstance(p,tuple) and len(p)==2
                and isinstance(p[0],int) and tid in p)
            or tid in confirmed_fused
            or tid in confirmed_debris
            or tid in confirmed_overturn
        )

        if is_acc:
            color = (0,0,255)
            label = f"ACCIDENT #{tid}  {spd}px/s"
            cv2.rectangle(frame,(x1-3,y1-3),(x2+3,y2+3),(0,0,255),4)
        elif trk.is_static:
            color = (160,160,160); label = f"STATIQUE #{tid}"
        elif trk.speed > MOVING_SPEED:
            color = (0,255,0)
            label = f"#{tid}  {spd}px/s  {trk.direction_str or ''}"
        else:
            color = (0,200,200); label = f"#{tid}  {spd}px/s"

        cv2.rectangle(frame,(x1,y1),(x2,y2),color,2)
        (tw,th),_ = cv2.getTextSize(label,cv2.FONT_HERSHEY_SIMPLEX,0.55,2)
        cv2.rectangle(frame,(x1,y1-th-14),(x1+tw+4,y1-2),(0,0,0),-1)
        cv2.putText(frame,label,(x1+2,y1-8),
                    cv2.FONT_HERSHEY_SIMPLEX,0.55,color,2)

    # Alertes paires
    for key, c in list(decision.confirmed.items()):
        if not (isinstance(key,tuple) and len(key)==2
                and isinstance(key[0],int)): continue
        id1,id2 = key
        trk = active.get(id1) or active.get(id2)
        if trk and trk.center:
            draw_alert(frame,*trk.center,
                       f"ACCIDENT #{id1}<->{id2}",
                       c["score"],level=c["level"])

    # Alertes renversement ← NOUVEAU
    for tid, sc in confirmed_overturn.items():
        trk = active.get(tid)
        if trk and trk.center:
            lv = decision.get_level(("overturn",tid))
            draw_alert(frame,*trk.center,
                       f"ACCIDENT #{tid} [renverse]",
                       sc, level=lv, bg=(140,0,80), border=(255,0,180))

    # Alertes fusionnées
    for tid, sc in confirmed_fused.items():
        trk = active.get(tid)
        if trk and trk.center:
            lv = decision.get_level(("fused",tid))
            draw_alert(frame,*trk.center,
                       f"ACCIDENT #{tid} [fusionne]",sc,level=lv)

    # Alertes débris
    for tid, sc in confirmed_debris.items():
        trk = active.get(tid)
        if trk and trk.center:
            lv = decision.get_level(("debris",tid))
            draw_alert(frame,*trk.center,
                       f"ACCIDENT #{tid} [epave]",sc,
                       level=lv,bg=(80,0,160),border=(160,0,255))

    # HUD
    fps_counter.append(1.0/max(1e-9, time.time()-t0))
    rfps   = np.mean(fps_counter)
    total  = sum(v["total"] for v in count_per_line.values())
    nb_acc = len([k for k in decision.confirmed
                  if isinstance(k,tuple) and k[0] not in ("spec_alone",)])
    nb_cor = len(decision.corrections)
    spec_s = "best.pt ON" if accident_model else "heuristique"

    cv2.rectangle(frame,(0,0),(700,70),(15,15,15),-1)
    cv2.putText(frame,
                f"Vehicules:{total}  Accidents:{nb_acc}  "
                f"Corrections:{nb_cor}  FPS:{rfps:.1f}  [{spec_s}]",
                (10,46),cv2.FONT_HERSHEY_SIMPLEX,0.70,(255,255,255),2)

    cv2.imshow("TRAFIQ AI v9.2", frame)
    if writer: writer.write(frame)
    if cv2.waitKey(1) == 27: break

# ══════════════════════════════════════════════════════════════════
cap.release()
if writer: writer.release()
cv2.destroyAllWindows()
save_events(events_log)
decision.save("trafiq_memory.json")

nb_pair = len([k for k in decision.confirmed
               if isinstance(k,tuple) and len(k)==2 and isinstance(k[0],int)])
log.info(f"FINAL — paires:{nb_pair}  renversés:{len(confirmed_overturn)}  "
         f"fused:{len(confirmed_fused)}  debris:{len(confirmed_debris)}  "
         f"corrections:{len(decision.corrections)}")
for lbl,s in count_per_line.items():
    log.info(f"  {lbl} → ↓{s['down']} ↑{s['up']} total={s['total']}")
if decision.corrections:
    log.info(f"CORRECTIONS EFFECTUÉES : {decision.corrections}")
log.info("Terminé.")