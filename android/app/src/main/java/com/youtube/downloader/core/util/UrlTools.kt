package com.youtube.downloader.core.util

import java.net.URI
import java.util.regex.Pattern

object UrlTools {
    private val VIDEO_ID_REGEX = Pattern.compile("^[a-zA-Z0-9_-]{11}$")

    fun isYouTubeUrl(url: String): Boolean {
        val trimmed = url.trim()
        if (trimmed.isEmpty()) return false
        val lower = trimmed.lowercase()
        return lower.contains("youtube.com") || lower.contains("youtu.be")
    }

    fun cleanUrl(rawUrl: String): String? {
        val trimmed = rawUrl.trim()
        if (!isYouTubeUrl(trimmed)) return null

        try {
            val uri = URI(if (!trimmed.startsWith("http://") && !trimmed.startsWith("https://")) "https://$trimmed" else trimmed)
            val host = uri.host?.lowercase() ?: return null
            val path = uri.path ?: ""
            val query = uri.query ?: ""

            var videoId: String? = null

            // youtu.be/<id>
            if (host.contains("youtu.be")) {
                val parts = path.split("/").filter { it.isNotEmpty() }
                if (parts.isNotEmpty()) videoId = parts[0]
            }
            // youtube.com/shorts/<id>
            else if (path.startsWith("/shorts/")) {
                val parts = path.removePrefix("/shorts/").split("/").filter { it.isNotEmpty() }
                if (parts.isNotEmpty()) videoId = parts[0]
            }
            // youtube.com/watch?v=<id>
            else if (path.startsWith("/watch")) {
                val params = query.split("&")
                for (p in params) {
                    val kv = p.split("=")
                    if (kv.size == 2 && kv[0] == "v") {
                        videoId = kv[1]
                        break
                    }
                }
            }

            if (videoId != null && VIDEO_ID_REGEX.matcher(videoId).matches()) {
                return "https://www.youtube.com/watch?v=$videoId"
            }
        } catch (e: Exception) {
            return null
        }
        return null
    }
}
