package com.youtube.downloader

import com.youtube.downloader.core.database.HistoryEntity
import org.junit.Assert.*
import org.junit.Test

class HistoryModelTest {

    @Test
    fun testHistoryEntityConstruction() {
        val entity = HistoryEntity(
            id = 1L,
            title = "Video Title",
            channel = "Channel Name",
            durationSeconds = 300,
            type = "video",
            qualityOrFormat = "1080p (FHD)",
            filePath = "/storage/emulated/0/Movies/YOuTUbE/video.mkv",
            originalUrl = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )

        assertEquals(1L, entity.id)
        assertEquals("Video Title", entity.title)
        assertEquals("video", entity.type)
        assertEquals("1080p (FHD)", entity.qualityOrFormat)
        assertTrue(entity.timestamp > 0)
    }

    @Test
    fun testAudioHistoryEntity() {
        val entity = HistoryEntity(
            id = 2L,
            title = "Audio Track",
            channel = "Artist",
            durationSeconds = 180,
            type = "audio",
            qualityOrFormat = "MP3",
            filePath = "/storage/emulated/0/Music/YOuTUbE/audio.mp3",
            originalUrl = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )

        assertEquals("audio", entity.type)
        assertEquals("MP3", entity.qualityOrFormat)
    }
}
