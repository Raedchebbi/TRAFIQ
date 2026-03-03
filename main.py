import cv2
from ultralytics import YOLO

# Charger modèle YOLO
model = YOLO("yolov8n.pt")

# Charger vidéo (mets une vidéo route dans le dossier)
video_path = "videos/traffic.mp4"
cap = cv2.VideoCapture(video_path)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Détection
    results = model(frame)

    # Affichage résultats
    annotated_frame = results[0].plot()

    cv2.imshow("TRAFIQ Detection", annotated_frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
