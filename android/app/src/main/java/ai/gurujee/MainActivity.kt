package ai.gurujee

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.activity.compose.setContent
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executor

class MainActivity : FragmentActivity() { // FragmentActivity required for Biometric
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        createNotificationChannel()
        setContent {
            GurujeeTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = Color.Black
                ) {
                    GurujeeApp()
                }
            }
        }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val name = "GURUJEE Service"
            val descriptionText = "Notifications for GURUJEE background tasks"
            val importance = NotificationManager.IMPORTANCE_DEFAULT
            val channel = NotificationChannel("GURUJEE_CHANNEL", name, importance).apply {
                description = descriptionText
            }
            val notificationManager: NotificationManager =
                getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }
}

@Composable
fun GurujeeTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = Color(0xFFFFBF00), // Amber
            background = Color.Black,
            surface = Color.Black,
            onPrimary = Color.Black,
            onBackground = Color(0xFFFFBF00),
            onSurface = Color(0xFFFFBF00)
        ),
        content = content
    )
}

@Composable
fun GurujeeApp() {
    val navController = rememberNavController()
    NavHost(navController = navController, startDestination = "splash") {
        composable("splash") { SplashScreen(navController) }
        composable("auth") { AuthScreen(navController) }
        composable("setup") { SetupScreen(navController) }
        composable("chat") { ChatScreen() }
    }
}

@Composable
fun SplashScreen(navController: NavHostController) {
    val context = LocalContext.current
    var statusText by remember { mutableStateOf("Initializing GURUJEE...") }
    var showInstallButton by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        delay(2000)
        if (isTermuxInstalled(context)) {
            navController.navigate("auth") {
                popUpTo("splash") { inclusive = true }
            }
        } else {
            statusText = "Termux is required but not installed.\nPlease install it from F-Droid."
            showInstallButton = true
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(
            text = "GURUJEE",
            color = Color(0xFFFFBF00),
            fontSize = 48.sp,
            fontWeight = FontWeight.Bold
        )
        Spacer(modifier = Modifier.height(24.dp))
        CircularProgressIndicator(color = Color(0xFFFFBF00))
        Spacer(modifier = Modifier.height(24.dp))
        Text(
            text = statusText,
            color = Color(0xFFFFBF00),
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(16.dp)
        )
        if (showInstallButton) {
            Button(
                onClick = {
                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse("https://f-droid.org/packages/com.termux/"))
                    context.startActivity(intent)
                },
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFFFBF00))
            ) {
                Text("Install Termux", color = Color.Black)
            }
            Spacer(modifier = Modifier.height(8.dp))
            TextButton(
                onClick = {
                    navController.navigate("auth") {
                        popUpTo("splash") { inclusive = true }
                    }
                }
            ) {
                Text("Already installed? Skip", color = Color(0xFFFFBF00))
            }
        }
    }
}

@Composable
fun AuthScreen(navController: NavHostController) {
    val context = LocalContext.current as FragmentActivity
    val executor = ContextCompat.getMainExecutor(context)
    
    val biometricPrompt = BiometricPrompt(context, executor,
        object : BiometricPrompt.AuthenticationCallback() {
            override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                super.onAuthenticationSucceeded(result)
                navController.navigate("setup") {
                    popUpTo("auth") { inclusive = true }
                }
            }

            override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                super.onAuthenticationError(errorCode, errString)
                Toast.makeText(context, "Auth error: $errString", Toast.LENGTH_SHORT).show()
            }
        })

    val promptInfo = BiometricPrompt.PromptInfo.Builder()
        .setTitle("GURUJEE Biometric Lock")
        .setSubtitle("Authenticate to access your AI companion")
        .setNegativeButtonText("Use PIN")
        .build()

    LaunchedEffect(Unit) {
        biometricPrompt.authenticate(promptInfo)
    }

    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Button(onClick = { biometricPrompt.authenticate(promptInfo) }) {
            Text("Unlock GURUJEE", color = Color.Black)
        }
    }
}

@Composable
fun SetupScreen(navController: NavHostController) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var logText by remember { mutableStateOf("Launching GURUJEE installation...") }
    val installCommand = "curl -fsSL https://raw.githubusercontent.com/staimoorulhassan/GURUJEE/main/install.sh | bash && gurujee --onboard && gurujee start"

    LaunchedEffect(Unit) {
        showNotification(context, "GURUJEE", "Setup is running in background...")
        launchTermuxCommand(context, installCommand)
        
        scope.launch {
            var attempt = 0
            while (true) {
                attempt++
                try {
                    val url = URL("http://127.0.0.1:7171/health")
                    val connection = url.openConnection() as HttpURLConnection
                    connection.connectTimeout = 2000
                    val responseCode = connection.responseCode
                    if (responseCode == 200) {
                        logText += "\n✓ Daemon ready!"
                        showNotification(context, "GURUJEE", "AI is online and ready!")
                        navController.navigate("chat") {
                            popUpTo("setup") { inclusive = true }
                        }
                        break
                    } else {
                        logText += "\n  [$attempt] Daemon responding with $responseCode..."
                    }
                } catch (e: Exception) {
                    logText += "\n  [$attempt] Waiting for daemon (127.0.0.1:7171)..."
                }
                delay(3000)
            }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            text = "Setup",
            color = Color(0xFFFFBF00),
            fontSize = 24.sp,
            fontWeight = FontWeight.Bold
        )
        Spacer(modifier = Modifier.height(16.dp))
        
        Card(
            modifier = Modifier.fillMaxWidth().weight(1f),
            colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A1A))
        ) {
            Text(
                text = logText,
                color = Color(0xFFFFBF00),
                fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace,
                fontSize = 12.sp,
                modifier = Modifier.padding(12.dp).fillMaxSize()
            )
        }

        Spacer(modifier = Modifier.height(16.dp))

        Text(
            text = "If Termux didn't open automatically:",
            color = Color.Gray,
            fontSize = 12.sp
        )
        
        Spacer(modifier = Modifier.height(8.dp))

        Button(
            onClick = {
                val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as android.content.ClipboardManager
                val clip = android.content.ClipData.newPlainText("GURUJEE Install", installCommand)
                clipboard.setPrimaryClip(clip)
                Toast.makeText(context, "Command copied! Paste it in Termux.", Toast.LENGTH_LONG).show()
                
                try {
                    val intent = context.packageManager.getLaunchIntentForPackage("com.termux")
                    context.startActivity(intent)
                } catch (e: Exception) {
                    Toast.makeText(context, "Could not open Termux", Toast.LENGTH_SHORT).show()
                }
            },
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFFFBF00))
        ) {
            Text("Copy Command & Open Termux", color = Color.Black)
        }
        
        Spacer(modifier = Modifier.height(16.dp))
    }
}

@Composable
fun ChatScreen() {
    AndroidView(
        factory = { context ->
            WebView(context).apply {
                settings.apply {
                    javaScriptEnabled = true
                    domStorageEnabled = true
                    loadWithOverviewMode = true
                    useWideViewPort = true
                }
                webViewClient = WebViewClient()
                loadUrl("http://127.0.0.1:7171")
            }
        },
        modifier = Modifier.fillMaxSize()
    )
}

fun isTermuxInstalled(context: android.content.Context): Boolean {
    return try {
        context.packageManager.getPackageInfo("com.termux", 0)
        true
    } catch (e: Exception) {
        false
    }
}

fun launchTermuxCommand(context: android.content.Context, command: String) {
    try {
        val intent = Intent("com.termux.RUN_COMMAND").apply {
            setClassName("com.termux", "com.termux.app.RunCommandService")
            putExtra("com.termux.RUN_COMMAND_PATH", "/data/data/com.termux/files/usr/bin/bash")
            putExtra("com.termux.RUN_COMMAND_ARGUMENTS", arrayOf("-c", command))
            putExtra("com.termux.RUN_COMMAND_BACKGROUND", false)
            putExtra("com.termux.RUN_COMMAND_SESSION_ACTION", "0") 
        }
        context.startService(intent)
        Toast.makeText(context, "Attempting to trigger Termux...", Toast.LENGTH_SHORT).show()
    } catch (e: Exception) {
        e.printStackTrace()
    }
}

fun showNotification(context: Context, title: String, message: String) {
    val builder = NotificationCompat.Builder(context, "GURUJEE_CHANNEL")
        .setSmallIcon(android.R.drawable.ic_dialog_info)
        .setContentTitle(title)
        .setContentText(message)
        .setPriority(NotificationCompat.PRIORITY_DEFAULT)
        .setAutoCancel(true)

    val notificationManager: NotificationManager =
        context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
    notificationManager.notify(1, builder.build())
}
