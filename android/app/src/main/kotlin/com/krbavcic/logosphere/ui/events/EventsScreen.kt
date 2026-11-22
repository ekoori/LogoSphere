package com.krbavcic.logosphere.ui.events

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.ExtendedFloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.krbavcic.logosphere.AppContainer
import com.krbavcic.logosphere.core.model.CommunityEvent
import com.krbavcic.logosphere.data.Change
import com.krbavcic.logosphere.ui.LoadViewModel
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.common.BackTopBar
import com.krbavcic.logosphere.ui.common.EmptyNote
import com.krbavcic.logosphere.ui.common.LoadContent
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.Refreshable
import com.krbavcic.logosphere.ui.common.ScreenPadding
import com.krbavcic.logosphere.ui.common.SnackbarMessages

class EventsViewModel(private val app: AppContainer) : LoadViewModel<List<CommunityEvent>>() {
    init {
        load()
        reloadOn(app.changes, Change.Events, Change.Communities)
    }

    override suspend fun fetch(force: Boolean): List<CommunityEvent> = app.api.events()
}

/** What's on: the events of your spheres, and those put on for everyone. */
@Composable
fun EventsScreen() {
    val app = LocalAppContainer.current
    val vm: EventsViewModel = viewModel { EventsViewModel(app) }
    val navigator = LocalNavigator.current
    val state by vm.state.collectAsStateWithLifecycle()
    val refreshing by vm.refreshing.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    SnackbarMessages(vm.messages, snackbar)

    Scaffold(
        topBar = { BackTopBar("What's on", navigator::back) },
        snackbarHost = { SnackbarHost(snackbar) },
        floatingActionButton = {
            ExtendedFloatingActionButton(
                onClick = { navigator.newEvent() },
                icon = { Icon(Icons.Filled.Add, contentDescription = null) },
                text = { Text("Put on an event") },
            )
        },
    ) { padding ->
        LoadContent(state, onRetry = vm::load, modifier = Modifier.padding(padding)) { events ->
            Refreshable(refreshing, vm::refresh, Modifier.padding(padding)) {
                LazyColumn(
                    // Room at the bottom so the last card clears the button.
                    contentPadding = PaddingValues(start = ScreenPadding, end = ScreenPadding, top = 4.dp, bottom = 96.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    item(key = "intro") { MetaText("Your spheres' events, and those open to every member.", maxLines = 2) }
                    if (events.isEmpty()) {
                        item { EmptyNote("Nothing is on yet. A mending night, a swap, a shared meal: yours could be the first.") }
                    }
                    items(events, key = { it.id }) { event -> EventCard(event, onClick = { navigator.event(event.id) }) }
                }
            }
        }
    }
}
