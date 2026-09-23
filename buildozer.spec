[app]
title = FNF Optimizer
package.name = fnfoptimizer
package.domain = org.fnfmods
source.dir = .
source.include_exts = py,txt,md,spec
source.exclude_dirs = .git,.github,.buildozer,bin,legacy_cli,tests
version = 0.1.0
requirements = python3,kivy,pillow
orientation = portrait
fullscreen = 0

# Sin icon.filename: usa el recurso por defecto de la cadena de compilación.
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE,READ_MEDIA_IMAGES
android.api = 35
android.minapi = 23
android.ndk = 28c
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
