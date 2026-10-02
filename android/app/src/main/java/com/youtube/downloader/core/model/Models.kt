package com.youtube.downloader.core.model

import com.youtube.downloader.core.util.UrlTools

data class VideoInfo(
    val id: String,
    val title: String,
    val channel: String,
    val durationSeconds: Long,
    val thumbnailUrl: String,
    val qualities: List<QualityOption> = emptyList(),
    val url: String = ""
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

data class DownloadJob(
    val jobId: String = java.util.UUID.randomUUID().toString(),
    val url: String,
    val videoId: String,
    val title: String,
    val channel: String,
    val durationSeconds: Long,
    val thumbnailUrl: String,
    val kind: DownloadType,
    val qualityLabel: String,
    val height: Int? = null,
    val audioFormat: String = "m4a",
    val createdAt: Long = System.currentTimeMillis()
) {
    fun toQueueItem(): QueueItem {
        return QueueItem(
            id = jobId,
            url = url,
            title = title,
            type = kind,
            qualityLabel = qualityLabel,
            targetHeight = height,
            audioFormat = audioFormat,
            status = QueueStatus.WAITING
        )
    }

    companion object {
        fun create(
            info: VideoInfo,
            kind: DownloadType,
            qualityLabel: String,
            height: Int? = null,
            audioFormat: String = "m4a",
            explicitUrl: String? = null
        ): DownloadJob {
            val rawUrl = explicitUrl ?: info.url
            val cleanedUrl = UrlTools.cleanUrl(rawUrl) ?: rawUrl
            val vid = UrlTools.extractVideoId(cleanedUrl)
                ?: UrlTools.extractVideoId(rawUrl)
                ?: info.id
            val title = info.title.trim()
            if (title.isEmpty() || title == rawUrl || title == cleanedUrl) {
                throw IllegalArgumentException("Invalid job title '$title'. Title must not be empty or equal to the URL.")
            }

            return DownloadJob(
                url = cleanedUrl,
                videoId = vid,
                title = title,
                channel = info.channel,
                durationSeconds = info.durationSeconds,
                thumbnailUrl = info.thumbnailUrl,
                kind = kind,
                qualityLabel = qualityLabel,
                height = height,
                audioFormat = audioFormat
            )
        }
    }
}
