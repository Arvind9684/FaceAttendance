"""Face detection + recognition using only core OpenCV and NumPy
(so it builds on Android without dlib / opencv-contrib).

Detection : Haar cascade
Recognition: LBP histogram (8x8 grid) + chi-square distance
"""
import os
import cv2
import numpy as np

CASCADE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "haarcascade_frontalface_default.xml")

# Lower = stricter. Tune using the score shown on the Attendance screen.
THRESHOLD = 0.45
GRID = 8
CELL = 12                      # 8 * 12 = 96 px inner face
FACE_SIZE = GRID * CELL + 2    # +2 for the LBP border


class FaceEngine:
    def __init__(self):
        self.detector = cv2.CascadeClassifier(CASCADE)

    def detect(self, gray):
        """Return the largest face (x, y, w, h) or None."""
        faces = self.detector.detectMultiScale(
            gray, scaleFactor=1.2, minNeighbors=5, minSize=(80, 80))
        if len(faces) == 0:
            return None
        return max(faces, key=lambda f: f[2] * f[3])

    @staticmethod
    def features(gray, box):
        x, y, w, h = box
        face = gray[y:y + h, x:x + w]
        face = cv2.resize(face, (FACE_SIZE, FACE_SIZE))
        face = cv2.equalizeHist(face)

        c = face[1:-1, 1:-1].astype(np.int16)
        size = c.shape[0]
        code = np.zeros(c.shape, np.uint8)
        offsets = [(-1, -1), (-1, 0), (-1, 1), (0, 1),
                   (1, 1), (1, 0), (1, -1), (0, -1)]
        for i, (dy, dx) in enumerate(offsets):
            n = face[1 + dy:1 + dy + size, 1 + dx:1 + dx + size].astype(np.int16)
            code |= ((n >= c).astype(np.uint8) << i)

        cells = code.reshape(GRID, CELL, GRID, CELL).transpose(0, 2, 1, 3)
        cells = cells.reshape(GRID * GRID, CELL * CELL)
        feat = np.empty((GRID * GRID, 256), np.float32)
        for i, cell in enumerate(cells):
            feat[i] = np.bincount(cell, minlength=256) / float(cell.size)
        return feat.ravel()

    @staticmethod
    def distances(feat, templates):
        """Mean chi-square distance of feat vs each row of templates."""
        a = feat.reshape(1, -1)
        d = 0.5 * ((templates - a) ** 2 / (templates + a + 1e-10))
        return d.reshape(len(templates), GRID * GRID, 256).sum(axis=2).mean(axis=1)

    def identify(self, feat, templates, owners):
        """templates: (N, D) array, owners: list of user ids (len N).
        Returns (user_id or None, best_distance)."""
        if len(templates) == 0:
            return None, 1.0
        d = self.distances(feat, templates)
        i = int(np.argmin(d))
        best = float(d[i])
        return (owners[i] if best < THRESHOLD else None), best
