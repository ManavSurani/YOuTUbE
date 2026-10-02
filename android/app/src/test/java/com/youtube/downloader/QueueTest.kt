package com.youtube.downloader

import com.youtube.downloader.core.model.DownloadType
import com.youtube.downloader.core.model.QueueItem
import com.youtube.downloader.core.model.QueueStatus
import org.junit.Assert.*
import org.junit.Test

class QueueTest {

    @Test
    fun testQueueItemStateTransitions() {
        val item = QueueItem(
            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            title = "Test Queue Item",
            type = DownloadType.VIDEO,
            qualityLabel = "1080p"
        )

        assertEquals(QueueStatus.WAITING, item.status)

        // Transition to DOWNLOADING
        item.status = QueueStatus.DOWNLOADING
        assertEquals(QueueStatus.DOWNLOADING, item.status)

        // Transition to DONE
        item.status = QueueStatus.DONE
        assertEquals(QueueStatus.DONE, item.status)
    }

    @Test
    fun testQueueFailureState() {
        val item = QueueItem(
            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            title = "Failing Item",
            type = DownloadType.AUDIO,
            qualityLabel = "MP3"
        )

        item.status = QueueStatus.FAILED
        item.errorMessage = "Video unavailable in your country."

        assertEquals(QueueStatus.FAILED, item.status)
        assertEquals("Video unavailable in your country.", item.errorMessage)
    }

    @Test
    fun testFifoQueueOrdering() {
        val queue = mutableListOf<QueueItem>()
        val item1 = QueueItem(url = "https://youtube.com/watch?v=item1", title = "First", type = DownloadType.VIDEO, qualityLabel = "720p")
        val item2 = QueueItem(url = "https://youtube.com/watch?v=item2", title = "Second", type = DownloadType.VIDEO, qualityLabel = "1080p")
        val item3 = QueueItem(url = "https://youtube.com/watch?v=item3", title = "Third", type = DownloadType.AUDIO, qualityLabel = "MP3")

        queue.add(item1)
        queue.add(item2)
        queue.add(item3)

        assertEquals(3, queue.size)
        // First in, first out
        val nextJob = queue.firstOrNull { it.status == QueueStatus.WAITING }
        assertEquals("First", nextJob?.title)

        nextJob?.status = QueueStatus.DONE
        val secondJob = queue.firstOrNull { it.status == QueueStatus.WAITING }
        assertEquals("Second", secondJob?.title)
    }
}
