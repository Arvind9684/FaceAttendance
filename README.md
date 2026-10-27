# Face Attendance (Python / Kivy) -> Android APK

## Files
- main.py                 UI + camera loop (Kivy)
- face_engine.py          face detection + recognition (OpenCV + NumPy)
- db.py                   SQLite storage (users, face data, attendance)
- haarcascade_frontalface_default.xml   face detector model
- buildozer.spec          APK build configuration
- .github/workflows/build.yml   automatic APK build on GitHub

## 1. Test on your PC first (webcam)
    pip install -r requirements-desktop.txt
    python main.py

## 2. Build the APK  (pick ONE option)

### Option A - GitHub (easiest, works from Windows too)
1. Create a free GitHub account and a new repository.
2. Upload ALL files of this folder (keep the .github folder).
3. Open the "Actions" tab -> "Build APK" runs automatically (30-60 min first time).
4. When it finishes, open the run -> Artifacts -> download FaceAttendance-apk.
5. Unzip, copy the .apk to your phone, install (allow "unknown sources").

### Option B - Google Colab (no installs)
In a Colab notebook, upload this folder as a zip, then run:
    !unzip FaceAttendance.zip -d /content/app
    %cd /content/app
    !sudo apt-get update -y
    !sudo apt-get install -y git zip unzip openjdk-17-jdk autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo6 cmake libffi-dev libssl-dev
    !pip install buildozer cython==0.29.36
    !buildozer -v android debug
APK appears in /content/app/bin/ - download it from the Files panel.

### Option C - Ubuntu / WSL2 on Windows
    sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo6 cmake libffi-dev libssl-dev
    pip install buildozer cython==0.29.36
    buildozer android debug
APK is created in ./bin/

## 3. Using the app
1. Register New Person: enter name, tap Start Capture, face the camera ~10 s.
2. Take Attendance: people look at the camera; marked once per day.
3. Reports: today's list; Export saves attendance.csv to Downloads.

## Tuning / troubleshooting
- Face sideways or upside-down on phone: change ROTATE_K in main.py (try 1 or 3).
- Wrong back/front camera: change CAM_INDEX (0 = back, 1 = front).
- Wrongly accepts strangers: lower THRESHOLD in face_engine.py (e.g. 0.38).
- Doesn't recognise registered people: raise it (e.g. 0.50). The score is shown on screen.
- Register in the same lighting you'll use for attendance.
- Build fails: run `buildozer android clean` and rebuild; read the last 50 log lines.
- Simple LBP matching has no liveness check - a printed photo can fool it.
