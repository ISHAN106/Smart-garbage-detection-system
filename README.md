GarbageDetector
===============

A local prototype for detecting and tracking garbage pollution on a map. The project includes:

- A React frontend (client/) using MapTiler and the browser Geolocation API to show the user's location and pollution markers.
- A Flask backend (app1.py) that runs YOLO-based object detection on uploaded or captured images and stores results in MongoDB.
- Scripts and utilities for creating a simple pollution map (folium) and returning analytics.

This README describes how to set up and run the project locally (Windows / PowerShell), environment variables, common troubleshooting steps (especially for geolocation), and where to look in the code.

Quick status
------------
- Frontend: React app in `client/` (Create React App). Uses `@maptiler/sdk` and `@turf/turf`.
- Backend: Flask app in `app1.py`, uses OpenCV, cvzone, ultralytics (YOLO), Pillow, folium, pymongo.
- Model: YOLO model expected at `Weights/best.pt` (required if you want detection to run locally).
- Database: MongoDB (Atlas URI configured via `MONGO_URI` or default in code). The app stores detections in the `detections` collection.

Prerequisites
-------------
- Python 3.9+ (or 3.8+)
- Node.js (14+ recommended) and npm
- MongoDB instance (Atlas or local) or adjust `MONGO_URI` in environment
- A YOLO model at `Weights/best.pt` (if you want real detections)
- MapTiler API key (for the map tiles)

Recommended development environment (Windows PowerShell)
--------------------------------------------------------
- Open two terminals (or three): one for backend, one for frontend, one for any other commands.

Backend setup (Flask)
---------------------
1. Create and activate a Python venv (optional but recommended):

```powershell
cd C:\Users\ishan\Downloads\GarbageDetector
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install Python dependencies. There is no maintained `requirements.txt` in the repo; install these commonly used packages manually (adjust versions as needed):

```powershell
pip install flask flask-cors pymongo Pillow opencv-python-headless cvzone ultralytics folium branca requests geopy
```

Note: `opencv-python-headless` avoids GUI dependencies on servers. If you need camera GUI features, install `opencv-python` instead.

3. Set environment variables (optional):

- `MONGO_URI` to point to your MongoDB (if not using the default in code).
- `OPENWEATHER_API_KEY` if you want weather enrichment.

You can set them in PowerShell for the session:

```powershell
$env:MONGO_URI = 'your_mongo_uri_here'
$env:OPENWEATHER_API_KEY = 'your_openweather_key'
```

4. Start the backend:

```powershell
python app1.py
```

The backend runs on http://0.0.0.0:5000 by default. Check `/health` (http://localhost:5000/health) for status.

Frontend setup (React)
----------------------
1. Put your MapTiler API key into `client/.env` as `REACT_APP_MAPTILER_KEY` (create the file if missing). Example:

```
REACT_APP_MAPTILER_KEY=YOUR_MAPTILER_KEY_HERE
```

Important: After editing `.env`, restart the React dev server.

2. Install and run the client:

```powershell
cd client
npm install
npm start
```

The React dev server opens on http://localhost:3000 and is configured to proxy API requests to the Flask backend (see `client/package.json` for proxy settings). If the dev server reports errors, check the terminal for messages (missing packages, ESLint errors, etc.).

Key frontend files
------------------
- `client/src/pages/PollutionMap.jsx` — main map page. Reads `REACT_APP_MAPTILER_KEY`, configures MapTiler SDK, places a "You are here" marker from browser geolocation, draws an accuracy circle (Turf), and fetches detection markers from `/api/get_all_detections`.
  - `getBestLocation()` implements improved geolocation: one-shot then watchPosition with a time cap.
  - You can change the accuracy threshold or max wait in this file.
- `client/src/pages/GarbageDetection.jsx` — capture/upload page. Captures camera frames, sends images to backend endpoints and displays detection results and computed pollution score.
- `client/src/pages/Dashboard.jsx` — polls `/get_pollution_data` and shows stats, hotspots and trend data.

Key backend endpoints (app1.py)
-------------------------------
- GET `/api/get_all_detections` — returns all detections (lat, lng, score, name, timestamp) for map markers.
- GET `/get_pollution_data` — returns recent statistics, hotspots and 7-day trend data for dashboard/analytics.
- POST `/capture_image` — accepts JSON with base64 image and optional latitude/longitude and runs detection.
- POST `/upload_with_location` — accepts multipart form upload (file + latitude + longitude) and runs detection.
- GET `/get_map` and `/generate_pollution_map` — returns a generated folium map HTML.
- GET `/result/<filename>` — serves processed images from `results/`.
- GET `/health` — server status, YOLO model loaded flag, and DB connectivity.

Why a red marker with score 100 appears
--------------------------------------
- The backend computes a pollution score (see `calculate_pollution_score()` in `app1.py`) and caps it with `min(100, ...)`. The frontend colors markers by the score (green/orange/red). A score of 100 is therefore a maximum severity (red) marker. You can inspect records by accessing `/api/get_all_detections` to find score 100 records.

Common issues & troubleshooting
-------------------------------
- Stuck on "Getting your location..." / very coarse location (large accuracy like 181,078 m):
  - Make sure you allowed the browser to use location (check the lock icon in the address bar → Site settings → Location). If you denied earlier, clear site permissions.
  - On Windows, enable Location Services in Settings → Privacy & security → Location and allow the browser to use location.
  - Disable VPN (VPNs often cause IP-based coarse geolocation) and connect to Wi‑Fi for better accuracy.
  - The frontend includes a "Use default location" button to proceed without precise geolocation.
  - If you want programmatic changes: change `accuracyThreshold` or `maxWait` in `client/src/pages/PollutionMap.jsx`.

- Backend fails to start or crashes on model load:
  - Ensure `Weights/best.pt` exists and is compatible with the installed ultralytics/YOLO version.
  - Check traceback printed by `python app1.py` — it will indicate missing packages or errors loading the model.
  - If you don't want model inference locally, you can stub out `process_image_with_location()` to return a success response for testing.

- API 500 when saving to DB:
  - Verify `MONGO_URI` and that your MongoDB Atlas IP whitelist allows your client, or run a local MongoDB and update `MONGO_URI` accordingly.

Inspecting data quickly
-----------------------
- View all detections (map markers): http://localhost:5000/api/get_all_detections
- Health: http://localhost:5000/health

PowerShell snippet to show detections with score 100:

```powershell
$response = Invoke-RestMethod -Uri "http://localhost:5000/api/get_all_detections" -Method GET
$response.detections | Where-Object { $_.score -eq 100 } | Format-List
```

Development notes and next steps
-------------------------------
- Consider adding `requirements.txt` (Python) and `package-lock.json` (frontend) to make setup reproducible.
- Consider using Server-Sent Events or WebSockets if you need real-time push updates to the dashboard instead of polling.
- Remove or secure any hard-coded API keys found in repository copies (there is a `PollutionMap copy.jsx` that previously contained a hard-coded MapTiler key). Keep keys in `client/.env` and add `.env` to `.gitignore` (already done in the project).
- Add a small manual lat/lng input on the map page for devices that can't provide accurate geolocation.

Where to look in the code for common edits
-----------------------------------------
- Change MapTiler style or tile source: `client/src/pages/PollutionMap.jsx` (style URL set with the MapTiler key).
- Adjust geolocation thresholds: `client/src/pages/PollutionMap.jsx` — `accuracyThreshold` and `maxWait`.
- Change pollution scoring weights: `app1.py` — `pollution_weights` and `calculate_pollution_score()`.
- Persisting and analyzing: `store_detection_data()` and `get_pollution_data()` in `app1.py`.

Contributing
------------
- If you add features, please add appropriate unit or integration tests where applicable.
- If you change model weights or classes, update `class_labels` and `pollution_weights` in `app1.py` so scoring remains consistent.

License
-------
This repository contains example code and is provided as-is for educational or prototyping purposes. Replace or remove any API keys before publishing.

Contact / help
----------------
If you'd like me to:
- start the backend and frontend here and capture startup errors, say: "Run servers and show logs".
- add a manual lat/lng input or click-to-place marker, say: "Add manual placement".
- remove the duplicate file with a hard-coded key, say: "Remove hard-coded key file".

---

README created by the project assistant. Update or expand sections as your project evolves.
