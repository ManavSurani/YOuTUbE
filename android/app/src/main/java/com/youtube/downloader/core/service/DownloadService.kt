package com.youtube.downloader.core.service

import android.app.Notification
import android.app.PendingIntent
import android.app.Service
import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.os.IBinder
import android.provider.MediaStore
import androidx.core.app.NotificationCompat
import com.yausername.youtubedl_android.YoutubeDL
import com.yausername.youtubedl_android.YoutubeDLRequest
import com.youtube.downloader.MainActivity
import com.youtube.downloader.R
import com.youtube.downloader.YouTubeApp
import com.youtube.downloader.core.database.AppDatabase
import com.youtube.downloader.core.database.HistoryEntity
import com.youtube.downloader.core.model.DownloadProgress
import com.youtube.downloader.core.model.DownloadType
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.io.File
import java.io.FileInputStream

class DownloadService : Service() {

    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var currentProcessId: String? = null
    private var isCancelled = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START_DOWNLOAD -> {
                val url = intent.getStringExtra(EXTRA_URL) ?: return START_NOT_STICKY
                val title = intent.getStringExtra(EXTRA_TITLE) ?: "YouTube Media"
                val type = intent.getStringExtra(EXTRA_TYPE) ?: "video"
                val height = if (intent.hasExtra(EXTRA_HEIGHT)) intent.getIntExtra(EXTRA_HEIGHT, 0) else null
                val audioFormat = intent.getStringExtra(EXTRA_AUDIO_FORMAT) ?: "mp3"
                val qualityLabel = intent.getStringExtra(EXTRA_QUALITY_LABEL) ?: ""

                startForeground(NOTIFICATION_ID, buildNotification(title, "Starting download…", 0))
                startDownload(url, title, type, height, audioFormat, qualityLabel)
            }
            ACTION_CANCEL -> {
                cancelCurrentDownload()
            }
        }
        return START_NOT_STICKY
    }

    private fun startDownload(
        url: String,
        title: String,
        type: String,
        height: Int?,
        audioFormat: String,
        qualityLabel: String
    ) {
        serviceScope.launch {
            isCancelled = false
            val processId = "dl_${System.currentTimeMillis()}"
            currentProcessId = processId

            val tempDir = File(cacheDir, "downloads").apply { mkdirs() }
            val request = YoutubeDLRequest(url)

            if (type == "video") {
                val formatString = if (height != null && height > 0) {
                    "bestvideo[height<=$height]+bestaudio/best[height<=$height]"
                } else {
                    "bestvideo+bestaudio/best"
                }
                request.addOption("-f", formatString)
                request.addOption("--merge-output-format", "mkv")
                request.addOption("-o", "${tempDir.absolutePath}/%(title)s.%(ext)s")
            } else {
                request.addOption("-x")
                request.addOption("--audio-format", audioFormat)
                request.addOption("-o", "${tempDir.absolutePath}/%(title)s.%(ext)s")
            }

            try {
                _downloadProgress.value = DownloadProgress(0f, "Downloading…", "", "", "", true)

                YoutubeDL.getInstance().execute(request, processId) { progress, etaInSeconds, line ->
                    if (isCancelled) return@execute

                    val etaStr = if (etaInSeconds > 0) "${etaInSeconds}s" else ""
                    val notifText = String.format("%.1f%%  ETA: %s", progress, etaStr)
                    updateNotification(title, notifText, progress.toInt())

                    _downloadProgress.value = DownloadProgress(
                        progressPercent = progress,
                        stage = "Downloading…",
                        speed = "",
                        eta = etaStr,
                        totalSize = "",
                        isRunning = true
                    )
                }

                // File completed - export to MediaStore
                val downloadedFiles = tempDir.listFiles() ?: emptyArray()
                if (downloadedFiles.isNotEmpty() && !isCancelled) {
                    val file = downloadedFiles.maxByOrNull { it.lastModified() }
                    if (file != null && file.exists()) {
                        val exportedUri = exportToMediaStore(file, type)
                        val finalPath = exportedUri?.toString() ?: file.absolutePath

                        // Save to History database
                        val db = AppDatabase.getDatabase(applicationContext)
                        db.historyDao().insert(
                            HistoryEntity(
                                title = title,
                                channel = "",
                                durationSeconds = 0,
                                type = type,
                                qualityOrFormat = qualityLabel,
                                filePath = finalPath,
                                originalUrl = url
                            )
                        )
                        file.delete()
                    }
                }

                _downloadProgress.value = DownloadProgress(100f, "Done", "", "", "", false)
                showFinishedNotification(title)
            } catch (e: Exception) {
                if (!isCancelled) {
                    _downloadProgress.value = DownloadProgress(0f, "Failed: ${e.message}", "", "", "", false)
                }
            } finally {
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
            }
        }
    }

    private fun cancelCurrentDownload() {
        isCancelled = true
        currentProcessId?.let { pid ->
            try {
                YoutubeDL.getInstance().destroyProcessById(pid)
            } catch (e: Exception) {
                // Process teardown
            }
        }
        val tempDir = File(cacheDir, "downloads")
        tempDir.deleteRecursively()
        _downloadProgress.value = DownloadProgress(0f, "Cancelled", "", "", "", false)
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    private fun exportToMediaStore(file: File, type: String): Uri? {
        val resolver = contentResolver
        val isVideo = type == "video"
        val collection = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            if (isVideo) MediaStore.Video.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
            else MediaStore.Audio.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
        } else {
            if (isVideo) MediaStore.Video.Media.EXTERNAL_CONTENT_URI
            else MediaStore.Audio.Media.EXTERNAL_CONTENT_URI
        }

        val relativeDir = if (isVideo) "${Environment.DIRECTORY_MOVIES}/YOuTUbE" else "${Environment.DIRECTORY_MUSIC}/YOuTUbE"
        val mimeType = if (isVideo) "video/x-matroska" else "audio/mpeg"

        val values = ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME, file.name)
            put(MediaStore.MediaColumns.MIME_TYPE, mimeType)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                put(MediaStore.MediaColumns.RELATIVE_PATH, relativeDir)
                put(MediaStore.MediaColumns.IS_PENDING, 1)
            }
        }

        val uri = resolver.insert(collection, values) ?: return null
        resolver.openOutputStream(uri)?.use { out ->
            FileInputStream(file).use { input ->
                input.copyTo(out)
            }
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            values.clear()
            values.put(MediaStore.MediaColumns.IS_PENDING, 0)
            resolver.update(uri, values, null, null)
        }

        return uri
    }

    private fun buildNotification(title: String, content: String, progress: Int): Notification {
        val openIntent = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )
        val cancelIntent = PendingIntent.getService(
            this, 1, Intent(this, DownloadService::class.java).apply { action = ACTION_CANCEL },
            PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, YouTubeApp.CHANNEL_DOWNLOAD)
            .setContentTitle(title)
            .setContentText(content)
            .setSmallIcon(R.drawable.ic_launcher)
            .setContentIntent(openIntent)
            .setProgress(100, progress, progress == 0)
            .setOngoing(true)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Cancel", cancelIntent)
            .build()
    }

    private fun updateNotification(title: String, content: String, progress: Int) {
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as android.app.NotificationManager
        manager.notify(NOTIFICATION_ID, buildNotification(title, content, progress))
    }

    private fun showFinishedNotification(title: String) {
        val openIntent = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )
        val notif = NotificationCompat.Builder(this, YouTubeApp.CHANNEL_DOWNLOAD)
            .setContentTitle("Download finished")
            .setContentText(title)
            .setSmallIcon(R.drawable.ic_launcher)
            .setContentIntent(openIntent)
            .setAutoCancel(true)
            .build()
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as android.app.NotificationManager
        manager.notify(NOTIFICATION_ID + 1, notif)
    }

    override fun onDestroy() {
        super.onDestroy()
        serviceScope.cancel()
    }

    companion object {
        const val NOTIFICATION_ID = 1001
        const val ACTION_START_DOWNLOAD = "com.youtube.downloader.START_DOWNLOAD"
        const val ACTION_CANCEL = "com.youtube.downloader.CANCEL"

        const val EXTRA_URL = "extra_url"
        const val EXTRA_TITLE = "extra_title"
        const val EXTRA_TYPE = "extra_type"
        const val EXTRA_HEIGHT = "extra_height"
        const val EXTRA_AUDIO_FORMAT = "extra_audio_format"
        const val EXTRA_QUALITY_LABEL = "extra_quality_label"

        private val _downloadProgress = MutableStateFlow(DownloadProgress())
        val downloadProgress: StateFlow<DownloadProgress> = _downloadProgress.asStateFlow()
    }
}
