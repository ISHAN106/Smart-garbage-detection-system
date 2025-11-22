from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import cv2
import math
import cvzone
from ultralytics import YOLO
import json
import os
from datetime import datetime
import base64
import numpy as np

app = Flask(__name__)
CORS(app)

# Load YOLO model with custom weights
yolo_model = YOLO("Weights/best.pt")

# Define class names
class_labels = ['0', 'c', 'garbage', 'garbage_bag', 'sampah-detection', 'trash']

# JSON file to store garbage data
DATA_FILE = 'garbage_data.json'

def load_garbage_data():
    """Load existing garbage data from JSON file"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return []

def save_garbage_data(data):
    """Save garbage data to JSON file"""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def detect_garbage(image):
    """Perform garbage detection on image and return results"""
    results = yolo_model(image)
    detections = []
    
    for r in results:
        boxes = r.boxes
        if boxes is not None:
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                w, h = x2 - x1, y2 - y1
                
                conf = math.ceil((box.conf[0] * 100)) / 100
                cls = int(box.cls[0])
                
                if conf > 0.3:
                    detections.append({
                        'class': class_labels[cls],
                        'confidence': conf,
                        'bbox': {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'w': w, 'h': h}
                    })
                    
                    # Draw bounding box on image
                    cvzone.cornerRect(image, (x1, y1, w, h), t=2)
                    cvzone.putTextRect(image, f'{class_labels[cls]} {conf}', 
                                     (x1, y1 - 10), scale=0.8, thickness=1, colorR=(255, 0, 0))
    
    return detections, image

# Folder to save processed images
IMAGE_FOLDER = os.path.join(os.getcwd(), "ProcessedImages")
os.makedirs(IMAGE_FOLDER, exist_ok=True)

@app.route('/api/detect-garbage', methods=['POST'])
def detect_garbage_endpoint():
    try:
        data = request.json

        # Decode base64 image
        image_data = data['image'].split(',')[1]
        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Location info
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        address = data.get('address', 'Unknown location')

        # Detect
        detections, processed_img = detect_garbage(img)
        garbage_count = len(detections)

        # Save processed image
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        image_filename = f'garbage_{timestamp}.jpg'
        image_path = os.path.join(IMAGE_FOLDER, image_filename)   # absolute path
        cv2.imwrite(image_path, processed_img)

        # Load existing data
        garbage_data = load_garbage_data()
        new_id = len(garbage_data) + 1

        # Create new record
        new_record = {
            'id': new_id,
            'timestamp': datetime.now().isoformat(),
            'location': {
                'latitude': latitude,
                'longitude': longitude,
                'address': address
            },
            'garbage_count': garbage_count,
            'detections': detections,
            'processed_image_path': image_path,  # keep internal
            'processed_image_url': f"http://localhost:5000/api/image/{new_id}"  # for frontend
        }

        garbage_data.append(new_record)
        save_garbage_data(garbage_data)

        return jsonify({
            'success': True,
            'record_id': new_id,
            'garbage_count': garbage_count,
            'detections': detections,
            'processed_image_url': new_record['processed_image_url']
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/garbage-locations', methods=['GET'])
def get_garbage_locations():
    """Get all garbage locations for map display"""
    try:
        garbage_data = load_garbage_data()
        
        # Transform data for map display
        locations = []
        for record in garbage_data:
            locations.append({
                'id': record['id'],
                'latitude': record['location']['latitude'],
                'longitude': record['location']['longitude'],
                'address': record['location']['address'],
                'garbage_count': record['garbage_count'],
                'timestamp': record['timestamp'],
                'detections': record['detections']
            })
        
        return jsonify({'success': True, 'locations': locations})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/garbage-data/<int:record_id>', methods=['GET'])
def get_garbage_record(record_id):
    try:
        garbage_data = load_garbage_data()
        record = next((r for r in garbage_data if r['id'] == record_id), None)

        if record:
            # Add processed_image_url dynamically if not stored
            record['processed_image_url'] = f"http://localhost:5000/api/image/{record_id}"
            return jsonify({'success': True, 'record': record})
        else:
            return jsonify({'success': False, 'error': 'Record not found'}), 404

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/image/<int:record_id>', methods=['GET'])
def get_processed_image(record_id):
    try:
        garbage_data = load_garbage_data()
        record = next((r for r in garbage_data if r['id'] == record_id), None)
        
        if not record:
            return jsonify({'success': False, 'error': 'Record not found'}), 404
        
        image_path = record.get('processed_image_path')
        if not image_path or not os.path.exists(image_path):
            return jsonify({'success': False, 'error': 'Image not found'}), 404
        
        return send_file(image_path, mimetype='image/jpeg')
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/delete-record/<int:record_id>', methods=['DELETE'])
def delete_record(record_id):
    """Delete a specific garbage record and its associated image"""
    try:
        garbage_data = load_garbage_data()
        record = next((r for r in garbage_data if r['id'] == record_id), None)
        
        if record:
            # Delete the associated image file if it exists
            image_path = record.get('processed_image_path')
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except OSError as e:
                    print(f"Error deleting image file: {e}")
        
        # Remove record from data
        garbage_data = [r for r in garbage_data if r['id'] != record_id]
        save_garbage_data(garbage_data)
        
        return jsonify({'success': True, 'message': 'Record deleted successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clear-all-data', methods=['DELETE'])
def clear_all_data():
    """Clear all garbage data and delete all associated images"""
    try:
        garbage_data = load_garbage_data()
        
        # Delete all associated image files
        for record in garbage_data:
            image_path = record.get('processed_image_path')
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except OSError as e:
                    print(f"Error deleting image file: {e}")
        
        # Clear all data
        save_garbage_data([])
        return jsonify({'success': True, 'message': 'All data cleared successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)