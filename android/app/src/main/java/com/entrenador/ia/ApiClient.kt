package com.entrenador.ia

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit

object ApiClient {

    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()

    private val JSON = "application/json; charset=utf-8".toMediaType()

    /**
     * POST /api/biometricos con X-API-Key header.
     * Lanza excepción si HTTP != 2xx.
     */
    fun postBiometricos(payload: JSONObject): Boolean {
        val body = payload.toString().toRequestBody(JSON)
        val request = Request.Builder()
            .url("${BuildConfig.API_BASE_URL}/api/biometricos")
            .addHeader("X-Api-Key", BuildConfig.API_KEY)
            .post(body)
            .build()

        client.newCall(request).execute().use { response ->
            return response.isSuccessful
        }
    }
}
