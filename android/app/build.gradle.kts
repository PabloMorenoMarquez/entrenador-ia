import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
}

// Lee API_BASE_URL y API_KEY de local.properties (git-ignorado)
val localProps = Properties().also { props ->
    val f = rootProject.file("local.properties")
    if (f.exists()) props.load(f.inputStream())
}

android {
    namespace = "com.entrenador.ia"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.entrenador.ia"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"

        buildConfigField(
            "String", "API_BASE_URL",
            "\"${localProps.getProperty("API_BASE_URL", "https://YOUR_APP.onrender.com")}\""
        )
        buildConfigField(
            "String", "API_KEY",
            "\"${localProps.getProperty("API_KEY", "")}\""
        )
    }

    buildFeatures {
        buildConfig = true
        viewBinding = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }
    kotlinOptions { jvmTarget = "1.8" }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.appcompat)
    implementation(libs.material)
    implementation(libs.health.connect)
    implementation(libs.work.runtime.ktx)
    implementation(libs.okhttp)
    implementation(libs.kotlinx.coroutines.android)
}
