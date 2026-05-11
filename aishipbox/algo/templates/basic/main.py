#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""${name} - Algorithm Service Entry Point."""

from __future__ import annotations

import logging

from rest.process_base import ProcessBase
from .utils import example_function

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AlgoProcessor(ProcessBase):
    """Algorithm Processor - maintains API compatibility with hosting platform."""

    def __init__(self):
        super().__init__(url="")

    def process(self, params_dict: dict) -> tuple[dict, int]:
        value = params_dict.get("value", "default")
        result = example_function(value)
        return {"result": result}, 200
