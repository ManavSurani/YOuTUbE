package com.youtube.downloader.core.util

import java.net.URI
import java.util.regex.Pattern

object UrlTools {
    private val VIDEO_ID_REGEX = Pattern.compile("^[a-zA-Z0-9_-]{11}$")

    fun extractVideoId(rawUrl: String): String? {
        val trimmed = rawUrl.trim()
        if (trimmed.isEmpty()) return null

        val fullUrl = if (!trimmed.startsWith("http://", ignoreCase = true) && !trimmed.startsWith("https://", ignoreCase = true)) {
            "https://$trimmed"
        } else {
            trimmed
        }

        return try {
            val uri = URI(fullUrl)
            var host = uri.host?.lowercase() ?: return null
            if (host.startsWith("www.")) {
                host = host.removePrefix("www.")
            }

            val path = uri.path ?: ""
            val query = uri.query ?: ""

            when {
                host == "youtube.com" || host == "m.youtube.com" -> {
                    when {
                        path.startsWith("/watch") -> {
                            val params = query.split("&")
                            var vid: String? = null
                            for (p in params) {
                                val kv = p.split("=")
                                if (kv.size == 2 && kv[0] == "v") {
                                    vid = kv[1]
                                    break
                                }
                            }
                            if (vid != null && VIDEO_ID_REGEX.matcher(vid).matches()) vid else null
                        }
                        path.startsWith("/shorts/") -> {
                            val parts = path.split("/").filter { it.isNotEmpty() }
                            if (parts.size >= 2 && VIDEO_ID_REGEX.matcher(parts[1]).matches()) parts[1] else null
                        }
                        path.startsWith("/embed/") -> {
                            val parts = path.split("/").filter { it.isNotEmpty() }
                            if (parts.size >= 2 && VIDEO_ID_REGEX.matcher(parts[1]).matches()) parts[1] else null
                        }
                        path.startsWith("/live/") -> {
                            val parts = path.split("/").filter { it.isNotEmpty() }
                            if (parts.size >= 2 && VIDEO_ID_REGEX.matcher(parts[1]).matches()) parts[1] else null
                        }
                        else -> null
                    }
                }
                host == "youtu.be" -> {
                    val pathClean = path.trimStart('/')
                    val firstSegment = pathClean.split("/").firstOrNull() ?: ""
                    if (VIDEO_ID_REGEX.matcher(firstSegment).matches()) firstSegment else null
                }
                else -> null
            }
        } catch (e: Exception) {
            null
        }
    }

    fun isYouTubeUrl(url: String): Boolean {
        return extractVideoId(url) != null
    }

    fun cleanUrl(rawUrl: String): String? {
        val vid = extractVideoId(rawUrl) ?: return null
        return "https://www.youtube.com/watch?v=$vid"
    }
}
