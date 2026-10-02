package com.youtube.downloader.ui.screens

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.material3.TabRowDefaults.tabIndicatorOffset
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.youtube.downloader.core.database.AppDatabase
import com.youtube.downloader.core.database.HistoryEntity
import com.youtube.downloader.core.engine.InfoFetcher
import com.youtube.downloader.core.model.DownloadType
import com.youtube.downloader.core.model.QualityOption
import com.youtube.downloader.core.model.QueueItem
import com.youtube.downloader.core.model.QueueStatus
import com.youtube.downloader.core.model.VideoInfo
import com.youtube.downloader.core.network.NetworkMonitor
import com.youtube.downloader.core.service.DownloadService
import com.youtube.downloader.core.util.UrlTools
import com.youtube.downloader.ui.components.MediaInfoCard
import com.youtube.downloader.ui.theme.*
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    initialSharedUrl: String? = null,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val networkMonitor = remember { NetworkMonitor(context) }
    val isOnline by networkMonitor.isOnline.collectAsStateWithLifecycle()
    val progress by DownloadService.downloadProgress.collectAsStateWithLifecycle()

    var selectedTabIndex by remember { mutableIntStateOf(0) }
    val tabs = listOf("Video", "Audio", "History")

    // Video Tab state
    var videoUrl by remember { mutableStateOf(initialSharedUrl ?: "") }
    var videoInfo by remember { mutableStateOf<VideoInfo?>(null) }
    var isFetchingVideo by remember { mutableStateOf(false) }
    var selectedQuality by remember { mutableStateOf<QualityOption?>(null) }
    var videoQueue by remember { mutableStateOf(listOf<QueueItem>()) }

    // Audio Tab state
    var audioUrl by remember { mutableStateOf("") }
    var audioInfo by remember { mutableStateOf<VideoInfo?>(null) }
    var isFetchingAudio by remember { mutableStateOf(false) }
    var selectedAudioFormat by remember { mutableStateOf("mp3") }

    // Show settings dialog
    var showSettings by remember { mutableStateOf(false) }

    // Auto-fetch shared URL on launch
    LaunchedEffect(initialSharedUrl) {
        if (!initialSharedUrl.isNullOrEmpty()) {
            val cleaned = UrlTools.cleanUrl(initialSharedUrl)
            if (cleaned != null) {
                videoUrl = cleaned
                isFetchingVideo = true
                val result = InfoFetcher.fetchInfo(cleaned)
                isFetchingVideo = false
                result.onSuccess {
                    videoInfo = it
                    selectedQuality = it.qualities.firstOrNull()
                }
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Box(
                            modifier = Modifier
                                .size(24.dp)
                                .clip(RoundedCornerShape(6.dp))
                                .background(BrandRed),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = Icons.Default.ArrowDownward,
                                contentDescription = null,
                                tint = Color.White,
                                modifier = Modifier.size(16.dp)
                            )
                        }
                        Text(
                            text = "YOuTUbE",
                            fontWeight = FontWeight.Bold,
                            fontSize = 18.sp,
                            color = TextPrimaryDark
                        )
                    }
                },
                actions = {
                    // Online / Offline live dot
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        modifier = Modifier.padding(end = 12.dp)
                    ) {
                        Box(
                            modifier = Modifier
                                .size(8.dp)
                                .clip(CircleShape)
                                .background(if (isOnline) StatusGreen else StatusRed)
                        )
                        Text(
                            text = if (isOnline) "Online" else "Offline",
                            fontSize = 12.sp,
                            color = TextSecondaryDark
                        )
                    }
                    IconButton(onClick = { showSettings = true }) {
                        Icon(
                            imageVector = Icons.Default.Settings,
                            contentDescription = "Settings",
                            tint = TextSecondaryDark
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = BgDark)
            )
        },
        containerColor = BgDark
    ) { innerPadding ->
        Column(
            modifier = modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            // Tabs Row
            TabRow(
                selectedTabIndex = selectedTabIndex,
                containerColor = BgDark,
                contentColor = TextPrimaryDark,
                indicator = { tabPositions ->
                    TabRowDefaults.SecondaryIndicator(
                        Modifier.tabIndicatorOffset(tabPositions[selectedTabIndex]),
                        color = BrandRed,
                        height = 2.dp
                    )
                }
            ) {
                tabs.forEachIndexed { index, title ->
                    Tab(
                        selected = selectedTabIndex == index,
                        onClick = { selectedTabIndex = index },
                        text = {
                            Text(
                                text = title,
                                fontSize = 14.sp,
                                fontWeight = if (selectedTabIndex == index) FontWeight.SemiBold else FontWeight.Normal,
                                color = if (selectedTabIndex == index) TextPrimaryDark else TextSecondaryDark
                            )
                        }
                    )
                }
            }

            // Offline alert banner
            if (!isOnline) {
                Surface(
                    color = SurfaceDark,
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
                    shape = RoundedCornerShape(6.dp)
                ) {
                    Text(
                        text = "Internet is off. You can still view your history.",
                        color = TextSecondaryDark,
                        fontSize = 12.sp,
                        modifier = Modifier.padding(10.dp)
                    )
                }
            }

            // Main Content Area
            Box(modifier = Modifier.fillMaxSize().padding(16.dp)) {
                when (selectedTabIndex) {
                    0 -> VideoTabContent(
                        url = videoUrl,
                        onUrlChange = { videoUrl = it },
                        info = videoInfo,
                        isFetching = isFetchingVideo,
                        isOnline = isOnline,
                        selectedQuality = selectedQuality,
                        onQualitySelect = { selectedQuality = it },
                        progress = progress,
                        queue = videoQueue,
                        onFetch = {
                            val cleaned = UrlTools.cleanUrl(videoUrl)
                            if (cleaned == null) {
                                Toast.makeText(context, "Please paste a valid YouTube link", Toast.LENGTH_SHORT).show()
                                return@VideoTabContent
                            }
                            isFetchingVideo = true
                            scope.launch {
                                val res = InfoFetcher.fetchInfo(cleaned)
                                isFetchingVideo = false
                                res.onSuccess {
                                    videoInfo = it
                                    selectedQuality = it.qualities.firstOrNull()
                                }.onFailure {
                                    Toast.makeText(context, "Fetch failed: ${it.message}", Toast.LENGTH_SHORT).show()
                                }
                            }
                        },
                        onDownload = {
                            val cleaned = UrlTools.cleanUrl(videoUrl) ?: return@VideoTabContent
                            val intent = Intent(context, DownloadService::class.java).apply {
                                action = DownloadService.ACTION_START_DOWNLOAD
                                putExtra(DownloadService.EXTRA_URL, cleaned)
                                putExtra(DownloadService.EXTRA_TITLE, videoInfo?.title ?: "Video")
                                putExtra(DownloadService.EXTRA_TYPE, "video")
                                putExtra(DownloadService.EXTRA_HEIGHT, selectedQuality?.height ?: 0)
                                putExtra(DownloadService.EXTRA_QUALITY_LABEL, selectedQuality?.label ?: "Best")
                            }
                            context.startService(intent)
                        },
                        onAddToQueue = {
                            val cleaned = UrlTools.cleanUrl(videoUrl) ?: return@VideoTabContent
                            val item = QueueItem(
                                url = cleaned,
                                title = videoInfo?.title ?: cleaned,
                                type = DownloadType.VIDEO,
                                qualityLabel = selectedQuality?.label ?: "Best",
                                targetHeight = selectedQuality?.height
                            )
                            videoQueue = videoQueue + item
                            videoUrl = ""
                            videoInfo = null
                        },
                        onCancel = {
                            val intent = Intent(context, DownloadService::class.java).apply {
                                action = DownloadService.ACTION_CANCEL
                            }
                            context.startService(intent)
                        },
                        onRemoveQueueItem = { itm ->
                            videoQueue = videoQueue.filter { it.id != itm.id }
                        }
                    )
                    1 -> AudioTabContent(
                        url = audioUrl,
                        onUrlChange = { audioUrl = it },
                        info = audioInfo,
                        isFetching = isFetchingAudio,
                        isOnline = isOnline,
                        selectedFormat = selectedAudioFormat,
                        onFormatSelect = { selectedAudioFormat = it },
                        progress = progress,
                        onFetch = {
                            val cleaned = UrlTools.cleanUrl(audioUrl)
                            if (cleaned == null) {
                                Toast.makeText(context, "Please paste a valid YouTube link", Toast.LENGTH_SHORT).show()
                                return@AudioTabContent
                            }
                            isFetchingAudio = true
                            scope.launch {
                                val res = InfoFetcher.fetchInfo(cleaned)
                                isFetchingAudio = false
                                res.onSuccess { audioInfo = it }
                                    .onFailure { Toast.makeText(context, "Fetch failed: ${it.message}", Toast.LENGTH_SHORT).show() }
                            }
                        },
                        onDownload = {
                            val cleaned = UrlTools.cleanUrl(audioUrl) ?: return@AudioTabContent
                            val intent = Intent(context, DownloadService::class.java).apply {
                                action = DownloadService.ACTION_START_DOWNLOAD
                                putExtra(DownloadService.EXTRA_URL, cleaned)
                                putExtra(DownloadService.EXTRA_TITLE, audioInfo?.title ?: "Audio")
                                putExtra(DownloadService.EXTRA_TYPE, "audio")
                                putExtra(DownloadService.EXTRA_AUDIO_FORMAT, selectedAudioFormat)
                                putExtra(DownloadService.EXTRA_QUALITY_LABEL, selectedAudioFormat.uppercase())
                            }
                            context.startService(intent)
                        },
                        onCancel = {
                            val intent = Intent(context, DownloadService::class.java).apply {
                                action = DownloadService.ACTION_CANCEL
                            }
                            context.startService(intent)
                        }
                    )
                    2 -> HistoryTabContent(
                        onRedownload = { item ->
                            if (item.type == "video") {
                                videoUrl = item.originalUrl
                                selectedTabIndex = 0
                            } else {
                                audioUrl = item.originalUrl
                                selectedTabIndex = 1
                            }
                        }
                    )
                }
            }
        }
    }

    if (showSettings) {
        SettingsDialog(onDismiss = { showSettings = false })
    }
}

@Composable
fun VideoTabContent(
    url: String,
    onUrlChange: (String) -> Unit,
    info: VideoInfo?,
    isFetching: Boolean,
    isOnline: Boolean,
    selectedQuality: QualityOption?,
    onQualitySelect: (QualityOption) -> Unit,
    progress: com.youtube.downloader.core.model.DownloadProgress,
    queue: List<QueueItem>,
    onFetch: () -> Unit,
    onDownload: () -> Unit,
    onAddToQueue: () -> Unit,
    onCancel: () -> Unit,
    onRemoveQueueItem: (QueueItem) -> Unit
) {
    var expandedQualityDropdown by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        // Link Input Row
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            OutlinedTextField(
                value = url,
                onValueChange = onUrlChange,
                modifier = Modifier.weight(1f),
                placeholder = { Text("Paste a YouTube link", color = TextSecondaryDark, fontSize = 13.sp) },
                singleLine = true,
                enabled = isOnline,
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = AccentBlue,
                    unfocusedBorderColor = BorderDark,
                    focusedTextColor = TextPrimaryDark,
                    unfocusedTextColor = TextPrimaryDark,
                    focusedContainerColor = SurfaceDark,
                    unfocusedContainerColor = SurfaceDark
                ),
                shape = RoundedCornerShape(8.dp)
            )

            Button(
                onClick = onFetch,
                enabled = isOnline && url.isNotEmpty() && !isFetching,
                colors = ButtonDefaults.buttonColors(containerColor = SurfaceHighlightDark),
                shape = RoundedCornerShape(8.dp)
            ) {
                if (isFetching) {
                    CircularProgressIndicator(modifier = Modifier.size(16.dp), color = TextPrimaryDark, strokeWidth = 2.dp)
                } else {
                    Text("Fetch", color = TextPrimaryDark)
                }
            }
        }

        // Thumbnail & Metadata Card
        MediaInfoCard(info = info)

        // Actions: Quality dropdown, Download button, Add to queue, Cancel
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box {
                OutlinedButton(
                    onClick = { expandedQualityDropdown = true },
                    enabled = isOnline && info != null,
                    colors = ButtonDefaults.outlinedButtonColors(containerColor = SurfaceDark),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text(
                        text = selectedQuality?.label ?: "Best available",
                        color = TextPrimaryDark,
                        fontSize = 12.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }

                DropdownMenu(
                    expanded = expandedQualityDropdown,
                    onDismissRequest = { expandedQualityDropdown = false },
                    modifier = Modifier.background(SurfaceDark)
                ) {
                    info?.qualities?.forEach { q ->
                        DropdownMenuItem(
                            text = { Text(q.label, color = TextPrimaryDark, fontSize = 12.sp) },
                            onClick = {
                                onQualitySelect(q)
                                expandedQualityDropdown = false
                            }
                        )
                    }
                }
            }

            Button(
                onClick = onDownload,
                enabled = isOnline && info != null && !progress.isRunning,
                colors = ButtonDefaults.buttonColors(containerColor = BrandRed),
                shape = RoundedCornerShape(8.dp)
            ) {
                Text("Download", color = Color.White, fontWeight = FontWeight.Bold)
            }

            Button(
                onClick = onAddToQueue,
                enabled = isOnline && info != null && !progress.isRunning,
                colors = ButtonDefaults.buttonColors(containerColor = SurfaceHighlightDark),
                shape = RoundedCornerShape(8.dp)
            ) {
                Text("Queue", color = TextPrimaryDark)
            }

            if (progress.isRunning) {
                OutlinedButton(
                    onClick = onCancel,
                    colors = ButtonDefaults.outlinedButtonColors(containerColor = SurfaceDark),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text("Cancel", color = TextSecondaryDark)
                }
            }
        }

        // Live Progress Display
        if (progress.isRunning) {
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text(
                    text = "${progress.stage}  ${progress.eta}",
                    color = TextSecondaryDark,
                    fontSize = 11.sp
                )
                LinearProgressIndicator(
                    progress = { progress.progressPercent / 100f },
                    modifier = Modifier.fillMaxWidth().height(6.dp).clip(RoundedCornerShape(3.dp)),
                    color = BrandRed,
                    trackColor = BorderDark
                )
                Text(
                    text = "${progress.progressPercent.toInt()}%",
                    color = TextSecondaryDark,
                    fontSize = 11.sp,
                    modifier = Modifier.align(Alignment.End)
                )
            }
        }

        // Queue List
        if (queue.isNotEmpty()) {
            Text("Queue (${queue.size} waiting)", color = TextSecondaryDark, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
            LazyColumn(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                items(queue) { item ->
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(6.dp))
                            .background(SurfaceDark)
                            .padding(horizontal = 10.dp, vertical = 6.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "${item.title} (${item.qualityLabel})",
                            color = TextPrimaryDark,
                            fontSize = 12.sp,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier.weight(1f)
                        )
                        IconButton(onClick = { onRemoveQueueItem(item) }, modifier = Modifier.size(24.dp)) {
                            Icon(Icons.Default.Close, contentDescription = "Remove", tint = TextSecondaryDark, modifier = Modifier.size(14.dp))
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun AudioTabContent(
    url: String,
    onUrlChange: (String) -> Unit,
    info: VideoInfo?,
    isFetching: Boolean,
    isOnline: Boolean,
    selectedFormat: String,
    onFormatSelect: (String) -> Unit,
    progress: com.youtube.downloader.core.model.DownloadProgress,
    onFetch: () -> Unit,
    onDownload: () -> Unit,
    onCancel: () -> Unit
) {
    val formats = listOf("mp3", "m4a", "opus", "wav", "flac")
    var expandedFormatDropdown by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            OutlinedTextField(
                value = url,
                onValueChange = onUrlChange,
                modifier = Modifier.weight(1f),
                placeholder = { Text("Paste a YouTube link", color = TextSecondaryDark, fontSize = 13.sp) },
                singleLine = true,
                enabled = isOnline,
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = AccentBlue,
                    unfocusedBorderColor = BorderDark,
                    focusedTextColor = TextPrimaryDark,
                    unfocusedTextColor = TextPrimaryDark,
                    focusedContainerColor = SurfaceDark,
                    unfocusedContainerColor = SurfaceDark
                ),
                shape = RoundedCornerShape(8.dp)
            )

            Button(
                onClick = onFetch,
                enabled = isOnline && url.isNotEmpty() && !isFetching,
                colors = ButtonDefaults.buttonColors(containerColor = SurfaceHighlightDark),
                shape = RoundedCornerShape(8.dp)
            ) {
                Text("Fetch", color = TextPrimaryDark)
            }
        }

        MediaInfoCard(info = info)

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box {
                OutlinedButton(
                    onClick = { expandedFormatDropdown = true },
                    enabled = isOnline && info != null,
                    colors = ButtonDefaults.outlinedButtonColors(containerColor = SurfaceDark),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text(selectedFormat.uppercase(), color = TextPrimaryDark, fontSize = 12.sp)
                }

                DropdownMenu(
                    expanded = expandedFormatDropdown,
                    onDismissRequest = { expandedFormatDropdown = false },
                    modifier = Modifier.background(SurfaceDark)
                ) {
                    formats.forEach { fmt ->
                        DropdownMenuItem(
                            text = { Text(fmt.uppercase(), color = TextPrimaryDark) },
                            onClick = {
                                onFormatSelect(fmt)
                                expandedFormatDropdown = false
                            }
                        )
                    }
                }
            }

            Button(
                onClick = onDownload,
                enabled = isOnline && info != null && !progress.isRunning,
                colors = ButtonDefaults.buttonColors(containerColor = BrandRed),
                shape = RoundedCornerShape(8.dp)
            ) {
                Text("Download Audio", color = Color.White, fontWeight = FontWeight.Bold)
            }

            if (progress.isRunning) {
                OutlinedButton(
                    onClick = onCancel,
                    colors = ButtonDefaults.outlinedButtonColors(containerColor = SurfaceDark),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text("Cancel", color = TextSecondaryDark)
                }
            }
        }

        if (progress.isRunning) {
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                LinearProgressIndicator(
                    progress = { progress.progressPercent / 100f },
                    modifier = Modifier.fillMaxWidth().height(6.dp).clip(RoundedCornerShape(3.dp)),
                    color = BrandRed,
                    trackColor = BorderDark
                )
            }
        }
    }
}

@Composable
fun HistoryTabContent(
    onRedownload: (HistoryEntity) -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val db = remember { AppDatabase.getDatabase(context) }
    var selectedFilter by remember { mutableStateOf("all") }
    var searchQuery by remember { mutableStateOf("") }

    val rawHistory by db.historyDao().getAllHistory().collectAsStateWithLifecycle(initialValue = emptyList())

    val filteredList = rawHistory.filter { item ->
        val matchesFilter = when (selectedFilter) {
            "video" -> item.type == "video"
            "audio" -> item.type == "audio"
            else -> true
        }
        val matchesSearch = searchQuery.isEmpty() || item.title.contains(searchQuery, ignoreCase = true)
        matchesFilter && matchesSearch
    }

    Column(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        // Search field
        OutlinedTextField(
            value = searchQuery,
            onValueChange = { searchQuery = it },
            modifier = Modifier.fillMaxWidth(),
            placeholder = { Text("Search history…", color = TextSecondaryDark, fontSize = 13.sp) },
            leadingIcon = { Icon(Icons.Default.Search, contentDescription = null, tint = TextSecondaryDark) },
            singleLine = true,
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = AccentBlue,
                unfocusedBorderColor = BorderDark,
                focusedTextColor = TextPrimaryDark,
                unfocusedTextColor = TextPrimaryDark,
                focusedContainerColor = SurfaceDark,
                unfocusedContainerColor = SurfaceDark
            ),
            shape = RoundedCornerShape(8.dp)
        )

        // Filter chips: All, Video, Audio
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf("all" to "All", "video" to "Video", "audio" to "Audio").forEach { (key, label) ->
                FilterChip(
                    selected = selectedFilter == key,
                    onClick = { selectedFilter = key },
                    label = { Text(label, fontSize = 12.sp) },
                    colors = FilterChipDefaults.filterChipColors(
                        selectedContainerColor = SurfaceHighlightDark,
                        selectedLabelColor = TextPrimaryDark,
                        containerColor = SurfaceDark,
                        labelColor = TextSecondaryDark
                    ),
                    shape = RoundedCornerShape(16.dp)
                )
            }
        }

        // History items list
        if (filteredList.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("Nothing here yet.", color = TextSecondaryDark, fontSize = 14.sp)
            }
        } else {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items(filteredList, key = { it.id }) { item ->
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(8.dp))
                            .background(SurfaceDark)
                            .clickable {
                                // Play with system media player
                                try {
                                    val uri = Uri.parse(item.filePath)
                                    val intent = Intent(Intent.ACTION_VIEW).apply {
                                        setDataAndType(uri, if (item.type == "video") "video/*" else "audio/*")
                                        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                                    }
                                    context.startActivity(intent)
                                } catch (e: Exception) {
                                    Toast.makeText(context, "Could not open file", Toast.LENGTH_SHORT).show()
                                }
                            }
                            .padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        Icon(
                            imageVector = if (item.type == "video") Icons.Default.Videocam else Icons.Default.MusicNote,
                            contentDescription = null,
                            tint = BrandRed,
                            modifier = Modifier.size(24.dp)
                        )

                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = item.title,
                                color = TextPrimaryDark,
                                fontSize = 13.sp,
                                fontWeight = FontWeight.Medium,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis
                            )
                            Text(
                                text = item.qualityOrFormat,
                                color = TextSecondaryDark,
                                fontSize = 11.sp
                            )
                        }

                        IconButton(onClick = { onRedownload(item) }, modifier = Modifier.size(28.dp)) {
                            Icon(Icons.Default.Refresh, contentDescription = "Re-download", tint = TextSecondaryDark, modifier = Modifier.size(16.dp))
                        }

                        IconButton(onClick = {
                            scope.launch { db.historyDao().delete(item) }
                        }, modifier = Modifier.size(28.dp)) {
                            Icon(Icons.Default.Delete, contentDescription = "Delete", tint = TextSecondaryDark, modifier = Modifier.size(16.dp))
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun SettingsDialog(onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("About YOuTUbE", color = TextPrimaryDark, fontWeight = FontWeight.Bold) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Version 1.0.1 (Android)", color = TextSecondaryDark, fontSize = 13.sp)
                HorizontalDivider(color = BorderDark)
                Text("Built with open-source tools:", color = TextSecondaryDark, fontSize = 12.sp)
                Text("• yt-dlp & youtubedl-android", color = TextSecondaryDark, fontSize = 11.sp)
                Text("• FFmpeg & FFprobe", color = TextSecondaryDark, fontSize = 11.sp)
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) {
                Text("Close", color = BrandRed)
            }
        },
        containerColor = SurfaceDark,
        shape = RoundedCornerShape(12.dp)
    )
}
