from pathlib import Path
from datetime import datetime
import cv2
import numpy as np
import time

BASE_DIR = Path(__file__).resolve().parent.parent
PHOTO_DIR = BASE_DIR / "student_photos"
SAMPLE_DIR = PHOTO_DIR / "samples"
REFERENCE_DIR = PHOTO_DIR / "reference"
CAPTURED_DIR = PHOTO_DIR / "captured"
MODEL_PATH = PHOTO_DIR / "trainer.yml"

PHOTO_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
CAPTURED_DIR.mkdir(parents=True, exist_ok=True)

CASCADE_PATH = str(Path(cv2.__file__).parent / "data" / "haarcascade_frontalface_default.xml")


def open_camera():
    test_options = [
        (0, cv2.CAP_DSHOW),
        (1, cv2.CAP_DSHOW),
        (2, cv2.CAP_DSHOW),
        (0, cv2.CAP_MSMF),
        (1, cv2.CAP_MSMF),
        (2, cv2.CAP_MSMF),
        (0, None),
        (1, None),
        (2, None),
    ]

    for index, backend in test_options:
        if backend is None:
            camera = cv2.VideoCapture(index)
        else:
            camera = cv2.VideoCapture(index, backend)

        if camera is not None and camera.isOpened():
            time.sleep(1.0)
            ret, frame = camera.read()
            if ret and frame is not None:
                return camera
            camera.release()

    return None


def count_face_samples(student_id: int):
    files = list(SAMPLE_DIR.glob(f"user_{student_id}_*.jpg"))
    return len(files)


def capture_faces_for_student(student_id: int, save_count: int = 5):
    detector = cv2.CascadeClassifier(CASCADE_PATH)
    camera = open_camera()

    if camera is None:
        return False, "Could not open webcam. Close other camera apps and try again.", None

    count = count_face_samples(student_id)
    start_count = count
    reference_path = None

    while True:
        ret, frame = camera.read()
        if not ret or frame is None:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

        display = frame.copy()

        for (x, y, w, h) in faces:
            cv2.rectangle(display, (x, y), (x + w, y + h), (0, 255, 0), 2)

        cv2.putText(
            display,
            f"Saved: {count - start_count}/{save_count} | Press S to save | Q to quit",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        cv2.imshow("Face Registration", display)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("s"):
            if len(faces) == 0:
                continue

            x, y, w, h = faces[0]
            face_img = gray[y:y + h, x:x + w]

            count += 1
            sample_path = SAMPLE_DIR / f"user_{student_id}_{count}.jpg"
            cv2.imwrite(str(sample_path), face_img)

            if reference_path is None:
                reference_path = REFERENCE_DIR / f"user_{student_id}_reference.jpg"
                cv2.imwrite(str(reference_path), frame)

            if (count - start_count) >= save_count:
                break

        elif key == ord("q"):
            break

    camera.release()
    cv2.destroyAllWindows()

    saved_now = count - start_count
    if saved_now == 0:
        return False, "No face samples captured.", None

    return True, f"Captured {saved_now} face sample(s).", str(reference_path) if reference_path else None


def train_face_model():
    detector = cv2.CascadeClassifier(CASCADE_PATH)
    image_paths = list(SAMPLE_DIR.glob("*.jpg"))

    faces = []
    ids = []

    for image_path in image_paths:
        img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue

        parts = image_path.stem.split("_")
        if len(parts) < 3:
            continue

        try:
            student_id = int(parts[1])
        except ValueError:
            continue

        detected_faces = detector.detectMultiScale(img)

        if len(detected_faces) == 0:
            faces.append(img)
            ids.append(student_id)
        else:
            for (x, y, w, h) in detected_faces:
                faces.append(img[y:y + h, x:x + w])
                ids.append(student_id)

    if not faces:
        return False, 0

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(faces, np.array(ids))
    recognizer.write(str(MODEL_PATH))

    return True, len(set(ids))


def recognize_face_live():
    if not MODEL_PATH.exists():
        return None, None, None, "Model not trained yet."

    detector = cv2.CascadeClassifier(CASCADE_PATH)
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(str(MODEL_PATH))

    camera = open_camera()
    if camera is None:
        return None, None, None, "Could not open webcam. Close other camera apps and try again."

    while True:
        ret, frame = camera.read()
        if not ret or frame is None:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)

        display = frame.copy()
        best_id = None
        best_confidence = None

        for (x, y, w, h) in faces:
            roi = gray[y:y + h, x:x + w]
            student_id, confidence = recognizer.predict(roi)

            if confidence < 75:
                best_id = int(student_id)
                best_confidence = float(confidence)
                label = f"ID {student_id} | Conf {round(confidence, 2)}"
                color = (0, 255, 0)
            else:
                label = f"Unknown | Conf {round(confidence, 2)}"
                color = (0, 0, 255)

            cv2.rectangle(display, (x, y), (x + w, y + h), color, 2)
            cv2.putText(
                display,
                label,
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2
            )

        cv2.putText(
            display,
            "Press S to capture | Q to quit",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

        cv2.imshow("Face Recognition", display)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("s"):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            captured_path = CAPTURED_DIR / f"captured_{timestamp}.jpg"
            cv2.imwrite(str(captured_path), frame)

            camera.release()
            cv2.destroyAllWindows()

            if best_id is not None:
                return best_id, best_confidence, str(captured_path), "Match found."

            return None, best_confidence, str(captured_path), "Record not found."

        elif key == ord("q"):
            break

    camera.release()
    cv2.destroyAllWindows()
    return None, None, None, "Recognition cancelled."