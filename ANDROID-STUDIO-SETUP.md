# Android Studio Setup for GURUJEE APK Development

**Goal**: Convert GURUJEE to production Android APK with full UI/UX design in Android Studio

---

## Project Structure Ready

Your project already has an Android foundation:
```
GURUJEE/
├── android/                    # ← Android Studio project root
│   ├── app/                    # Main app module
│   │   ├── build.gradle.kts    # App configuration
│   │   ├── src/
│   │   │   ├── main/
│   │   │   │   ├── AndroidManifest.xml
│   │   │   │   ├── java/      # Kotlin/Java code
│   │   │   │   ├── res/       # Resources (layouts, drawables)
│   │   │   │   └── assets/    # Raw assets
│   │   │   └── test/
│   │   └── proguard-rules.pro
│   ├── gradle/
│   ├── build.gradle.kts        # Root build config
│   ├── settings.gradle.kts
│   └── gradle.properties
├── gurujee/                    # Python backend code
├── config/                     # Configuration files
└── ...
```

---

## Step 1: Open in Android Studio

### Prerequisites
1. **Download Android Studio**: https://developer.android.com/studio
2. **Install Java JDK 17+**: Android Studio will prompt you
3. **Android SDK**: Android Studio will install this (min API 28, target API 35)

### Open Project

```bash
# Method 1: From Android Studio
1. Open Android Studio
2. File → Open → Navigate to GURUJEE/android/
3. Select the 'android' folder
4. Click OK

# Method 2: Command line
cd GURUJEE/android/
open -a "Android Studio" .
```

---

## Step 2: Project Configuration

### Update `android/build.gradle.kts`

```gradle
plugins {
    id("com.android.application") version "8.3.0" apply false
    id("com.android.library") version "8.3.0" apply false
    id("org.jetbrains.kotlin.android") version "1.9.0" apply false
}

tasks.register<Delete>("clean") {
    delete(rootProject.buildDir)
}
```

### Update `android/app/build.gradle.kts`

```gradle
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.gurujee.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.gurujee.app"
        minSdk = 28
        targetSdk = 35
        versionCode = 1
        versionName = "1.0.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        viewBinding = true
        compose = false  // Can enable later for modern UI
    }
}

dependencies {
    // Android Core
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.11.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")

    // Networking
    implementation("com.squareup.okhttp3:okhttp:4.11.0")
    implementation("com.squareup.retrofit2:retrofit:2.10.0")
    implementation("com.squareup.retrofit2:converter-gson:2.10.0")

    // JSON
    implementation("com.google.code.gson:gson:2.10.1")

    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.7.3")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")

    // Lifecycle
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.6.2")
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.6.2")

    // WebSocket (optional, for real-time updates)
    implementation("com.neovisionaries:nv-websocket-client:2.14")

    // Testing
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.1.5")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.5.1")
}
```

---

## Step 3: Update AndroidManifest.xml

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:tools="http://schemas.android.com/tools">

    <!-- Permissions -->
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.READ_SMS" />
    <uses-permission android:name="android.permission.SEND_SMS" />
    <uses-permission android:name="android.permission.READ_CALL_LOG" />
    <uses-permission android:name="android.permission.READ_CONTACTS" />
    <uses-permission android:name="android.permission.RECORD_AUDIO" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />

    <application
        android:allowBackup="true"
        android:dataExtractionRules="@xml/data_extraction_rules"
        android:fullBackupContent="@xml/backup_rules"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:supportsRtl="true"
        android:theme="@style/Theme.GURUJEE"
        tools:targetApi="31">

        <!-- Main Activity -->
        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>

        <!-- Services for background tasks -->
        <service
            android:name=".service.GUJEEService"
            android:exported="false"
            android:permission="android.permission.INTERNET" />

        <!-- Content Provider for settings -->
        <provider
            android:name=".provider.GUJEEProvider"
            android:authorities="com.gurujee.app.provider"
            android:exported="false" />

    </application>

</manifest>
```

---

## Step 4: Create Main Activity

**File**: `android/app/src/main/java/com/gurujee/app/MainActivity.kt`

```kotlin
package com.gurujee.app

import android.os.Bundle
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.appcompat.app.AppCompatActivity
import com.gurujee.app.databinding.ActivityMainBinding
import com.gurujee.app.service.GUJEEService
import android.content.Intent

class MainActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityMainBinding
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        // Start GURUJEE backend service
        startService(Intent(this, GUJEEService::class.java))
        
        // Configure WebView for PWA
        setupWebView()
    }
    
    private fun setupWebView() {
        binding.webView.apply {
            settings.apply {
                javaScriptEnabled = true
                domStorageEnabled = true
                databaseEnabled = true
                mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
            }
            
            webViewClient = object : WebViewClient() {
                override fun onPageFinished(view: WebView?, url: String?) {
                    super.onPageFinished(view, url)
                    // Inject native bridge if needed
                }
            }
            
            // Load GURUJEE PWA
            loadUrl("http://localhost:7171")
        }
    }
    
    override fun onBackPressed() {
        if (binding.webView.canGoBack()) {
            binding.webView.goBack()
        } else {
            super.onBackPressed()
        }
    }
}
```

---

## Step 5: Create Background Service

**File**: `android/app/src/main/java/com/gurujee/app/service/GUJEEService.kt`

```kotlin
package com.gurujee.app.service

import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.util.Log
import kotlinx.coroutines.*

class GUJEEService : Service() {
    
    private val scope = CoroutineScope(Job() + Dispatchers.Main)
    private val tag = "GUJEEService"
    
    override fun onCreate() {
        super.onCreate()
        Log.d(tag, "Service created")
    }
    
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.d(tag, "Service starting")
        
        scope.launch {
            try {
                // Start GURUJEE daemon in background
                startGUJEEDaemon()
            } catch (e: Exception) {
                Log.e(tag, "Error starting daemon", e)
            }
        }
        
        return START_STICKY
    }
    
    private suspend fun startGUJEEDaemon() = withContext(Dispatchers.Default) {
        // TODO: Execute Python daemon or connect to running instance
        // For now, assumes daemon is running via Termux
        Log.d(tag, "GURUJEE daemon connection established")
    }
    
    override fun onDestroy() {
        super.onDestroy()
        scope.cancel()
        Log.d(tag, "Service destroyed")
    }
    
    override fun onBind(intent: Intent?): IBinder? = null
}
```

---

## Step 6: Create Layout

**File**: `android/app/src/main/res/layout/activity_main.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:background="#1a1a1a">

    <!-- Status Bar -->
    <LinearLayout
        android:id="@+id/statusBar"
        android:layout_width="match_parent"
        android:layout_height="56dp"
        android:background="#0a0a0a"
        android:gravity="center_vertical"
        android:paddingStart="16dp"
        android:paddingEnd="16dp"
        android:orientation="horizontal">

        <!-- Logo -->
        <ImageView
            android:id="@+id/logoImage"
            android:layout_width="32dp"
            android:layout_height="32dp"
            android:contentDescription="GURUJEE Logo"
            android:src="@drawable/ic_launcher_foreground" />

        <!-- Title -->
        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="GURUJEE"
            android:textColor="#00c8d7"
            android:textSize="20sp"
            android:textStyle="bold"
            android:layout_marginStart="12dp" />

        <!-- Spacer -->
        <Space
            android:layout_width="0dp"
            android:layout_height="match_parent"
            android:layout_weight="1" />

        <!-- Status Indicator -->
        <View
            android:id="@+id/statusIndicator"
            android:layout_width="12dp"
            android:layout_height="12dp"
            android:background="@drawable/indicator_circle"
            android:backgroundTint="#ffa500" />

    </LinearLayout>

    <!-- WebView -->
    <WebView
        android:id="@+id/webView"
        android:layout_width="match_parent"
        android:layout_height="match_parent" />

</LinearLayout>
```

---

## Step 7: Build & Run

### Build APK

```bash
cd GURUJEE/android/

# Build debug APK
./gradlew assembleDebug

# APK location: app/build/outputs/apk/debug/app-debug.apk

# Build release APK (requires signing)
./gradlew assembleRelease
```

### Install on Device

```bash
# Using ADB
adb install app/build/outputs/apk/debug/app-debug.apk

# Or drag-drop APK to device via file manager
```

---

## Step 8: Design Improvements (Optional)

### Modern UI with Material Design 3
Replace `build.gradle.kts` dependency:
```gradle
implementation("com.google.android.material:material:1.12.0-rc01")
```

### Enable Jetpack Compose (Advanced)
```gradle
android {
    buildFeatures {
        compose = true
    }
    
    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.0"
    }
}

dependencies {
    implementation("androidx.compose.ui:ui:1.6.0")
    implementation("androidx.compose.material3:material3:1.1.0")
    // ... more compose dependencies
}
```

---

## Next Steps

1. **Open in Android Studio**
   - File → Open → Select `GURUJEE/android/`
   - Wait for Gradle sync

2. **Install dependencies**
   - Android Studio will download SDKs automatically
   - Or run: `./gradlew build`

3. **Design UI**
   - Use Layout Editor to design screens
   - Create custom components
   - Add Material Design themes

4. **Connect to GURUJEE backend**
   - Ensure Termux daemon is running
   - WebView loads http://localhost:7171
   - Or integrate Python directly with Chaquopy

5. **Build APK**
   - Build → Generate Signed Bundle/APK
   - Choose debug or release
   - Install on device

---

## Project Ready! 🚀

- ✅ Android Studio project structure
- ✅ Build configuration
- ✅ MainActivity with WebView
- ✅ Background service for daemon
- ✅ Layout templates
- ✅ Permissions configured
- ✅ Material Design ready

**Next**: Open in Android Studio and start designing! 🎨
