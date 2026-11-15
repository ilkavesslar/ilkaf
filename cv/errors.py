"""Errors for the CV ingest library. These are not HTTP API errors."""


class VideoSourceError(Exception):
    """Invalid path, unsupported container, or source not open."""


class VideoDecodeError(VideoSourceError):
    """A frame could not be decoded from an otherwise opened file."""


class CvDependencyError(VideoSourceError):
    """Raised when video ingest needs OpenCV and it is not installed."""


class DetectorError(Exception):
    """Person-detector failures. Not incidents, alerts, or HTTP errors."""


class DetectorDependencyError(CvDependencyError, DetectorError):
    """Raised when the optional CPU detector needs Torch or TorchVision."""


class DetectorModelError(DetectorError):
    """Weights path is missing, unreadable, or not a valid state dict."""


class DetectorInferenceError(DetectorError):
    """A frame could not be converted or the model forward pass failed."""
