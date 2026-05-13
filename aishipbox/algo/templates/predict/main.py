#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""${name} - Prediction service with external model via HTTP."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pandas as pd
import requests

from rest.process_base import ProcessBase
from .utils import preprocess_dataframe, validate_features

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AlgoProcessor(ProcessBase):
    """Algorithm Processor for prediction tasks."""

    def __init__(self):
        super().__init__(url="")
        self.model_url = os.getenv("MODEL_URL")
        if not self.model_url:
            logger.warning("MODEL_URL not set, model calls will fail")

    def process(self, params_dict: dict) -> tuple[dict, int]:
        file_path = params_dict.get("file_path")
        features = params_dict.get("features")

        if file_path:
            return self._predict_from_file(file_path)
        elif features:
            return self._predict_single(features)
        else:
            return {"error": "file_path or features is required"}, 400

    def _call_model(self, data: dict) -> dict:
        """Call external model service."""
        resp = requests.post(self.model_url, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _predict_from_file(self, file_path: str) -> tuple[dict, int]:
        path = Path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}, 404

        try:
            df = pd.read_csv(path)
            df = preprocess_dataframe(df)
            model_result = self._call_model({"data": df.to_dict(orient="records")})

            result = {
                "rows": len(df),
                "columns": list(df.columns),
                "predictions": model_result.get("predictions", []),
            }
            return result, 200

        except requests.RequestException as e:
            logger.exception("Model service call failed")
            return {"error": f"Model service error: {e}"}, 502
        except Exception as e:
            logger.exception("File processing failed")
            return {"error": str(e)}, 500

    def _predict_single(self, features: list) -> tuple[dict, int]:
        try:
            model_result = self._call_model({"features": features})

            result = {
                "features": features,
                "prediction": model_result.get("prediction"),
            }
            return result, 200

        except requests.RequestException as e:
            logger.exception("Model service call failed")
            return {"error": f"Model service error: {e}"}, 502
        except Exception as e:
            logger.exception("Prediction failed")
            return {"error": str(e)}, 500
