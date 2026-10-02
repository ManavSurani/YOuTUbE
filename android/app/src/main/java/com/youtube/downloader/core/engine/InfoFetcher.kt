package com.youtube.downloader.core.engine

import com.yausername.youtubedl_android.YoutubeDL
import com.yausername.youtubedl_android.mapper.VideoInfo as YtdlVideoInfo
import com.youtube.downloader.core.model.QualityOption
import com.youtube.downloader.core.model.VideoInfo
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

object InfoFetcher {

    suspend fun fetchInfo(url: String): Result<VideoInfo> = withContext(Dispatchers.IO) {
        try {
            val ytdlInfo: YtdlVideoInfo = YoutubeDL.getInstance().getInfo(url)

            val formats = ytdlInfo.formats ?: emptyList()
            val videoHeights = formats
                .mapNotNull { it.height }
                .filter { it > 0 }
                .distinct()
                .sortedDescending()

            val qualityList = mutableListOf<QualityOption>()
            qualityList.add(
                QualityOption(
                    label = if (videoHeights.isNotEmpty()) "Best available (${labelForHeight(videoHeights[0])})" else "Best available",
                    height = null
                )
            )

            for (h in videoHeights) {
                qualityList.add(QualityOption(label = labelForHeight(h), height = h))
            }

            val info = VideoInfo(
                id = ytdlInfo.id ?: "",
                title = ytdlInfo.title ?: "Unknown Video",
                channel = ytdlInfo.uploader ?: "",
                durationSeconds = ytdlInfo.duration.toLong(),
                thumbnailUrl = ytdlInfo.thumbnail ?: "",
                qualities = qualityList,
                url = url
            )

            Result.success(info)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    private fun labelForHeight(height: Int): String {
        return when {
            height >= 4320 -> "8K (${height}p)"
            height >= 2160 -> "4K (${height}p)"
            height >= 1440 -> "2K (${height}p)"
            height >= 1080 -> "1080p (FHD)"
            height >= 720 -> "720p (HD)"
            height >= 480 -> "480p (SD)"
            height >= 360 -> "360p"
            height >= 240 -> "240p"
            height >= 144 -> "144p"
            else -> "${height}p"
        }
    }
}
