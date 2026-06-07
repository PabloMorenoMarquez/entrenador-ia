package com.entrenador.ia

import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.PermissionController
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.*
import androidx.lifecycle.lifecycleScope
import androidx.work.*
import com.entrenador.ia.databinding.ActivityMainBinding
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*
import java.util.concurrent.TimeUnit

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    companion object {
        val PERMISOS = setOf(
            HealthPermission.getReadPermission(StepsRecord::class),
            HealthPermission.getReadPermission(RestingHeartRateRecord::class),
            HealthPermission.getReadPermission(HeartRateVariabilityRmssdRecord::class),
            HealthPermission.getReadPermission(OxygenSaturationRecord::class),
            HealthPermission.getReadPermission(SleepSessionRecord::class),
            HealthPermission.getReadPermission(ActiveCaloriesBurnedRecord::class),
        )
    }

    private val requestPermissions = registerForActivityResult(
        PermissionController.createRequestPermissionResultContract()
    ) { granted ->
        if (granted.containsAll(PERMISOS)) {
            scheduleSync()
            updateStatus()
        } else {
            Toast.makeText(this, "Permisos necesarios para sincronizar", Toast.LENGTH_LONG).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.btnSync.setOnClickListener { triggerManualSync() }
        binding.btnPermisos.setOnClickListener { solicitarPermisos() }

        updateStatus()
        checkAndInit()
    }

    private fun checkAndInit() {
        if (HealthConnectClient.getSdkStatus(this) != HealthConnectClient.SDK_AVAILABLE) {
            binding.tvEstado.text = "Health Connect no disponible en este dispositivo."
            return
        }
        lifecycleScope.launch {
            val client = HealthConnectClient.getOrCreate(this@MainActivity)
            val granted = client.permissionController.getGrantedPermissions()
            if (granted.containsAll(PERMISOS)) {
                scheduleSync()
            }
        }
    }

    private fun solicitarPermisos() {
        if (HealthConnectClient.getSdkStatus(this) != HealthConnectClient.SDK_AVAILABLE) {
            Toast.makeText(this, "Health Connect no disponible", Toast.LENGTH_SHORT).show()
            return
        }
        requestPermissions.launch(PERMISOS)
    }

    private fun scheduleSync() {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

        val request = PeriodicWorkRequestBuilder<HealthSyncWorker>(1, TimeUnit.DAYS)
            .setConstraints(constraints)
            .setInitialDelay(calcularRetardoHasta8am(), TimeUnit.MILLISECONDS)
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 15, TimeUnit.MINUTES)
            .build()

        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            HealthSyncWorker.WORK_NAME,
            ExistingPeriodicWorkPolicy.KEEP,
            request
        )
    }

    private fun triggerManualSync() {
        if (HealthConnectClient.getSdkStatus(this) != HealthConnectClient.SDK_AVAILABLE) {
            Toast.makeText(this, "Health Connect no disponible", Toast.LENGTH_SHORT).show()
            return
        }
        val oneTime = OneTimeWorkRequestBuilder<HealthSyncWorker>()
            .setConstraints(
                Constraints.Builder()
                    .setRequiredNetworkType(NetworkType.CONNECTED)
                    .build()
            )
            .build()

        WorkManager.getInstance(this).enqueue(oneTime)
        binding.tvEstado.text = "Sincronizando…"

        WorkManager.getInstance(this)
            .getWorkInfoByIdLiveData(oneTime.id)
            .observe(this) { info ->
                when (info?.state) {
                    WorkInfo.State.SUCCEEDED -> {
                        Toast.makeText(this, "Sync completado", Toast.LENGTH_SHORT).show()
                        updateStatus()
                    }
                    WorkInfo.State.FAILED -> {
                        Toast.makeText(this, "Error — revisa conexión o API key", Toast.LENGTH_LONG).show()
                        updateStatus()
                    }
                    else -> {}
                }
            }
    }

    private fun updateStatus() {
        val prefs = getSharedPreferences("sync", MODE_PRIVATE)
        val ts = prefs.getLong("last_sync_ts", 0L)
        val fecha = prefs.getString("last_sync_fecha", null)

        binding.tvEstado.text = if (ts == 0L) {
            "Sin sincronizaciones todavía."
        } else {
            val hora = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date(ts))
            "Último sync: $fecha a las $hora"
        }
        binding.tvUrl.text = "Backend: ${BuildConfig.API_BASE_URL}"
    }

    private fun calcularRetardoHasta8am(): Long {
        val ahora = Calendar.getInstance()
        val objetivo = Calendar.getInstance().apply {
            set(Calendar.HOUR_OF_DAY, 8)
            set(Calendar.MINUTE, 0)
            set(Calendar.SECOND, 0)
            set(Calendar.MILLISECOND, 0)
            if (!after(ahora)) add(Calendar.DAY_OF_MONTH, 1)
        }
        return objetivo.timeInMillis - ahora.timeInMillis
    }
}
