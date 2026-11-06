-keep class com.ratansec.superagent.** { *; }
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}
