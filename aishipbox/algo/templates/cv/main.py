#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""${name} - Image processing service with external model via HTTP."""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path

import cv2
import requests

from rest.process_base import ProcessBase
from .utils import resize_image, validate_image

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AlgoProcessor(ProcessBase):
    """Algorithm Processor for image processing tasks."""

    def __init__(self):
        super().__init__(url="")
        self.model_url = os.getenv("MODEL_URL")
        if not self.model_url:
            logger.warning("MODEL_URL not set, model calls will fail")

    def process(self, params_dict: dict) -> tuple[dict, int]:
        input_path = params_dict.get("input_path")
        if not input_path:
            return {"error": "input_path is required"}, 400

        path = Path(input_path)
        if not path.exists():
            return {"error": f"File not found: {input_path}"}, 404

        output_path = params_dict.get("output_path")
        if not output_path:
            output_path = str(path.parent / f"{path.stem}_processed{path.suffix}")

        try:
            img = cv2.imread(str(path))
            if not validate_image(img):
                return {"error": f"Failed to read image: {input_path}"}, 400

            original_h, original_w = img.shape[:2]
            img = resize_image(img)

            # Encode image as base64 for model service
            _, buffer = cv2.imencode(".jpg", img)
            img_b64 = base64.b64encode(buffer).decode("utf-8")

            # Call model service
            model_result = self._call_model({"image": img_b64})

            # Save processed image if returned by model
            if "image" in model_result:
                out_bytes = base64.b64decode(model_result["image"])
                with open(output_path, "wb") as f:
                    f.write(out_bytes)

            result = {
                "input_path": str(input_path),
                "output_path": str(output_path),
                "original_size": [original_w, original_h],
                "model_result": model_result,
            }
            return result, 200

        except requests.RequestException as e:
            logger.exception("Model service call failed")
            return {"error": f"Model service error: {e}"}, 502
        except Exception as e:
            logger.exception("Image processing failed")
            return {"error": str(e)}, 500

    def _call_model(self, data: dict) -> dict:
        """Call external model service."""
        resp = requests.post(self.model_url, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()
