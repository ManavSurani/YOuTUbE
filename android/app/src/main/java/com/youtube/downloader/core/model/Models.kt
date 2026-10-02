package com.youtube.downloader.core.model

data class VideoInfo(
    val id: String,
    val title: String,
    val channel: String,
    val durationSeconds: Long,
    val thumbnailUrl: String,
    val qualities: List<QualityOption> = emptyList()
) {
    val formattedDuration: String
        get() {
            if (durationSeconds <= 0) return ""
            val h = durationSeconds / 3600
            val m = (durationSeconds % 3600) / 60
            val s = durationSeconds % 60
            return if (h > 0) String.format("%d:%02d:%02d", h, m, s)
            else String.format("%d:%02d", m, s)
        }
}

data class QualityOption(
    val label: String,
    val height: Int?
)

data class DownloadProgress(
    val progressPercent: Float = 0f,
    val stage: String = "",
    val speed: String = "",
    val eta: String = "",
    val totalSize: String = "",
    val isRunning: Boolean = false
)

enum class DownloadType {
    VIDEO, AUDIO
}

data class QueueItem(
    val id: String = java.util.UUID.randomUUID().toString(),
    val url: String,
    val title: String,
    val type: DownloadType,
    val qualityLabel: String,
    val targetHeight: Int? = null,
    val audioFormat: String = "m4a",
    var status: QueueStatus = QueueStatus.WAITING,
    var errorMessage: String = ""
)

enum class QueueStatus {
    WAITING, DOWNLOADING, DONE, FAILED, CANCELLED
}
