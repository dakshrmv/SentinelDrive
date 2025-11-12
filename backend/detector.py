import cv2
import mediapipe as mp
import numpy as np
import time
import math
import os
from datetime import datetime

class DrowsinessDetector:
    def __init__(self):
        print("Initializing DrowsinessDetector...")
        self.ear_thresh = 0.25
        self.mar_thresh = 0.30
        self.gaze_threshold = 0.10
        self.reference_gaze_ratio = None
        self.reference_eye_center = None
        self.eye_center_tolerance = 0.07
        self.recent_eye_positions = []
        self.closed_eye_duration = 1.2
        self.yawn_duration = 1.0
        self.distraction_duration_thresh = 4.0
        self.fatigue_level = 0
        self.warning_lvl = 4
        self.alert_lvl = 8
        # Correct import
        self.mp_face_mesh = mp.solutions.face_mesh
        self.facemesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.LEFT_EYE = [362, 385, 387, 263, 373, 380]
        self.RIGHT_EYE = [33, 160, 158, 133, 153, 144]
        self.LEFT_IRIS = [474, 475, 476, 477]
        self.RIGHT_IRIS = [469, 470, 471, 472]
        self.LEFT_EYE_CORNERS = [362, 263]
        self.RIGHT_EYE_CORNERS = [133, 33]
        self.MOUTH = [13, 14, 78, 308]
        self.eye_closed_start = None
        self.yawn_start = None
        self.distraction_start = None
        self.last_decay = time.time()
        self.ss_dir = "static/screenshots_log"
        os.makedirs(self.ss_dir, exist_ok=True)
        self.last_ss_time = 0
        self.ss_cooldown = 5.0
        self.alarm_playing = False
        self.last_distraction_alert_time = 0
        self.distraction_alert_cooldown = 5.0
        self.consecutive_distraction_frames = 0
        self.distraction_frame_threshold = 10
        self.distraction_active = False
        self.calibrated = False

    def dist(self, p1, p2):
        return math.hypot(p1.x - p2.x, p1.y - p2.y)

    def get_ear(self, lm, eye_idx):
        try:
            p1, p2, p3, p4, p5, p6 = [lm[i] for i in eye_idx]
            v1 = self.dist(p2, p6)
            v2 = self.dist(p3, p5)
            h = self.dist(p1, p4)
            if h < 1e-6:
                return 0.0
            return np.clip((v1 + v2) / (2.0 * h), 0.0, 1.0)
        except:
            return 0.0

    def get_mar(self, lm):
        try:
            top, bottom, left, right = [lm[i] for i in self.MOUTH]
            v = self.dist(top, bottom)
            h = self.dist(left, right)
            return v / h if h > 1e-6 else 0.0
        except:
            return 0.0

    def get_gaze_ratio(self, lm):
        try:
            r_outer, r_inner, r_iris = lm[self.RIGHT_EYE_CORNERS[0]], lm[self.RIGHT_EYE_CORNERS[1]], lm[self.RIGHT_IRIS[0]]
            r_width = self.dist(r_outer, r_inner)
            if r_width < 1e-6:
                return None
            r_pos = self.dist(r_iris, r_outer) / r_width
            l_outer, l_inner, l_iris = lm[self.LEFT_EYE_CORNERS[0]], lm[self.LEFT_EYE_CORNERS[1]], lm[self.LEFT_IRIS[0]]
            l_width = self.dist(l_outer, l_inner)
            if l_width < 1e-6:
                return None
            l_pos = self.dist(l_iris, l_outer) / l_width
            return (l_pos + r_pos) / 2.0
        except:
            return None

    def is_eye_on_camera(self, landmarks):
        if not self.calibrated or self.reference_eye_center is None:
            return True
        try:
            iris_pts = [landmarks[i] for i in self.LEFT_IRIS + self.RIGHT_IRIS]
            cx = np.mean([p.x for p in iris_pts])
            cy = np.mean([p.y for p in iris_pts])
            self.recent_eye_positions.append((cx, cy))
            if len(self.recent_eye_positions) > 5:
                self.recent_eye_positions.pop(0)
            avg_x = np.mean([p[0] for p in self.recent_eye_positions])
            avg_y = np.mean([p[1] for p in self.recent_eye_positions])
            ref_x, ref_y = self.reference_eye_center
            return math.hypot(avg_x - ref_x, avg_y - ref_y) < self.eye_center_tolerance
        except:
            return True

    def take_screenshot(self, frame, event_name):
        now = time.time()
        if now - self.last_ss_time < self.ss_cooldown:
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fn = os.path.join(self.ss_dir, f"{event_name}_{ts}.jpg")
        try:
            cv2.imwrite(fn, frame)
        except Exception as e:
            print(f"Screenshot failed: {e}")
        self.last_ss_time = now

    def analyze_frame(self, frame):
        if time.time() - self.last_decay > 2.0 and self.fatigue_level > 0:
            self.fatigue_level -= 1
            self.last_decay = time.time()
        status, color = "AWAKE", (0, 255, 0)
        ear, mar, gaze_ratio = 0.0, 0.0, None
        distraction_alert_triggered = False
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.facemesh.process(rgb_frame)
        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark
            gaze_ratio = self.get_gaze_ratio(landmarks)
            is_distracted = not self.is_eye_on_camera(landmarks)
            if is_distracted:
                self.consecutive_distraction_frames += 1
                if self.distraction_start is None:
                    self.distraction_start = time.time()
                duration_met = time.time() - self.distraction_start > self.distraction_duration_thresh
                frames_met = self.consecutive_distraction_frames > self.distraction_frame_threshold
                if duration_met and frames_met:
                    self.distraction_active = True
                    current_time = time.time()
                    if current_time - self.last_distraction_alert_time > self.distraction_alert_cooldown:
                        self.take_screenshot(frame, "distraction_alert")
                        self.last_distraction_alert_time = current_time
                        status, color = "ALERT! LOOK AT ROAD!", (0, 0, 255)
                        distraction_alert_triggered = True
                        self.fatigue_level = min(self.fatigue_level + 1, 10)
                        return status, color, ear, mar, self.fatigue_level, gaze_ratio, True, "distraction"
                elif self.consecutive_distraction_frames > 2:
                    status, color = "WARNING! PAY ATTENTION", (0, 165, 255)
                    distraction_alert_triggered = True
            else:
                self.consecutive_distraction_frames = 0
                self.distraction_start = None
                self.distraction_active = False
            if not distraction_alert_triggered:
                ear = (self.get_ear(landmarks, self.LEFT_EYE) + self.get_ear(landmarks, self.RIGHT_EYE)) / 2.0
                mar = self.get_mar(landmarks)
                if ear < self.ear_thresh:
                    if self.eye_closed_start is None:
                        self.eye_closed_start = time.time()
                    elif time.time() - self.eye_closed_start > self.closed_eye_duration:
                        self.fatigue_level = min(self.fatigue_level + 3, 10)
                        self.take_screenshot(frame, "eye_closure_detected")
                        self.eye_closed_start = None
                        return "EYES CLOSED! WAKE UP!", (0, 0, 255), ear, mar, self.fatigue_level, gaze_ratio, True, "eyes_closed"
                else:
                    self.eye_closed_start = None
                if mar > self.mar_thresh:
                    if self.yawn_start is None:
                        self.yawn_start = time.time()
                    elif time.time() - self.yawn_start > self.yawn_duration:
                        self.fatigue_level = min(self.fatigue_level + 2, 10)
                        self.yawn_start = None
                        return "YAWN DETECTED!", (0, 100, 255), ear, mar, self.fatigue_level, gaze_ratio, True, "yawn"
                else:
                    self.yawn_start = None
                if self.fatigue_level >= self.alert_lvl:
                    status, color = "ALERT! DROWSY!", (0, 0, 255)
                    self.take_screenshot(frame, "fatigue_alert")
                    return status, color, ear, mar, self.fatigue_level, gaze_ratio, True, "fatigue_alert"
                elif self.fatigue_level >= self.warning_lvl:
                    status, color = "WARNING: Drowsy", (0, 255, 255)
                    return status, color, ear, mar, self.fatigue_level, gaze_ratio, False, "fatigue_warning"
        return status, color, ear, mar, self.fatigue_level, gaze_ratio, False, None

    def draw_hud(self, frame, status, color, ear, mar, fatigue_level, gaze_ratio):
        h, w = frame.shape[:2]
        overlay = np.zeros_like(frame, dtype=np.uint8)
        cv2.rectangle(overlay, (0, h - 60), (w, h), (0, 0, 0), -1)
        cv2.putText(overlay, f"{status}", (int(w / 2 - 200), h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.1, color, 3)
        gauge_h, gauge_w = 150, 25
        pos_x, pos_y = w - 50, h - 80
        cv2.rectangle(overlay, (pos_x, pos_y - gauge_h), (pos_x + gauge_w, pos_y), (255, 255, 255), 1)
        fatigue_h = int(fatigue_level / 10.0 * gauge_h)
        fatigue_color = (0, 255, 0) if fatigue_level < self.warning_lvl else \
                        (0, 255, 255) if fatigue_level < self.alert_lvl else (0, 0, 255)
        cv2.rectangle(overlay, (pos_x, pos_y - fatigue_h), (pos_x + gauge_w, pos_y), fatigue_color, -1)
        cv2.putText(overlay, "FATIGUE", (pos_x - 65, pos_y - gauge_h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        start_x, start_y = 20, 40
        spacing = 35
        cv2.putText(overlay, f"EAR: {ear:.2f}", (start_x, start_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(overlay, f"MAR: {mar:.2f}", (start_x, start_y + spacing),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        if gaze_ratio is not None:
            cv2.putText(overlay, f"GAZE: {gaze_ratio:.2f}", (start_x, start_y + 2 * spacing),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        return cv2.addWeighted(frame, 1, overlay, 0.8, 0)

    def run_calibration(self, cap, duration=10):
        print("Running calibration for 10 seconds...")
        start_time = time.time()
        gaze_ratios, ear_values, mar_values, eye_centers = [], [], [], []
        while time.time() - start_time < duration:
            ret, frame = cap.read()
            if not ret:
                continue
            h, w = frame.shape[:2]
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.facemesh.process(rgb_frame)
            if results.multi_face_landmarks:
                lm = results.multi_face_landmarks[0].landmark
                gaze = self.get_gaze_ratio(lm)
                if gaze is not None:
                    gaze_ratios.append(gaze)
                ear = (self.get_ear(lm, self.LEFT_EYE) + self.get_ear(lm, self.RIGHT_EYE)) / 2.0
                ear_values.append(ear)
                mar = self.get_mar(lm)
                mar_values.append(mar)
                try:
                    iris_pts = [lm[i] for i in self.LEFT_IRIS + self.RIGHT_IRIS]
                    avg_x = np.mean([p.x for p in iris_pts])
                    avg_y = np.mean([p.y for p in iris_pts])
                    eye_centers.append((avg_x, avg_y))
                except:
                    pass
            cv2.imshow("Calibration...", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        if gaze_ratios:
            self.reference_gaze_ratio = np.mean(gaze_ratios)
        if ear_values:
            self.ear_thresh = np.mean(ear_values) * 0.85
        if mar_values:
            self.mar_thresh = np.mean(mar_values) + 0.08
        if eye_centers:
            self.reference_eye_center = np.mean(eye_centers, axis=0)
        self.calibrated = True
        print("Calibration complete!")
        cv2.destroyWindow("Calibration...")
