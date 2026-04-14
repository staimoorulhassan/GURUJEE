[app]

# Application metadata
title = GURUJEE
package.name = gurujee
package.domain = ai.gurujee
version = 1.0.0

# Source files
source.dir = ..
source.include_exts = py,apk,sh,yaml,yml,json,md

# Requirements (ARM64 Termux-compatible)
requirements = python3==3.11.9,kivy==2.3.0,requests,jnius,android

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
    QUERY_ALL_PACKAGES

# Bundle Termux + Termux:API APKs as assets (copied to /sdcard/DCIM/ on first run)
# Place termux.apk and termux-api.apk in launcher/assets/ before building.
android.add_aars =
android.add_jars =

# Presplash and icon (place files in launcher/assets/)
presplash.filename = %(source.dir)s/launcher/assets/presplash.png
icon.filename = %(source.dir)s/launcher/assets/icon.png

# Gradle / build extras
android.gradle_dependencies =
android.enable_androidx = True

# Release signing (set via env vars; do NOT hardcode)
# android.keystore = %(GURUJEE_KEYSTORE)s
# android.keystore_alias = %(GURUJEE_KEY_ALIAS)s
# android.keystore_passwd = %(GURUJEE_KEYSTORE_PASS)s
# android.keyalias_passwd = %(GURUJEE_KEY_PASS)s

[buildozer]

# Log verbosity (0=quiet, 1=normal, 2=verbose)
log_level = 2

# Warn only; do not fail on missing optional assets
warn_on_root = 1
