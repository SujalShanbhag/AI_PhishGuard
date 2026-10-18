import os
import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict, Any

class FaceDetector:
    """
    Robust Face Detector using an ensemble of OpenCV Haar Cascades
    (frontalface_alt2, frontalface_default, frontalface_alt, frontalface_alt_tree, profileface, eyes, upperbody)
    with CLAHE contrast adaptation, multi-scale pyramid handling, multi-rotation recovery, and context expansion.
    """
    def __init__(self, context_margin: float = 0.25):
        self.context_margin = context_margin
        cascade_dir = cv2.data.haarcascades
        
        # Load cascade ensemble
        self.cascades = []
        for name in [
            "haarcascade_frontalface_alt2.xml",
            "haarcascade_frontalface_default.xml",
            "haarcascade_frontalface_alt.xml",
            "haarcascade_frontalface_alt_tree.xml",
            "haarcascade_profileface.xml"
        ]:
            p = os.path.join(cascade_dir, name)
            if os.path.exists(p):
                clf = cv2.CascadeClassifier(p)
                if not clf.empty():
                    self.cascades.append((name, clf))

        mouth_path = os.path.join(cascade_dir, "haarcascade_mcs_mouth.xml")
        if not os.path.exists(mouth_path):
            mouth_path = os.path.join(cascade_dir, "haarcascade_smile.xml")
        self.mouth_cascade = cv2.CascadeClassifier(mouth_path) if os.path.exists(mouth_path) else None

        eye_path = os.path.join(cascade_dir, "haarcascade_eye.xml")
        self.eye_cascade = cv2.CascadeClassifier(eye_path) if os.path.exists(eye_path) else None

        upperbody_path = os.path.join(cascade_dir, "haarcascade_upperbody.xml")
        self.upperbody_cascade = cv2.CascadeClassifier(upperbody_path) if os.path.exists(upperbody_path) else None

        # CLAHE for lighting normalization
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    def _apply_nms(self, boxes: List[List[int]], overlap_thresh: float = 0.35) -> List[List[int]]:
        """Applies true Non-Maximum Suppression without dropping single-detector boxes."""
        if not boxes:
            return []
        arr = np.array(boxes, dtype=np.float32)
        x1 = arr[:, 0]
        y1 = arr[:, 1]
        x2 = arr[:, 0] + arr[:, 2]
        y2 = arr[:, 1] + arr[:, 3]
        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        order = np.argsort(areas)[::-1]
        keep = []
        while len(order) > 0:
            i = order[0]
            keep.append(i)
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            w = np.maximum(0.0, xx2 - xx1 + 1)
            h = np.maximum(0.0, yy2 - yy1 + 1)
            inter = w * h
            ovr = inter / (areas[i] + areas[order[1:]] - inter)
            inds = np.where(ovr <= overlap_thresh)[0]
            order = order[inds + 1]
        return arr[keep].astype(int).tolist()

    def _detect_raw_boxes(self, gray_img: np.ndarray, gray_clahe: np.ndarray, gray_eq: np.ndarray) -> List[List[int]]:
        """Scans for faces across multiple cascade models and contrast equalizations."""
        boxes = []
        for name, clf in self.cascades:
            for g in [gray_clahe, gray_img, gray_eq]:
                res = clf.detectMultiScale(
                    g,
                    scaleFactor=1.06,
                    minNeighbors=2,
                    minSize=(20, 20),
                    flags=cv2.CASCADE_SCALE_IMAGE
                )
                for b in res:
                    boxes.append(list(b))
        return boxes

    def _detect_via_eyes(self, gray_img: np.ndarray) -> List[List[int]]:
        """Detects eye pairs and reconstructs the enclosing facial bounding box."""
        if not self.eye_cascade:
            return []
        eyes = self.eye_cascade.detectMultiScale(gray_img, scaleFactor=1.1, minNeighbors=3, minSize=(12, 12))
        if len(eyes) < 2:
            return []
        # Find horizontal pairs of eyes
        face_boxes = []
        for i in range(len(eyes)):
            for j in range(i + 1, len(eyes)):
                e1, e2 = eyes[i], eyes[j]
                if abs(e1[1] - e2[1]) < max(e1[3], e2[3]) * 0.5:  # similar y-level
                    left = min(e1[0], e2[0])
                    right = max(e1[0] + e1[2], e2[0] + e2[2])
                    eye_dist = right - left
                    if 15 < eye_dist < gray_img.shape[1] * 0.8:
                        fw = int(eye_dist * 2.0)
                        fh = int(fw * 1.25)
                        fx = max(0, int((left + right) / 2 - fw / 2))
                        fy = max(0, int(min(e1[1], e2[1]) - fh * 0.35))
                        face_boxes.append([fx, fy, fw, fh])
        return face_boxes

    def _detect_via_upperbody(self, gray_img: np.ndarray) -> List[List[int]]:
        """Identifies head region from upper-body detections in ID documents and portraits."""
        if not self.upperbody_cascade:
            return []
        bodies = self.upperbody_cascade.detectMultiScale(gray_img, scaleFactor=1.1, minNeighbors=2, minSize=(50, 50))
        head_boxes = []
        for (bx, by, bw, bh) in bodies:
            hw = int(bw * 0.55)
            hh = int(bh * 0.45)
            hx = int(bx + (bw - hw) / 2)
            hy = int(by)
            head_boxes.append([hx, hy, hw, hh])
        return head_boxes

    def detect_faces(self, image_bgr: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detects faces in BGR image using multi-pass ensemble, multi-angle rotation,
        eye-pair reconstruction, and document photo detection.
        Guarantees high recall across standard portraits, selfies, documents, and ID photos.
        """
        if image_bgr is None or image_bgr.size == 0:
            return []

        h, w = image_bgr.shape[:2]
        if h < 15 or w < 15:
            return []

        # Resize for faster and more reliable detection if image is very large
        scale = 1.0
        max_dim = max(h, w)
        if max_dim > 1400:
            scale = 1400.0 / max_dim
            proc_w = int(w * scale)
            proc_h = int(h * scale)
            proc_img = cv2.resize(image_bgr, (proc_w, proc_h), interpolation=cv2.INTER_AREA)
        else:
            proc_img = image_bgr

        all_raw_boxes = []

        # Pass 1: Standard upright orientation
        gray = cv2.cvtColor(proc_img, cv2.COLOR_BGR2GRAY)
        gray_clahe = self.clahe.apply(gray)
        gray_eq = cv2.equalizeHist(gray)
        all_raw_boxes = self._detect_raw_boxes(gray, gray_clahe, gray_eq)

        # Pass 2: Multi-Orientation Rotation Recovery (90 deg, 270 deg, 180 deg)
        # Crucial for smartphone portrait captures with missing or non-standard EXIF tags
        rot_angle = 0
        if len(all_raw_boxes) == 0:
            for angle, code in [
                (90, cv2.ROTATE_90_CLOCKWISE),
                (270, cv2.ROTATE_90_COUNTERCLOCKWISE),
                (180, cv2.ROTATE_180)
            ]:
                rotated = cv2.rotate(proc_img, code)
                r_gray = cv2.cvtColor(rotated, cv2.COLOR_BGR2GRAY)
                r_clahe = self.clahe.apply(r_gray)
                r_eq = cv2.equalizeHist(r_gray)
                r_boxes = self._detect_raw_boxes(r_gray, r_clahe, r_eq)
                if len(r_boxes) > 0:
                    rot_angle = angle
                    # Map coordinates back to proc_img space
                    rh, rw = rotated.shape[:2]
                    for (rx, ry, r_w, r_h) in r_boxes:
                        if angle == 90:
                            # 90 deg clockwise: (x_rot, y_rot) -> orig_x = y_rot, orig_y = pw - x_rot - w_rot
                            orig_x = ry
                            orig_y = proc_img.shape[0] - rx - r_w
                            orig_w, orig_h = r_h, r_w
                        elif angle == 270:
                            orig_x = proc_img.shape[1] - ry - r_h
                            orig_y = rx
                            orig_w, orig_h = r_h, r_w
                        else:  # 180
                            orig_x = proc_img.shape[1] - rx - r_w
                            orig_y = proc_img.shape[0] - ry - r_h
                            orig_w, orig_h = r_w, r_h
                        all_raw_boxes.append([orig_x, orig_y, orig_w, orig_h])
                    break

        # Pass 3: Eye-pair reconstruction
        if len(all_raw_boxes) == 0:
            eye_boxes = self._detect_via_eyes(gray_clahe)
            all_raw_boxes.extend(eye_boxes)

        # Pass 4: Upper-body / portrait detector
        if len(all_raw_boxes) == 0:
            body_boxes = self._detect_via_upperbody(gray_clahe)
            all_raw_boxes.extend(body_boxes)

        # Pass 5: Skin-tone / facial contour detection for ID cards & documents
        if len(all_raw_boxes) == 0:
            ycrcb = cv2.cvtColor(proc_img, cv2.COLOR_BGR2YCrCb)
            lower_skin = np.array([0, 133, 77], dtype=np.uint8)
            upper_skin = np.array([255, 173, 127], dtype=np.uint8)
            skin_mask = cv2.inRange(ycrcb, lower_skin, upper_skin)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            min_face_area = (proc_img.shape[0] * proc_img.shape[1]) * 0.010
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area > min_face_area:
                    bx, by, bw, bh = cv2.boundingRect(cnt)
                    aspect = bh / float(bw) if bw > 0 else 0
                    if 0.75 <= aspect <= 2.2:  # Portrait face aspect ratio
                        all_raw_boxes.append([bx, by, bw, bh])

        if len(all_raw_boxes) == 0:
            return []

        # Scale coordinates back to original unresized image dimensions
        boxes_scaled = []
        for (rx, ry, rw, rh) in all_raw_boxes:
            orig_x = int(rx / scale)
            orig_y = int(ry / scale)
            orig_w = int(rw / scale)
            orig_h = int(rh / scale)
            orig_x = max(0, min(w - 10, orig_x))
            orig_y = max(0, min(h - 10, orig_y))
            orig_w = min(w - orig_x, orig_w)
            orig_h = min(h - orig_y, orig_h)
            if orig_w >= 15 and orig_h >= 15:
                boxes_scaled.append([orig_x, orig_y, orig_w, orig_h])

        # Apply robust IoU Non-Maximum Suppression
        final_boxes = self._apply_nms(boxes_scaled, overlap_thresh=0.35)

        detected_faces = []
        for (x, y, fw, fh) in final_boxes:
            margin_x = int(fw * self.context_margin)
            margin_y = int(fh * self.context_margin)

            x1 = max(0, x - margin_x)
            y1 = max(0, y - margin_y)
            x2 = min(w, x + fw + margin_x)
            y2 = min(h, y + fh + margin_y)

            face_crop = image_bgr[y1:y2, x1:x2].copy()
            if face_crop.size == 0 or face_crop.shape[0] < 10 or face_crop.shape[1] < 10:
                continue

            mouth_crop = None
            if self.mouth_cascade:
                mouth_roi_y1 = int(fh * 0.55)
                face_lower = gray[int(y*scale + mouth_roi_y1*scale) : int((y + fh)*scale), int(x*scale) : int((x + fw)*scale)]
                if face_lower.size > 0:
                    mouths = self.mouth_cascade.detectMultiScale(face_lower, 1.2, 4, minSize=(14, 10))
                    if len(mouths) > 0:
                        mx, my, mw, mh = mouths[0]
                        orig_mx = int((x*scale + mx) / scale)
                        orig_my = int((y*scale + mouth_roi_y1*scale + my) / scale)
                        orig_mw = int(mw / scale)
                        orig_mh = int(mh / scale)
                        mouth_crop = image_bgr[orig_my : orig_my + orig_mh, orig_mx : orig_mx + orig_mw]

            detected_faces.append({
                "bbox": (int(x), int(y), int(fw), int(fh)),
                "expanded_bbox": (int(x1), int(y1), int(x2), int(y2)),
                "face_crop": face_crop,
                "mouth_crop": mouth_crop,
                "area": int(fw * fh),
            })

        detected_faces.sort(key=lambda item: item["area"], reverse=True)
        return detected_faces

    def extract_fallback_region(self, image_bgr: np.ndarray) -> np.ndarray:
        """
        When no distinct face is found, extracts the salient central region of the image
        so that deepfake neural inference and Grad-CAM can analyze whole-image synthetic artifacts.
        """
        if image_bgr is None or image_bgr.size == 0:
            return np.zeros((224, 224, 3), dtype=np.uint8)

        h, w = image_bgr.shape[:2]
        # Central 80% crop
        start_y = int(h * 0.10)
        end_y = int(h * 0.90)
        start_x = int(w * 0.10)
        end_x = int(w * 0.90)

        crop = image_bgr[start_y:end_y, start_x:end_x]
        return crop if crop.size > 0 else image_bgr.copy()

    def extract_face_embedding(self, face_crop: np.ndarray) -> np.ndarray:
        """
        Extracts a normalized facial embedding vector for privacy-preserving identity comparison.
        """
        if face_crop is None or face_crop.size == 0:
            return np.zeros(256, dtype=np.float32)

        resized = cv2.resize(face_crop, (128, 128))
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        
        # Color histogram (HSV)
        hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
        hist_h = cv2.calcHist([hsv], [0], None, [32], [0, 180]).flatten()
        hist_s = cv2.calcHist([hsv], [1], None, [32], [0, 256]).flatten()
        
        # Edge gradient histogram (Sobel)
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        mag, ang = cv2.cartToPolar(gx, gy, angleInDegrees=True)
        hist_edge = cv2.calcHist([ang], [0], None, [64], [0, 360]).flatten()

        # Multi-region intensity pooling (4x4 grid)
        blocks = []
        step = 128 // 4
        for r in range(4):
            for c in range(4):
                block = gray[r * step : (r + 1) * step, c * step : (c + 1) * step]
                blocks.append(np.mean(block))
                blocks.append(np.std(block))

        embedding = np.concatenate([hist_h, hist_s, hist_edge, np.array(blocks, dtype=np.float32)])
        norm = np.linalg.norm(embedding)
        if norm > 1e-6:
            embedding = embedding / norm
        return embedding.astype(np.float32)


face_detector = FaceDetector()
