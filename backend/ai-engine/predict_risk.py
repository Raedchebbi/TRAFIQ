from ultralytics import YOLO
import cv2
import math
import json
import datetime
import os
import numpy as np
from collections import deque
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# ================= CONFIG =================
MODEL_VEHICLE_PATH = "models/vehicule-model.pt"
VIDEO_PATH = "accident0.mp4"
LOG_PATH = "predictions_log.json"

HISTORY_SIZE = 10
MIN_SAFE_DISTANCE = 80
TTC_DANGER_THRESHOLD = 30
DECELERATION_THRESHOLD = 8
DENSITY_HIGH = 5
RISK_ALERT_THRESHOLD = 65
ALERT_COOLDOWN_FRAMES = 150

# K-Means : 3 clusters (normal, risque, critique)
N_CLUSTERS = 3
kmeans = None
scaler = StandardScaler()
data_buffer = []
KMEANS_MIN_SAMPLES = 30  # samples minimum avant de fitter K-Means

print("Loading vehicle model...")
vehicle_model = YOLO(MODEL_VEHICLE_PATH)
print("Model loaded.")

vehicle_history = {}  # {id: deque([(cx, cy, speed), ...])}


# ==========================================
#              FONCTIONS UTILITAIRES
# ==========================================

def get_speed(vid, cx, cy):
    if vid in vehicle_history and len(vehicle_history[vid]) > 0:
        last = vehicle_history[vid][-1]
        dx = cx - last[0]
        dy = cy - last[1]
        return math.sqrt(dx * dx + dy * dy)
    return 0


def get_deceleration(vid, current_speed):
    if vid in vehicle_history and len(vehicle_history[vid]) >= 5:
        past_speeds = [h[2] for h in list(vehicle_history[vid])[-5:]]
        avg_past_speed = sum(past_speeds) / len(past_speeds)
        return max(0, avg_past_speed - current_speed)
    return 0


def compute_ttc(dist, speed_a, speed_b):
    relative_speed = speed_a + speed_b
    if relative_speed < 1:
        return 999
    return dist / relative_speed


def get_min_distance(vid, cx, cy, vehicles_data):
    min_dist = 999
    for other_vid, other_cx, other_cy, _, _ in vehicles_data:
        if other_vid != vid:
            dist = math.sqrt((cx - other_cx) ** 2 + (cy - other_cy) ** 2)
            if dist < min_dist:
                min_dist = dist
    return min_dist


def get_min_ttc(speed, vehicles_data, cx, cy, vid):
    min_ttc = 999
    for other_vid, other_cx, other_cy, other_speed, _ in vehicles_data:
        if other_vid != vid:
            dist = math.sqrt((cx - other_cx) ** 2 + (cy - other_cy) ** 2)
            ttc = compute_ttc(dist, speed, other_speed)
            if ttc < min_ttc:
                min_ttc = ttc
    return min_ttc


# ==========================================
#         K-MEANS CLUSTERING
# ==========================================

def extract_features(vid, cx, cy, speed, decel, vehicles_data):
    """
    Features utilisées par K-Means :
    [vitesse, décélération, distance_min_avec_voisin, ttc_min, densité_trafic]
    """
    min_dist = get_min_distance(vid, cx, cy, vehicles_data)
    min_ttc = get_min_ttc(speed, vehicles_data, cx, cy, vid)
    density = len(vehicles_data)
    return [speed, decel, min_dist, min_ttc, density]


def fit_kmeans(data):
    """Entraîne K-Means sur les données collectées"""
    global kmeans, scaler
    X = np.array(data)
    X_scaled = scaler.fit_transform(X)
    kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=10)
    kmeans.fit(X_scaled)
    print("✅ K-Means model fitted successfully!")


def get_cluster_risk(features):
    """Calcule le risk score basé sur les features du véhicule"""
    speed, decel, min_dist, min_ttc, density = features
    risk = 0
    if decel > DECELERATION_THRESHOLD:
        risk += 30
    if min_dist < MIN_SAFE_DISTANCE:
        risk += 25
    if min_ttc < TTC_DANGER_THRESHOLD:
        risk += 35
    if density >= DENSITY_HIGH:
        risk += 10
    return min(risk, 100)


def predict_cluster(features):
    """Prédit le cluster K-Means d'un véhicule"""
    global kmeans, scaler
    if kmeans is None:
        return None
    X = np.array([features])
    X_scaled = scaler.transform(X)
    return int(kmeans.predict(X_scaled)[0])


# ==========================================
#         RISK LEVEL ET AFFICHAGE
# ==========================================

def get_risk_level(score):
    if score >= 80:
        return "CRITICAL", (0, 0, 255)
    elif score >= 60:
        return "HIGH", (0, 100, 255)
    elif score >= 30:
        return "MEDIUM", (0, 255, 255)
    else:
        return "LOW", (0, 255, 0)


def save_prediction(risk_score, risk_level, cluster_info, frame, frame_idx):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pred_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_path = f"pred_snapshot_{pred_id}.jpg"
    cv2.imwrite(snapshot_path, frame)

    prediction = {
        "prediction_id": pred_id,
        "frame": frame_idx,
        "timestamp": timestamp,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "kmeans_clusters": cluster_info,
        "snapshot": snapshot_path,
        "model": "KMeans-clustering + YOLO"
    }

    logs = []
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, "r") as f:
            try:
                logs = json.load(f)
            except Exception:
                logs = []
    logs.append(prediction)
    with open(LOG_PATH, "w") as f:
        json.dump(logs, f, indent=4)

    print(f"⚠️  RISK ALERT | Score: {risk_score} | Level: {risk_level} | Clusters: {cluster_info}")


# ==========================================
#              MAIN LOOP
# ==========================================

cap = cv2.VideoCapture(VIDEO_PATH)
frame_idx = 0
alert_cooldown = 0
kmeans_fitted = False

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_idx += 1

    results = vehicle_model.track(frame, persist=True, conf=0.4, verbose=False)
    annotated_frame = results[0].plot()

    vehicles_data = []

    if results[0].boxes.id is not None:
        ids = results[0].boxes.id.cpu().numpy()
        xyxy = results[0].boxes.xyxy.cpu().numpy()

        for i, box in enumerate(xyxy):
            x1, y1, x2, y2 = box
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            vid = int(ids[i])

            speed = get_speed(vid, cx, cy)
            decel = get_deceleration(vid, speed)

            if vid not in vehicle_history:
                vehicle_history[vid] = deque(maxlen=HISTORY_SIZE)
            vehicle_history[vid].append((cx, cy, speed))

            vehicles_data.append((vid, cx, cy, speed, decel))

    # --- Collecte features + Prédiction K-Means ---
    frame_risk_scores = []
    cluster_info = []

    for vid, cx, cy, speed, decel in vehicles_data:
        features = extract_features(vid, cx, cy, speed, decel, vehicles_data)
        data_buffer.append(features)

        # Fit K-Means une fois qu'on a assez de données
        if not kmeans_fitted and len(data_buffer) >= KMEANS_MIN_SAMPLES:
            fit_kmeans(data_buffer)
            kmeans_fitted = True

        if kmeans_fitted:
            cluster = predict_cluster(features)
            risk_score = get_cluster_risk(features)
            frame_risk_scores.append(risk_score)
            cluster_info.append({
                "vehicle_id": int(vid),
                "cluster": cluster,
                "risk_score": risk_score
            })
        else:
            # Affiche progression pendant la collecte
            cv2.rectangle(annotated_frame, (10, 10), (450, 60), (20, 20, 20), -1)
            cv2.putText(annotated_frame,
                        f"K-Means: collecting data {len(data_buffer)}/{KMEANS_MIN_SAMPLES}",
                        (15, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (200, 200, 200), 2)

    # --- Affichage Risk Score global ---
    if frame_risk_scores and kmeans_fitted:
        global_risk = max(frame_risk_scores)
        risk_level, color = get_risk_level(global_risk)

        cv2.rectangle(annotated_frame, (10, 10), (450, 100), (20, 20, 20), -1)
        cv2.putText(annotated_frame, f"RISK SCORE: {global_risk}/100",
                    (15, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
        cv2.putText(annotated_frame, f"LEVEL: {risk_level}  [K-Means AI]",
                    (15, 78), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        if global_risk >= RISK_ALERT_THRESHOLD and alert_cooldown == 0:
            save_prediction(global_risk, risk_level, cluster_info, frame, frame_idx)
            alert_cooldown = ALERT_COOLDOWN_FRAMES

    if alert_cooldown > 0:
        alert_cooldown -= 1

    cv2.imshow("TRAFIQ - AI Risk Prediction [K-Means]", annotated_frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
print("Done.")
