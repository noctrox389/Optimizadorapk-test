from __future__ import annotations

import os


def is_android() -> bool:
    return "ANDROID_ARGUMENT" in os.environ


def default_external_path() -> str:
    if not is_android():
        return os.path.abspath(os.path.expanduser("~/FNFOptimizer"))
    try:
        from android.storage import primary_external_storage_path
        return os.path.join(primary_external_storage_path(), "Download", "FNFOptimizer")
    except Exception:
        return "/storage/emulated/0/Download/FNFOptimizer"


def request_storage_permissions() -> str:
    """Request ordinary storage permissions and, on Android 11+, open All Files Access settings.

    This project is intended for sideload/testing. Google Play has additional policy
    restrictions for MANAGE_EXTERNAL_STORAGE.
    """
    if not is_android():
        return "No es Android: no se necesitan permisos."

    messages = []
    try:
        from android.permissions import request_permissions, Permission
        requested = []
        for name in ("READ_EXTERNAL_STORAGE", "WRITE_EXTERNAL_STORAGE", "READ_MEDIA_IMAGES"):
            value = getattr(Permission, name, None)
            if value is not None:
                requested.append(value)
        if requested:
            request_permissions(requested)
            messages.append("Permisos normales solicitados")
    except Exception as exc:
        messages.append(f"Permisos normales: {exc}")

    try:
        from jnius import autoclass
        BuildVersion = autoclass("android.os.Build$VERSION")
        if int(BuildVersion.SDK_INT) >= 30:
            Environment = autoclass("android.os.Environment")
            if not Environment.isExternalStorageManager():
                Settings = autoclass("android.provider.Settings")
                Intent = autoclass("android.content.Intent")
                Uri = autoclass("android.net.Uri")
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                activity = PythonActivity.mActivity
                intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                intent.setData(Uri.parse("package:" + activity.getPackageName()))
                activity.startActivity(intent)
                messages.append("Abriendo acceso a todos los archivos")
            else:
                messages.append("Acceso a todos los archivos ya concedido")
    except Exception as exc:
        messages.append(f"All files access: {exc}")

    return " | ".join(messages) or "Solicitud enviada."
