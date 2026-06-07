package com.entrenador.ia

import android.content.Context
import android.util.Log
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.records.*
import androidx.health.connect.client.request.AggregateRequest
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import org.json.JSONObject
import java.time.Duration
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter

class HealthSyncWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    companion object {
        private const val TAG = "HealthSyncWorker"
        const val WORK_NAME = "health_connect_daily_sync"
    }

    override suspend fun doWork(): Result {
        if (HealthConnectClient.getSdkStatus(applicationContext) != HealthConnectClient.SDK_AVAILABLE) {
            Log.w(TAG, "Health Connect no disponible")
            return Result.failure()
        }

        val client = HealthConnectClient.getOrCreate(applicationContext)
        val now = Instant.now()
        val windowStart = now.minus(Duration.ofHours(26))
        val timeRange = TimeRangeFilter.between(windowStart, now)
        val fecha = LocalDate.now().minusDays(1).toString()

        val payload = JSONObject().apply {
            put("fuente", "watch")
            put("fecha", fecha)
        }

        // ---- Pasos y calorías activas ----
        try {
            val agg = client.aggregate(
                AggregateRequest(
                    metrics = setOf(
                        StepsRecord.COUNT_TOTAL,
                        ActiveCaloriesBurnedRecord.ACTIVE_CALORIES_TOTAL
                    ),
                    timeRangeFilter = timeRange
                )
            )
            agg[StepsRecord.COUNT_TOTAL]?.let { payload.put("pasos", it.toInt()) }
            agg[ActiveCaloriesBurnedRecord.ACTIVE_CALORIES_TOTAL]
                ?.inKilocalories?.let { payload.put("kcal_activas", it.toInt()) }
        } catch (e: Exception) {
            Log.w(TAG, "Error pasos/calorías: ${e.message}")
        }

        // ---- FC en reposo ----
        try {
            val records = client.readRecords(
                ReadRecordsRequest(RestingHeartRateRecord::class, timeRange)
            ).records
            if (records.isNotEmpty()) {
                val avg = records.map { it.beatsPerMinute }.average().toInt()
                payload.put("fc_reposo", avg)
            }
        } catch (e: Exception) {
            Log.w(TAG, "Error FC reposo: ${e.message}")
        }

        // ---- HRV ----
        try {
            val records = client.readRecords(
                ReadRecordsRequest(HeartRateVariabilityRmssdRecord::class, timeRange)
            ).records
            if (records.isNotEmpty()) {
                val avg = records.map { it.heartRateVariabilityMillis }.average().toInt()
                payload.put("hrv", avg)
            }
        } catch (e: Exception) {
            Log.w(TAG, "Error HRV: ${e.message}")
        }

        // ---- SpO2 ----
        try {
            val records = client.readRecords(
                ReadRecordsRequest(OxygenSaturationRecord::class, timeRange)
            ).records
            if (records.isNotEmpty()) {
                val avg = records.map { it.percentage.value }.average()
                payload.put("spo2", avg)
            }
        } catch (e: Exception) {
            Log.w(TAG, "Error SpO2: ${e.message}")
        }

        // ---- Sueño ----
        try {
            val sessions = client.readRecords(
                ReadRecordsRequest(SleepSessionRecord::class, timeRange)
            ).records

            if (sessions.isNotEmpty()) {
                val main: SleepSessionRecord = sessions.maxByOrNull { s: SleepSessionRecord ->
                    Duration.between(s.startTime, s.endTime).toMillis()
                }!!

                val totalMin = Duration.between(main.startTime, main.endTime).toMinutes()
                payload.put("sueno_horas", Math.round((totalMin / 60.0) * 10.0) / 10.0)

                val fmt = DateTimeFormatter.ofPattern("HH:mm").withZone(ZoneId.systemDefault())
                payload.put("hora_acostarse", fmt.format(main.startTime))
                payload.put("hora_despertar", fmt.format(main.endTime))

                // Sleep stages
                try {
                    var remMin = 0L
                    var profundoMin = 0L
                    for (stage in main.stages) {
                        val dur = Duration.between(stage.startTime, stage.endTime).toMinutes()
                        when (stage.stage) {
                            SleepSessionRecord.STAGE_TYPE_REM -> remMin += dur
                            SleepSessionRecord.STAGE_TYPE_DEEP -> profundoMin += dur
                        }
                    }
                    payload.put("rem_min", remMin.toInt())
                    payload.put("profundo_min", profundoMin.toInt())
                } catch (e: Exception) {
                    Log.d(TAG, "Stages no disponibles: ${e.message}")
                }
            }
        } catch (e: Exception) {
            Log.w(TAG, "Error sueño: ${e.message}")
        }

        // ---- POST ----
        return try {
            val ok = ApiClient.postBiometricos(payload)
            if (ok) {
                Log.i(TAG, "Sync OK — $fecha $payload")
                applicationContext.getSharedPreferences("sync", Context.MODE_PRIVATE)
                    .edit()
                    .putLong("last_sync_ts", System.currentTimeMillis())
                    .putString("last_sync_fecha", fecha)
                    .apply()
                Result.success()
            } else {
                Log.w(TAG, "Backend error — reintentando")
                Result.retry()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error POST: ${e.message}")
            Result.retry()
        }
    }
}
