"""Example utility module for ${name}."""

import cv2
import numpy as np


def resize_image(img: np.ndarray, max_size: int = 1024) -> np.ndarray:
    """Resize image while maintaining aspect ratio."""
    h, w = img.shape[:2]
    if max(h, w) <= max_size:
        return img

    scale = max_size / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    return cv2.resize(img, (new_w, new_h))


def validate_image(img: np.ndarray) -> bool:
    """Validate image dimensions."""
    if img is None or img.size == 0:
        return False
    h, w = img.shape[:2]
    return h > 0 and w > 0
