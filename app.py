from flask import Flask, render_template, jsonify, request, send_file
import cv2
import threading
import base64
from io import BytesIO
import os
import glob
import json
from datetime import datetime
from backend.detector import DrowsinessDetector

app = Flask(__name__)

# ====== GLOBAL VARIABLES ======
detector = None
cap = None
is_running = False
current_frame = None
frame_lock = threading.Lock()

# Store metrics
latest_metrics = {
    "ear": "--",
    "mar": "--",
    "gaze": "--",
    "fatigue": 0,
    "status": "IDLE"
}

# Session data storage
sessions = {}
current_session = None
metrics_history = []
alert_count = 0

# Driver profiles
driver_profiles = {
    "default": {
        "id": "default",
        "name": "Default Driver",
        "sensitivity": "normal",
        "alert_threshold": 5,
        "language": "en",
        "created_at": datetime.now().isoformat()
    }
}

current_driver = "default"

# Settings
app_settings = {
    "sensitivity": "normal",  # easy, normal, strict
    "alert_threshold": 5,
    "language": "en",
    "notifications": True,
    "auto_export": False,
    "sound_alerts": True,
    "alert_volume": 70
}

# ====== ROUTE: HOME PAGE ======
@app.route('/')
def index():
    return render_template('index.html')

# ====== ROUTE: DETECTION PAGE ======
@app.route('/detection')
def detection():
    return render_template('detection.html')

# ====== ROUTE: ANALYTICS PAGE ======
@app.route('/analytics')
def analytics():
    return render_template('analytics.html')

# ====== ROUTE: SETTINGS PAGE ======
@app.route('/settings')
def settings():
    return render_template('settings.html')

# ====== ROUTE: HISTORY PAGE ======
@app.route('/history')
def history():
    return render_template('history.html')

# ====== ROUTE: PROFILES PAGE ======
@app.route('/profiles')
def profiles():
    return render_template('profiles.html')

# ====== ROUTE: GALLERY PAGE ======
@app.route('/gallery')
def gallery():
    return render_template('gallery.html')

# ====== ROUTE: ABOUT PAGE ======
@app.route('/about')
def about():
    return render_template('about.html')

# ====== API: START DETECTION ======
@app.route('/api/start-detection', methods=['POST'])
def start_detection():
    global detector, cap, is_running, current_session, metrics_history, alert_count
    try:
        detector = DrowsinessDetector()
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            return jsonify({"error": "Could not open webcam"}), 500
        
        # Apply camera settings
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        # Run calibration
        detector.run_calibration(cap, duration=5)
        
        is_running = True
        alert_count = 0
        
        # Create new session
        current_session = {
            "id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "start_time": datetime.now().isoformat(),
            "alerts": 0,
            "total_fatigue": 0,
            "frames_count": 0,
            "driver_id": current_driver,
            "peak_fatigue": 0,
            "avg_ear": 0,
            "avg_mar": 0
        }
        
        metrics_history = []
        
        # Start detection thread
        threading.Thread(target=detection_loop, daemon=True).start()
        
        return jsonify({"status": "Detection started", "session_id": current_session["id"]}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ====== API: STOP DETECTION ======
@app.route('/api/stop-detection', methods=['POST'])
def stop_detection():
    global is_running, cap, current_session, sessions
    
    is_running = False
    
    if cap:
        cap.release()
    
    # Save session
    if current_session:
        current_session["end_time"] = datetime.now().isoformat()
        current_session["duration_seconds"] = (
            datetime.fromisoformat(current_session["end_time"]) - 
            datetime.fromisoformat(current_session["start_time"])
        ).total_seconds()
        
        # Calculate statistics
        if metrics_history:
            current_session["avg_fatigue"] = sum(m["fatigue"] for m in metrics_history) / len(metrics_history)
            current_session["peak_fatigue"] = max(m["fatigue"] for m in metrics_history)
            current_session["avg_ear"] = sum(m["ear"] for m in metrics_history) / len(metrics_history)
            current_session["avg_mar"] = sum(m["mar"] for m in metrics_history) / len(metrics_history)
        
        sessions[current_session["id"]] = current_session
        save_sessions()
    
    return jsonify({"status": "Detection stopped"}), 200

# ====== API: GET FRAME ======
@app.route('/api/frame-b64')
def get_frame_b64():
    global current_frame
    with frame_lock:
        if current_frame is None:
            return jsonify({"error": "No frame available"}), 404
        
        ret, jpeg = cv2.imencode('.jpg', current_frame)
        b64_img = base64.b64encode(jpeg.tobytes()).decode('utf-8')
        return jsonify({"frame": b64_img})

# ====== API: GET METRICS ======
@app.route('/api/metrics')
def api_metrics():
    return jsonify(latest_metrics)

# ====== API: GET METRICS HISTORY ======
@app.route('/api/metrics-history')
def api_metrics_history():
    return jsonify({"history": metrics_history[-500:]})  # Last 500 readings

# ====== API: GET SESSIONS ======
@app.route('/api/sessions')
def api_sessions():
    return jsonify({"sessions": list(sessions.values())})

# ====== API: GET SESSION DETAIL ======
@app.route('/api/sessions/<session_id>')
def api_session_detail(session_id):
    if session_id in sessions:
        return jsonify(sessions[session_id])
    return jsonify({"error": "Session not found"}), 404

# ====== API: GET DRIVERS ======
@app.route('/api/drivers')
def api_drivers():
    return jsonify({"drivers": driver_profiles})

# ====== API: CREATE DRIVER ======
@app.route('/api/drivers', methods=['POST'])
def create_driver():
    global driver_profiles
    data = request.json
    driver_id = data.get('id', 'driver_' + datetime.now().strftime("%Y%m%d_%H%M%S"))
    
    driver_profiles[driver_id] = {
        "id": driver_id,
        "name": data.get('name', 'New Driver'),
        "sensitivity": data.get('sensitivity', 'normal'),
        "alert_threshold": data.get('alert_threshold', 5),
        "language": data.get('language', 'en'),
        "created_at": datetime.now().isoformat()
    }
    
    save_drivers()
    return jsonify({"status": "Driver created", "id": driver_id}), 201

# ====== API: DELETE DRIVER ======
@app.route('/api/drivers/<driver_id>', methods=['DELETE'])
def delete_driver(driver_id):
    global driver_profiles, current_driver
    
    if driver_id == "default":
        return jsonify({"error": "Cannot delete default driver"}), 400
    
    if driver_id in driver_profiles:
        del driver_profiles[driver_id]
        if current_driver == driver_id:
            current_driver = "default"
        save_drivers()
        return jsonify({"status": "Driver deleted"}), 200
    
    return jsonify({"error": "Driver not found"}), 404

# ====== API: GET SETTINGS ======
@app.route('/api/settings', methods=['GET'])
def get_settings():
    return jsonify(app_settings)

# ====== API: UPDATE SETTINGS ======
@app.route('/api/settings', methods=['POST'])
def update_settings():
    global app_settings
    app_settings.update(request.json)
    save_settings()
    return jsonify({"status": "Settings updated"}), 200

# ====== API: GET CURRENT DRIVER ======
@app.route('/api/current-driver')
def get_current_driver():
    return jsonify({
        "driver_id": current_driver,
        "profile": driver_profiles.get(current_driver, {})
    })

# ====== API: SET CURRENT DRIVER ======
@app.route('/api/current-driver/<driver_id>', methods=['POST'])
def set_current_driver(driver_id):
    global current_driver
    
    if driver_id in driver_profiles:
        current_driver = driver_id
        return jsonify({"status": "Driver switched"}), 200
    
    return jsonify({"error": "Driver not found"}), 404

# ====== API: GET SCREENSHOTS ======
@app.route('/api/screenshots')
def api_screenshots():
    ss_dir = "static/screenshots_log"
    if not os.path.exists(ss_dir):
        return jsonify({"screenshots": []})
    
    files = sorted(
        glob.glob(os.path.join(ss_dir, "*.jpg")),
        key=os.path.getmtime,
        reverse=True
    )
    
    screenshots = []
    for f in files:
        filename = os.path.basename(f)
        screenshots.append({
            "filename": filename,
            "path": f"/static/screenshots_log/{filename}",
            "size": os.path.getsize(f),
            "created": datetime.fromtimestamp(os.path.getmtime(f)).isoformat()
        })
    
    return jsonify({"screenshots": screenshots})

# ====== API: DELETE SCREENSHOT ======
@app.route('/api/screenshots/<filename>', methods=['DELETE'])
def delete_screenshot(filename):
    try:
        filepath = os.path.join("static/screenshots_log", filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            return jsonify({"status": "Screenshot deleted"}), 200
    except:
        pass
    return jsonify({"error": "Could not delete screenshot"}), 400

# ====== API: EXPORT SESSION ======
@app.route('/api/export/session/<session_id>')
def export_session(session_id):
    if session_id not in sessions:
        return jsonify({"error": "Session not found"}), 404
    
    session_data = sessions[session_id]
    json_data = json.dumps(session_data, indent=2)
    
    return send_file(
        BytesIO(json_data.encode()),
        mimetype='application/json',
        as_attachment=True,
        download_name=f'session_{session_id}.json'
    )

# ====== API: CLEAR ALL DATA ======
@app.route('/api/clear-all', methods=['POST'])
def clear_all():
    global sessions, metrics_history, current_session
    sessions = {}
    metrics_history = []
    current_session = None
    save_sessions()
    return jsonify({"status": "All data cleared"}), 200

# ====== DETECTION LOOP ======
def detection_loop():
    global detector, cap, is_running, current_frame, latest_metrics, current_session, metrics_history, alert_count
    
    while is_running and cap:
        ret, frame = cap.read()
        
        if not ret:
            continue
        
        try:
            # Analyze frame
            status, color, ear, mar, fatigue, gaze_ratio, alert_triggered, event_type = detector.analyze_frame(frame)
            frame_with_hud = detector.draw_hud(frame, status, color, ear, mar, fatigue, gaze_ratio)
            
            with frame_lock:
                current_frame = frame_with_hud
            
            # Update live metrics
            latest_metrics["ear"] = round(ear, 2)
            latest_metrics["mar"] = round(mar, 2)
            latest_metrics["gaze"] = round(gaze_ratio or 0, 2)
            latest_metrics["fatigue"] = fatigue
            latest_metrics["status"] = status
            
            # Store in history
            metrics_history.append({
                "timestamp": datetime.now().isoformat(),
                "ear": round(ear, 2),
                "mar": round(mar, 2),
                "gaze": round(gaze_ratio or 0, 2),
                "fatigue": fatigue,
                "status": status
            })
            
            # Update session stats
            if current_session:
                current_session["total_fatigue"] += fatigue
                current_session["frames_count"] += 1
                current_session["peak_fatigue"] = max(current_session.get("peak_fatigue", 0), fatigue)
                
                if alert_triggered:
                    current_session["alerts"] += 1
                    alert_count += 1
                    print(f"🚨 ALERT #{alert_count}: {event_type} - {status}")
            
            # Handle alerts
            if alert_triggered:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ALERT: {event_type} - Fatigue: {fatigue}/10")
        
        except Exception as e:
            print(f"Error in detection loop: {e}")

# ====== FILE OPERATIONS ======
def save_sessions():
    os.makedirs('data', exist_ok=True)
    with open('data/sessions.json', 'w') as f:
        json.dump(
            {k: v for k, v in sessions.items()},
            f,
            indent=2,
            default=str
        )

def save_drivers():
    os.makedirs('data', exist_ok=True)
    with open('data/drivers.json', 'w') as f:
        json.dump(driver_profiles, f, indent=2, default=str)

def save_settings():
    os.makedirs('data', exist_ok=True)
    with open('data/settings.json', 'w') as f:
        json.dump(app_settings, f, indent=2)

def load_data():
    global sessions, driver_profiles, app_settings
    
    os.makedirs('data', exist_ok=True)
    
    # Load sessions
    if os.path.exists('data/sessions.json'):
        try:
            with open('data/sessions.json', 'r') as f:
                sessions = json.load(f)
        except:
            sessions = {}
    
    # Load drivers
    if os.path.exists('data/drivers.json'):
        try:
            with open('data/drivers.json', 'r') as f:
                loaded_drivers = json.load(f)
                driver_profiles.update(loaded_drivers)
        except:
            pass
    
    # Load settings
    if os.path.exists('data/settings.json'):
        try:
            with open('data/settings.json', 'r') as f:
                loaded_settings = json.load(f)
                app_settings.update(loaded_settings)
        except:
            pass

# ====== ERROR HANDLERS ======
@app.errorhandler(404)
def not_found(error):
    return render_template('index.html'), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Internal server error"}), 500

# ====== MAIN ======
if __name__ == '__main__':
    print("🛡️ Starting SentinelDrive...")
    load_data()
    print(f"✅ Loaded {len(sessions)} sessions")
    print(f"✅ Loaded {len(driver_profiles)} driver profiles")
    print(f"✅ Settings configured")
    print("\n🚀 Server running on http://0.0.0.0:5000")
    print("📱 Access from browser: http://localhost:5000\n")
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=True)
