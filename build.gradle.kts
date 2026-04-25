plugins {
    alias(libs.plugins.android.application)
}

android {
    namespace = "com.example.gesturecontrolapp"

    // Simplified the compileSdk syntax
    compileSdk = 36

    defaultConfig {
        applicationId = "com.example.gesturecontrolapp"
        minSdk = 26 // This is correct, fixes the MethodHandle error
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"

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

    // --- THIS BLOCK NOW FIXES BOTH ERRORS ---
    packaging {
        resources {
            // This line fixes the first error
            excludes.add("META-INF/INDEX.LIST")

            // --- ADD THIS NEW LINE ---
            // This line fixes the new error you just found
            excludes.add("META-INF/io.netty.versions.properties")
        }
    }
    // --- END OF FIX ---

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
}

dependencies {
    // Default AndroidX libraries (from your file)
    implementation(libs.appcompat)
    implementation(libs.material)
    implementation(libs.activity)
    implementation(libs.constraintlayout)

    // Test libraries (from your file)
    testImplementation(libs.junit)
    androidTestImplementation(libs.ext.junit)
    androidTestImplementation(libs.espresso.core)

    // --- OUR CUSTOM LIBRARIES ---
    // You added these correctly! This syntax is perfect.

    // For MQTT Communication (HiveMQ)
    implementation("com.hivemq:hivemq-mqtt-client:1.3.1")

    // For TensorFlow Lite (The ML Model)
    implementation("org.tensorflow:tensorflow-lite:2.15.0")
    implementation("org.tensorflow:tensorflow-lite-support:0.4.4")
}