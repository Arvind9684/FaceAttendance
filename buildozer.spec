[app]
title = Face Attendance
package.name = faceattendance
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,xml
version = 1.0
requirements = python3,kivy==2.3.0,numpy,opencv,pyjnius,android
orientation = portrait
fullscreen = 0

android.permissions = CAMERA
android.api = 33
android.minapi = 24
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
