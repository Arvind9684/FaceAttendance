import os
import csv
import numpy as np
import cv2
from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.uix.camera import Camera
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.utils import platform

from db import DB
from face_engine import FaceEngine

ANDROID = platform == "android"
CAM_INDEX = 1 if ANDROID else 0      # 1 = front camera on most phones
ROTATE_K = 3 if ANDROID else 0       # np.rot90 steps; change to 1 if the face is upside-down
MIRROR = ANDROID                     # front camera is mirrored
SAMPLES = 20                         # photos stored per person
CONFIRM_FRAMES = 3                   # same person N frames in a row => mark

KV = """
<Btn@Button>:
    size_hint_y: None
    height: dp(52)
    font_size: sp(18)

ScreenManager:
    HomeScreen:
    RegisterScreen:
    AttendScreen:
    ReportScreen:

<HomeScreen>:
    name: "home"
    BoxLayout:
        orientation: "vertical"
        padding: dp(24)
        spacing: dp(14)
        Label:
            text: "Face Attendance"
            font_size: sp(30)
            size_hint_y: None
            height: dp(80)
        Label:
            id: info
            text: root.info
            size_hint_y: None
            height: dp(40)
        Btn:
            text: "Register New Person"
            on_release: app.root.current = "register"
        Btn:
            text: "Take Attendance"
            on_release: app.root.current = "attend"
        Btn:
            text: "Reports"
            on_release: app.root.current = "report"
        Widget:

<RegisterScreen>:
    name: "register"
    BoxLayout:
        orientation: "vertical"
        padding: dp(10)
        spacing: dp(8)
        BoxLayout:
            id: cambox
            size_hint_y: 0.55
        TextInput:
            id: name
            hint_text: "Full name"
            multiline: False
            size_hint_y: None
            height: dp(44)
        TextInput:
            id: roll
            hint_text: "Roll / Employee ID"
            multiline: False
            size_hint_y: None
            height: dp(44)
        Label:
            id: status
            text: root.status
            size_hint_y: None
            height: dp(40)
        Btn:
            text: "Start Capture"
            on_release: root.start_capture()
        Btn:
            text: "Back"
            on_release: app.root.current = "home"

<AttendScreen>:
    name: "attend"
    BoxLayout:
        orientation: "vertical"
        padding: dp(10)
        spacing: dp(8)
        BoxLayout:
            id: cambox
            size_hint_y: 0.7
        Label:
            text: root.status
            font_size: sp(20)
            size_hint_y: None
            height: dp(70)
            halign: "center"
            text_size: self.width, None
        Btn:
            text: "Back"
            on_release: app.root.current = "home"

<ReportScreen>:
    name: "report"
    BoxLayout:
        orientation: "vertical"
        padding: dp(10)
        spacing: dp(8)
        Label:
            text: "Today's Attendance"
            font_size: sp(22)
            size_hint_y: None
            height: dp(40)
        ScrollView:
            Label:
                text: root.text
                size_hint_y: None
                height: self.texture_size[1]
                text_size: self.width, None
                halign: "left"
                valign: "top"
        Label:
            text: root.msg
            size_hint_y: None
            height: dp(40)
            font_size: sp(13)
        Btn:
            text: "Export All to CSV"
            on_release: root.export()
        Btn:
            text: "Back"
            on_release: app.root.current = "home"
"""

engine = None
db = None


class CamScreen(Screen):
    """Screen that owns a camera only while it is visible."""
    interval = 0.3

    def on_enter(self):
        self.cam = Camera(index=CAM_INDEX, resolution=(640, 480), play=True)
        self.cam.allow_stretch = True
        self.cam.keep_ratio = True
        self.ids.cambox.add_widget(self.cam)
        self.ev = Clock.schedule_interval(self.tick, self.interval)
        self.on_cam_ready()

    def on_leave(self):
        self.ev.cancel()
        self.cam.play = False
        self.ids.cambox.remove_widget(self.cam)
        self.cam = None

    def on_cam_ready(self):
        pass

    def grab_gray(self):
        tex = self.cam.texture if self.cam else None
        if tex is None:
            return None
        w, h = tex.size
        buf = np.frombuffer(tex.pixels, np.uint8)
        if buf.size != w * h * 4:
            return None
        gray = cv2.cvtColor(buf.reshape(h, w, 4), cv2.COLOR_RGBA2GRAY)
        gray = np.rot90(gray, ROTATE_K)
        if MIRROR:
            gray = np.fliplr(gray)
        return np.ascontiguousarray(gray)

    def tick(self, dt):
        pass


class HomeScreen(Screen):
    from kivy.properties import StringProperty
    info = StringProperty("")

    def on_pre_enter(self):
        self.info = "Registered people: %d" % db.count_users()


class RegisterScreen(CamScreen):
    from kivy.properties import StringProperty
    status = StringProperty("Enter details, then tap Start Capture")
    capturing = False
    feats = []

    def on_cam_ready(self):
        self.capturing = False
        self.feats = []
        self.status = "Enter details, then tap Start Capture"

    def start_capture(self):
        if not self.ids.name.text.strip():
            self.status = "Please enter a name"
            return
        self.feats = []
        self.capturing = True
        self.status = "Look at the camera... 0/%d" % SAMPLES

    def tick(self, dt):
        if not self.capturing:
            return
        gray = self.grab_gray()
        if gray is None:
            return
        box = engine.detect(gray)
        if box is None:
            self.status = "No face found - face the camera"
            return
        self.feats.append(engine.features(gray, box))
        self.status = "Capturing... %d/%d (slowly turn head a little)" % (
            len(self.feats), SAMPLES)
        if len(self.feats) >= SAMPLES:
            self.capturing = False
            db.add_user(self.ids.name.text.strip(), self.ids.roll.text.strip(),
                        self.feats)
            self.status = "Saved: %s" % self.ids.name.text.strip()
            self.ids.name.text = ""
            self.ids.roll.text = ""
            self.feats = []


class AttendScreen(CamScreen):
    from kivy.properties import StringProperty
    status = StringProperty("Starting...")

    def on_cam_ready(self):
        self.templates, self.owners = db.load_templates()
        self.last, self.count = None, 0
        self.status = ("No people registered yet" if not self.owners
                       else "Look at the camera")

    def tick(self, dt):
        if not self.owners:
            return
        gray = self.grab_gray()
        if gray is None:
            return
        box = engine.detect(gray)
        if box is None:
            self.last, self.count = None, 0
            self.status = "No face detected"
            return
        feat = engine.features(gray, box)
        uid, score = engine.identify(feat, self.templates, self.owners)
        if uid is None:
            self.last, self.count = None, 0
            self.status = "Unknown face (score %.2f)" % score
            return
        self.count = self.count + 1 if uid == self.last else 1
        self.last = uid
        name, roll = db.user_name(uid)
        if self.count >= CONFIRM_FRAMES:
            if db.mark(uid):
                self.status = "[Present] %s marked! (%.2f)" % (name, score)
            else:
                self.status = "%s - already marked today" % name


class ReportScreen(Screen):
    from kivy.properties import StringProperty
    text = StringProperty("")
    msg = StringProperty("")

    def on_pre_enter(self):
        rows = db.report()
        self.msg = ""
        self.text = "\n".join("%s  (%s)   %s" % (n, r or "-", t)
                              for n, r, d, t in rows) or "No attendance yet today"

    def export(self):
        folder = App.get_running_app().user_data_dir
        if ANDROID:
            try:
                from android.storage import primary_external_storage_path
                folder = os.path.join(primary_external_storage_path(), "Download")
            except Exception:
                pass
        path = os.path.join(folder, "attendance.csv")
        try:
            with open(path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["Name", "Roll", "Date", "Time"])
                w.writerows(db.all_records())
            self.msg = "Saved: " + path
        except Exception as e:
            self.msg = "Export failed: %s" % e


class FaceAttendanceApp(App):
    def build(self):
        global engine, db
        engine = FaceEngine()
        db = DB(self.user_data_dir)
        return Builder.load_string(KV)

    def on_start(self):
        if ANDROID:
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.CAMERA])


if __name__ == "__main__":
    FaceAttendanceApp().run()
