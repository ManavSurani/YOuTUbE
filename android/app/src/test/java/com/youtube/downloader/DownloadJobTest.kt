package com.youtube.downloader

import com.youtube.downloader.core.model.*
import org.junit.Assert.*
import org.junit.Test

class DownloadJobTest {

    @Test
    fun testValidJobSnapshotCreation() {
        val info = VideoInfo(
            id = "dQw4w9WgXcQ",
            title = "Sample Video Title",
            channel = "Official Channel",
            durationSeconds = 212,
            thumbnailUrl = "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )

        val job = DownloadJob.create(
            info = info,
            kind = DownloadType.VIDEO,
            qualityLabel = "1080p (FHD)",
            height = 1080
        )

        assertEquals("Sample Video Title", job.title)
        assertEquals("dQw4w9WgXcQ", job.videoId)
        assertEquals("Official Channel", job.channel)
        assertEquals(212L, job.durationSeconds)
        assertEquals(DownloadType.VIDEO, job.kind)
        assertEquals("1080p (FHD)", job.qualityLabel)
        assertEquals(1080, job.height)
        assertNotNull(job.jobId)
        assertTrue(job.createdAt > 0)
    }

    @Test(expected = IllegalArgumentException::class)
    fun testJobRejectsEmptyTitle() {
        val info = VideoInfo(
            id = "dQw4w9WgXcQ",
            title = "   ",
            channel = "Channel",
            durationSeconds = 100,
            thumbnailUrl = "",
            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        DownloadJob.create(info, DownloadType.VIDEO, "Best available")
    }

    @Test(expected = IllegalArgumentException::class)
    fun testJobRejectsTitleEqualToUrl() {
        val url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        val info = VideoInfo(
            id = "dQw4w9WgXcQ",
            title = url,
            channel = "Channel",
            durationSeconds = 100,
            thumbnailUrl = "",
            url = url
        )
        DownloadJob.create(info, DownloadType.VIDEO, "Best available")
    }

    @Test
    fun testConvertToQueueItem() {
        val info = VideoInfo(
            id = "dQw4w9WgXcQ",
            title = "Song Title",
            channel = "Artist",
            durationSeconds = 180,
            thumbnailUrl = "thumb.jpg",
            url = "https://youtu.be/dQw4w9WgXcQ"
        )
        val job = DownloadJob.create(
            info = info,
            kind = DownloadType.AUDIO,
            qualityLabel = "MP3",
            audioFormat = "mp3"
        )
        val queueItem = job.toQueueItem()

        assertEquals(job.jobId, queueItem.id)
        assertEquals("Song Title", queueItem.title)
        assertEquals(DownloadType.AUDIO, queueItem.type)
        assertEquals("mp3", queueItem.audioFormat)
        assertEquals(QueueStatus.WAITING, queueItem.status)
    }
}
