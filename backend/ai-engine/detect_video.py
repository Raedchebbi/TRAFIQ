from ultralytics import YOLO
import cv2
import json
import datetime
import os
import math
from itertools import combinations

# ================= CONFIG =================

MODEL_VEHICLE_PATH = "C:/Users/Malek/Desktop/TRAFIQ/backend/ai-engine/models/vehicule-model.pt"
MODEL_CRASH_PATH = "C:/Users/Malek/Desktop/TRAFIQ/backend/ai-engine/models/crash-model.pt"
VIDEO_PATH = "accident0.mp4"

BASE_CONF = 0.4
IOU_THRESHOLD = 0.4
DIST_DROP_THRESHOLD = 25
SPEED_DROP_THRESHOLD = 15
CONFIRMATION_FRAMES = 2
COOLDOWN_FRAMES = 400
LOG_PATH = "incidents_log.json"


print("Loading model...")
vehicle_model = YOLO(MODEL_VEHICLE_PATH)
print("Model loaded.")


def compute_iou(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    inter = max(0, xB-xA) * max(0, yB-yA)
    areaA = (boxA[2]-boxA[0])*(boxA[3]-boxA[1])
    areaB = (boxB[2]-boxB[0])*(boxB[3]-boxB[1])
    union = areaA + areaB - inter

    if union == 0:
        return 0
    return inter/union



cap = cv2.VideoCapture(VIDEO_PATH)

vehicle_memory = {}  
collision_streak = 0
cooldown = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = vehicle_model.track(frame, persist=True, conf=BASE_CONF, verbose=False)

    annotated_frame = results[0].plot()

    boxes = []
    centers = {}
    speeds = {}

    if results[0].boxes.id is not None:

        ids = results[0].boxes.id.cpu().numpy()
        xyxy = results[0].boxes.xyxy.cpu().numpy()

        for i, box in enumerate(xyxy):
            x1, y1, x2, y2 = box
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2

            vid = int(ids[i])
            centers[vid] = (cx, cy)
            boxes.append((vid, [x1, y1, x2, y2]))

            if vid in vehicle_memory:
                dx = cx - vehicle_memory[vid][0]
                dy = cy - vehicle_memory[vid][1]
                speed = math.sqrt(dx*dx + dy*dy)
                speeds[vid] = speed
            else:
                speeds[vid] = 0

        vehicle_memory = centers.copy()

    collision_detected = False

    for (idA, boxA), (idB, boxB) in combinations(boxes, 2):

        iou = compute_iou(boxA, boxB)

        if idA in speeds and idB in speeds:
            speedA = speeds[idA]
            speedB = speeds[idB]

            if (
                iou > IOU_THRESHOLD
                and (speedA < SPEED_DROP_THRESHOLD or speedB < SPEED_DROP_THRESHOLD)
            ):
                collision_detected = True
                print(f"IoU: {iou:.2f} | Speeds: {speedA:.1f}, {speedB:.1f}")
                break

    if collision_detected:
        collision_streak += 1
    else:
        collision_streak = max(0, collision_streak - 1)

    if cooldown > 0:
        cooldown -= 1

    if collision_streak >= CONFIRMATION_FRAMES and cooldown == 0:

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        incident_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_path = f"snapshot_{incident_id}.jpg"

        cv2.imwrite(snapshot_path, frame)

        incident_data = {
            "incident_id": incident_id,
            "incident_type": "vehicle_collision",
            "timestamp": timestamp,
            "snapshot": snapshot_path
        }

        logs = []
        if os.path.exists(LOG_PATH):
            with open(LOG_PATH, "r") as f:
                try:
                    logs = json.load(f)
                except:
                    logs = []

        logs.append(incident_data)

        with open(LOG_PATH, "w") as f:
            json.dump(logs, f, indent=4)

        print("COLLISION CONFIRMED")

        collision_streak = 0
        cooldown = COOLDOWN_FRAMES

    cv2.imshow("TRAFIQ AI", annotated_frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
print("Done.")