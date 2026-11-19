package com.krbavcic.logosphere.ui.inbox

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.krbavcic.logosphere.AppContainer
import com.krbavcic.logosphere.core.logic.Dates
import com.krbavcic.logosphere.core.logic.Links
import com.krbavcic.logosphere.core.model.AppNotification
import com.krbavcic.logosphere.ui.LoadViewModel
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.common.Avatar
import com.krbavcic.logosphere.ui.common.EmptyNote
import com.krbavcic.logosphere.ui.common.LoadContent
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.Refreshable
import com.krbavcic.logosphere.ui.common.SnackbarMessages
import kotlinx.coroutines.launch

class InboxViewModel(private val app: AppContainer) : LoadViewModel<List<AppNotification>>() {
    init {
        load()
    }

    override suspend fun fetch(force: Boolean): List<AppNotification> = app.inbox.load().notifications

    /** Marks it read in the background; opening its link doesn't wait. */
    fun open(notification: AppNotification) {
        if (notification.isRead) return
        update { list -> list.map { if (it.id == notification.id) it.copy(isRead = true) else it } }
        viewModelScope.launch { runCatching { app.inbox.markRead(notification) } }
    }

    fun markAllRead() = act {
        app.inbox.markAllRead()
        update { list -> list.map { it.copy(isRead = true) } }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun InboxScreen() {
    val app = LocalAppContainer.current
    val vm: InboxViewModel = viewModel { InboxViewModel(app) }
    val navigator = LocalNavigator.current
    val state by vm.state.collectAsStateWithLifecycle()
    val refreshing by vm.refreshing.collectAsStateWithLifecycle()
    val unread by app.inbox.unread.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    SnackbarMessages(vm.messages, snackbar)

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Inbox", style = MaterialTheme.typography.headlineSmall) },
                actions = {
                    if (unread > 0) TextButton(onClick = vm::markAllRead) { Text("Mark all read") }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background),
            )
        },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        LoadContent(state, onRetry = vm::load, modifier = Modifier.padding(padding)) { notifications ->
            Refreshable(refreshing, vm::refresh, Modifier.padding(padding)) {
                LazyColumn(contentPadding = PaddingValues(bottom = 24.dp)) {
                    if (notifications.isEmpty()) item { EmptyNote("You're all caught up.") }
                    items(notifications, key = { it.id }) { n ->
                        NotificationRow(n) {
                            vm.open(n)
                            Links.parse(n.link)?.let(navigator::link)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun NotificationRow(n: AppNotification, onClick: () -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .background(if (n.isRead) MaterialTheme.colorScheme.background else MaterialTheme.colorScheme.surfaceContainerLow)
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Avatar(n.actorId, n.actorName, size = 40.dp)
        Spacer(Modifier.width(12.dp))
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(
                n.message,
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = if (n.isRead) FontWeight.Normal else FontWeight.SemiBold,
            )
            MetaText(Dates.ago(n.createdAt))
        }
        if (!n.isRead) {
            Spacer(Modifier.width(8.dp))
            Box(
                Modifier
                    .size(10.dp)
                    .clip(CircleShape)
                    .background(MaterialTheme.colorScheme.tertiary),
            )
        }
    }
}
