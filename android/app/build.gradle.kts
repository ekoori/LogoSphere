plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.serialization)
}

// Push notifications need the Firebase project's google-services.json beside this file (kept out
// of git). Without it the app builds and runs as before, just without push (see push/Push.kt).
if (file("google-services.json").exists()) {
    apply(plugin = "com.google.gms.google-services")
}

// The release key never enters the repository: its keystore and password are Gradle properties
// (in ~/.gradle/gradle.properties) or environment variables.
fun releaseSigning(property: String, variable: String): String? =
    providers.gradleProperty(property).orElse(providers.environmentVariable(variable)).orNull

val releaseKeystore = releaseSigning("logosphereKeystore", "LOGOSPHERE_KEYSTORE")

// The upload key (~/.android/logosphere-upload.jks, alias logosphere; docs/play/README.md). Without it a
// release build falls back to the debug key, which Google Play rejects: say so when one is asked for.
if (releaseKeystore == null && gradle.startParameter.taskNames.any { "release" in it.lowercase() }) {
    logger.warn("LogoSphere: no logosphereKeystore property, so this release is signed with the DEBUG key; Google Play will refuse it.")
}

// The version, and a version code derived from it so it always rises: 1.2.3 is 10203.
val appVersion = "0.4.0"
val appVersionCode = appVersion.split(".").map(String::toInt)
    .let { (major, minor, patch) -> major * 10_000 + minor * 100 + patch }

android {
    namespace = "com.krbavcic.logosphere"
    compileSdk = 36

    defaultConfig {
        applicationId = "earth.logosphere.app"
        minSdk = 26
        targetSdk = 36
        versionCode = appVersionCode
        versionName = appVersion

        // The LogoSphere server the app talks to. Debug builds can point elsewhere from the
        // sign-in screen (e.g. a local backend); release builds always use this one.
        buildConfigField("String", "DEFAULT_SERVER_URL", "\"https://logosphere.earth\"")
    }

    signingConfigs {
        create("release") {
            storeFile = releaseKeystore?.let { file(it) }
            storePassword = releaseSigning("logosphereKeystorePassword", "LOGOSPHERE_KEYSTORE_PASSWORD")
            keyAlias = "logosphere"
            // keytool's default PKCS12 keystore has one password for the store and its key.
            keyPassword =
                releaseSigning("logosphereKeyPassword", "LOGOSPHERE_KEY_PASSWORD") ?: storePassword
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            signingConfig = if (releaseKeystore != null) {
                signingConfigs.getByName("release")
            } else {
                // So the project still builds anywhere; a store will not accept the debug key.
                signingConfigs.getByName("debug")
            }
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
        compose = true
        buildConfig = true
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

dependencies {
    implementation(project(":core"))

    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.core.splashscreen)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.navigation.compose)
    implementation(libs.androidx.datastore.preferences)
    implementation(libs.kotlinx.coroutines.android)

    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.foundation)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.material.icons.extended)
    debugImplementation(libs.androidx.compose.ui.tooling)

    implementation(libs.coil.compose)
    implementation(libs.coil.svg)

    implementation(platform(libs.firebase.bom))
    implementation(libs.firebase.messaging)
    implementation(libs.kotlinx.coroutines.play.services)

    testImplementation(libs.junit)
}
