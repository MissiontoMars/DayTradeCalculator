from __future__ import annotations

import io
from typing import Any, Protocol

import numpy as np
from PIL import Image
from rapidocr_onnxruntime import RapidOCR


class _OcrLike(Protocol):
    def run(self, image: Image.Image) -> list[dict[str, Any]]:
        ...


class RapidOcrWrapper:
    def __init__(self) -> None:
        self._ocr = RapidOCR()

    def run(self, image: Image.Image) -> list[dict[str, Any]]:
        rgb = image.convert("RGB")
        arr = np.array(rgb)
        result, _elapse = self._ocr(arr)
        items: list[dict[str, Any]] = []
        if not result:
            return items
        for box, text, score in result:
            items.append({"box": box, "text": text, "score": score})
        return items


class MacOsVisionOcrWrapper:
    def __init__(self) -> None:
        import Quartz
        import Vision
        from Foundation import NSData

        self._Quartz = Quartz
        self._Vision = Vision
        self._NSData = NSData
        self._ctx = Quartz.CIContext.contextWithOptions_(None)

    def run(self, image: Image.Image) -> list[dict[str, Any]]:
        Quartz = self._Quartz
        Vision = self._Vision
        NSData = self._NSData

        buf = io.BytesIO()
        image.convert("RGB").save(buf, format="PNG")
        data = NSData.dataWithBytes_length_(buf.getvalue(), len(buf.getvalue()))
        ci = Quartz.CIImage.imageWithData_(data)
        if ci is None:
            return []
        cg = self._ctx.createCGImage_fromRect_(ci, ci.extent())
        if cg is None:
            return []

        items: list[dict[str, Any]] = []

        def handler(req, _err) -> None:
            results = req.results() or []
            w, h = image.size
            for obs in results:
                cand = (obs.topCandidates_(1) or [None])[0]
                if cand is None:
                    continue
                text = str(cand.string() or "")
                conf = float(cand.confidence() or 0.0)
                bb = obs.boundingBox()
                x = float(bb.origin.x) * w
                y = float(bb.origin.y) * h
                bw = float(bb.size.width) * w
                bh = float(bb.size.height) * h
                y_top = h - (y + bh)
                box = [[x, y_top], [x + bw, y_top], [x + bw, y_top + bh], [x, y_top + bh]]
                items.append({"box": box, "text": text, "score": conf})

        req = Vision.VNRecognizeTextRequest.alloc().initWithCompletionHandler_(handler)
        req.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
        req.setUsesLanguageCorrection_(True)
        req.setRecognitionLanguages_(["zh-Hans", "en-US"])

        hdl = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg, None)
        _ok, _err = hdl.performRequests_error_([req], None)
        return items


class OcrEngine:
    def __init__(self) -> None:
        self._engine: _OcrLike
        try:
            self._engine = MacOsVisionOcrWrapper()
            self.engine_name = "macOS Vision"
        except Exception:
            self._engine = RapidOcrWrapper()
            self.engine_name = "RapidOCR"

    def ocr(self, image: Image.Image) -> list[dict[str, Any]]:
        return self._engine.run(image)


engine = OcrEngine()
