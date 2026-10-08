# Kotlin/Java reflection entry points that R8 must never rename or strip.
# (minifyEnabled is false in release today — these rules are here so turning R8 on is a
# one-line change that stays safe for the WebView bridge.)
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}
-keep class io.github.ratanpatel.ratanagent.MainActivity { *; }
-keep class io.github.ratanpatel.ratanagent.AgentBridge { *; }
-keepclassmembers class io.github.ratanpatel.ratanagent.AgentBridge {
    public *;
}

# Keep annotations used by the runtime
-keepattributes *Annotation*, JavascriptInterface

# WebView posts messages through reflection on some OEM builds
-keepclassmembers class * extends android.webkit.WebViewClient { *; }
-keepclassmembers class * extends android.webkit.WebChromeClient { *; }
