[app]

# Application metadata
title = GURUJEE
package.name = gurujee
package.domain = ai.gurujee
version = 1.0.0

# Source files (Thin launcher)
source.dir = .
source.include_exts = py,png,jpg,apk,sh,yaml,yml,json,md,kv

# Requirements (ARM64 Termux-compatible)
requirements = python3,kivy,requests,jnius,android

# Orientation and window
orientation = portrait
fullscreen = 0

# Android settings
android.api = 34
android.minapi = 29
android.ndk = 25c
android.archs = arm64-v8a
android.copy_libs = 1

# Permissions required by launcher
android.permissions = \
    INTERNET, \
    REQUEST_INSTALL_PACKAGES, \
    READ_EXTERNAL_STORAGE, \
    WRITE_EXTERNAL_STORAGE, \
    QUERY_ALL_PACKAGES, \
    com.termux.permission.RUN_COMMAND

# Presplash and icon
presplash.filename = assets/presplash.png
icon.filename = assets/icon.png

# Gradle / build extras
android.gradle_dependencies =
android.enable_androidx = True

[buildozer]
log_level = 2
warn_on_root = 1
