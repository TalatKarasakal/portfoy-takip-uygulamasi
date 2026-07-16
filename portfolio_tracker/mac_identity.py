"""macOS Dock kimliği: python ile açıldığında Dock'ta uygulama simgesini/adını
ayarlar (PyObjC/Cocoa)."""
from __future__ import annotations
import os
import sys


def set_dock_name(name: str) -> None:
    if sys.platform != "darwin":
        return
    try:
        from Foundation import NSBundle
        b = NSBundle.mainBundle()
        info = b.localizedInfoDictionary() or b.infoDictionary()
        if info is not None:
            info["CFBundleName"] = name
            info["CFBundleDisplayName"] = name
    except Exception:
        pass


def set_dock_icon(icon_path: str) -> None:
    if sys.platform != "darwin":
        return
    if not icon_path or not os.path.exists(icon_path):
        return
    try:
        from AppKit import NSApplication, NSImage
        img = NSImage.alloc().initWithContentsOfFile_(icon_path)
        if img is not None:
            NSApplication.sharedApplication().setApplicationIconImage_(img)
    except Exception:
        pass
