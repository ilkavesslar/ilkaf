"""Anonymous cross-camera continuity hypotheses. Never face recognition or named identity."""

from cv.identity.anonymous import (
    MATCHER_VERSION,
    AnonymousIdentityMatcher,
    AppearanceSignature,
    CameraTopology,
    CameraTransition,
    GlobalAnonymousPersonId,
    IdentityAssignment,
    MatcherConfig,
    appearance_histogram,
)

__all__ = [
    "MATCHER_VERSION",
    "AnonymousIdentityMatcher",
    "AppearanceSignature",
    "CameraTopology",
    "CameraTransition",
    "GlobalAnonymousPersonId",
    "IdentityAssignment",
    "MatcherConfig",
    "appearance_histogram",
]
