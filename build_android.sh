#!/bin/bash

# GURUJEE Android Build Script
# This script prepares and builds the native Android application.

set -e

echo "🤖 GURUJEE Android Builder"
echo "--------------------------"

# Check for Android SDK
if [ -z "$ANDROID_HOME" ]; then
    echo "❌ ERROR: ANDROID_HOME is not set."
    echo "Please set it to your Android SDK path (e.g., export ANDROID_HOME=/path/to/sdk)"
    exit 1
fi

cd android

# Initialize Gradle wrapper if it doesn't exist
if [ ! -f "gradlew" ]; then
    echo "📦 Initializing Gradle Wrapper..."
    # If system gradle is not available, we assume the user will open in Android Studio
    if command -v gradle >/dev/null 2>&1; then
        gradle wrapper
    else
        echo "⚠️  System 'gradle' not found. Please open the 'android' folder in Android Studio"
        echo "to let it initialize the project and build the APK."
        exit 1
    fi
fi

echo "🔨 Building GURUJEE Debug APK..."
./gradlew assembleDebug

echo ""
echo "✅ Build Complete!"
echo "📍 APK Location: android/app/build/outputs/apk/debug/app-debug.apk"
echo ""
echo "Next steps:"
echo "1. Transfer the APK to your phone."
echo "2. Install and grant Biometric/Notification permissions."
echo "3. Ensure Termux is installed from F-Droid."
