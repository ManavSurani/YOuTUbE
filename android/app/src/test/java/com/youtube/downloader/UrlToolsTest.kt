package com.youtube.downloader

import com.youtube.downloader.core.util.UrlTools
import org.junit.Assert.*
import org.junit.Test

class UrlToolsTest {

    @Test
    fun testStandardWatchUrl() {
        val url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assertTrue(UrlTools.isYouTubeUrl(url))
        assertEquals("dQw4w9WgXcQ", UrlTools.extractVideoId(url))
        assertEquals("https://www.youtube.com/watch?v=dQw4w9WgXcQ", UrlTools.cleanUrl(url))
    }

    @Test
    fun testShortsUrl() {
        val url = "https://youtube.com/shorts/dQw4w9WgXcQ"
        assertTrue(UrlTools.isYouTubeUrl(url))
        assertEquals("dQw4w9WgXcQ", UrlTools.extractVideoId(url))
        assertEquals("https://www.youtube.com/watch?v=dQw4w9WgXcQ", UrlTools.cleanUrl(url))
    }

    @Test
    fun testEmbedUrl() {
        val url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        assertTrue(UrlTools.isYouTubeUrl(url))
        assertEquals("dQw4w9WgXcQ", UrlTools.extractVideoId(url))
        assertEquals("https://www.youtube.com/watch?v=dQw4w9WgXcQ", UrlTools.cleanUrl(url))
    }

    @Test
    fun testLiveUrl() {
        val url = "https://www.youtube.com/live/dQw4w9WgXcQ"
        assertTrue(UrlTools.isYouTubeUrl(url))
        assertEquals("dQw4w9WgXcQ", UrlTools.extractVideoId(url))
        assertEquals("https://www.youtube.com/watch?v=dQw4w9WgXcQ", UrlTools.cleanUrl(url))
    }

    @Test
    fun testShortDomainUrl() {
        val url = "https://youtu.be/dQw4w9WgXcQ"
        assertTrue(UrlTools.isYouTubeUrl(url))
        assertEquals("dQw4w9WgXcQ", UrlTools.extractVideoId(url))
        assertEquals("https://www.youtube.com/watch?v=dQw4w9WgXcQ", UrlTools.cleanUrl(url))
    }

    @Test
    fun testTrackingParametersStripped() {
        val url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL123456789&t=120s&feature=share"
        assertTrue(UrlTools.isYouTubeUrl(url))
        assertEquals("dQw4w9WgXcQ", UrlTools.extractVideoId(url))
        assertEquals("https://www.youtube.com/watch?v=dQw4w9WgXcQ", UrlTools.cleanUrl(url))
    }

    @Test
    fun testInvalidUrls() {
        assertFalse(UrlTools.isYouTubeUrl("https://google.com"))
        assertFalse(UrlTools.isYouTubeUrl("https://youtube.com/about"))
        assertFalse(UrlTools.isYouTubeUrl(""))
        assertFalse(UrlTools.isYouTubeUrl("not a url"))
        assertNull(UrlTools.cleanUrl("https://google.com"))
        assertNull(UrlTools.cleanUrl(""))
    }
}
