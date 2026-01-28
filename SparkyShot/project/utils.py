import cv2
import numpy as np
from PyQt6.QtGui import QImage, QPixmap
import math

def convert_qpixmap_to_opencv(qpixmap):
    """Converts a QPixmap to an OpenCV compatible image (numpy array)."""
    qimage = qpixmap.toImage()
    qimage = qimage.convertToFormat(QImage.Format.Format_RGBA8888)

    width = qimage.width()
    height = qimage.height()

    ptr = qimage.bits()
    ptr.setsize(height * width * 4)

    arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))

    return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)

def convert_opencv_to_qpixmap(cv_img):
    """Converts an OpenCV image back to QPixmap."""
    if cv_img.shape[2] == 3:
        cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    elif cv_img.shape[2] == 4:
        cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGRA2RGBA)

    height, width, channel = cv_img.shape
    bytes_per_line = channel * width

    fmt = QImage.Format.Format_RGB888 if channel == 3 else QImage.Format.Format_RGBA8888

    qimage = QImage(cv_img.data, width, height, bytes_per_line, fmt)

    return QPixmap.fromImage(qimage.copy())

def apply_pixelate(image, x, y, w, h, block_size=10):
    """Applies a pixelation effect to a region."""
    if w < 1 or h < 1: return image
    if block_size < 2: block_size = 2

    roi = image[y:y+h, x:x+w]

    small_w = max(1, w // block_size)
    small_h = max(1, h // block_size)
    small = cv2.resize(roi, (small_w, small_h), interpolation=cv2.INTER_LINEAR)

    pixelated = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)

    result = image.copy()
    result[y:y+h, x:x+w] = pixelated
    return result

def apply_blur(image, x, y, w, h, kernel_size=51):
    """Applies a Gaussian Blur effect."""
    if w < 1 or h < 1: return image

    if kernel_size % 2 == 0: kernel_size += 1

    result = image.copy()
    roi = result[y:y+h, x:x+w]

    blurred = cv2.GaussianBlur(roi, (kernel_size, kernel_size), 0)
    result[y:y+h, x:x+w] = blurred
    return result

def calculate_ngon_points(cx, cy, radius, sides):
    """Calculates vertices (x,y) for a regular polygon."""
    points = []
    if sides < 3: return points

    angle_step = 2 * math.pi / sides
    rotation = -math.pi / 2

    for i in range(sides):
        px = cx + radius * math.cos(i * angle_step + rotation)
        py = cy + radius * math.sin(i * angle_step + rotation)
        points.append((px, py))
    return points

def detect_qr_content(image):
    """
    Detects and decodes a QR code in the given image.
    Returns the content string or None.
    """
    try:
        detector = cv2.QRCodeDetector()
        data, bbox, _ = detector.detectAndDecode(image)

        if data:
            return data
        return None
    except Exception as e:
        print(f"QR Error: {e}")
        return None
