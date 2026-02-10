"""Utility modules for the Deep Sci-Fi platform."""


def __getattr__(name):
    if name in ("create_notification", "send_callback"):
        from .notifications import create_notification, send_callback
        globals()["create_notification"] = create_notification
        globals()["send_callback"] = send_callback
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["create_notification", "send_callback"]
