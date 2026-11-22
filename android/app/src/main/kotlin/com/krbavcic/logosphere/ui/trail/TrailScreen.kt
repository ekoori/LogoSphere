package com.krbavcic.logosphere.ui.trail

import android.content.Context
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExtendedFloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.ListItem
import androidx.compose.material3.ListItemDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.krbavcic.logosphere.AppContainer
import com.krbavcic.logosphere.core.model.DemoStatus
import com.krbavcic.logosphere.core.model.Exchange
import com.krbavcic.logosphere.core.model.LikeTarget
import com.krbavcic.logosphere.core.model.Opening
import com.krbavcic.logosphere.core.model.PersonRef
import com.krbavcic.logosphere.data.Change
import com.krbavcic.logosphere.ui.LoadViewModel
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.Tab
import com.krbavcic.logosphere.ui.common.Avatar
import com.krbavcic.logosphere.ui.common.DemoInviteCard
import com.krbavcic.logosphere.ui.common.EmptyNote
import com.krbavcic.logosphere.ui.common.ExchangeCard
import com.krbavcic.logosphere.ui.common.LoadContent
import com.krbavcic.logosphere.ui.common.OpeningCard
import com.krbavcic.logosphere.ui.common.Refreshable
import com.krbavcic.logosphere.ui.common.ScreenPadding
import com.krbavcic.logosphere.ui.common.ScrollingTabs
import com.krbavcic.logosphere.ui.common.SnackbarMessages
import com.krbavcic.logosphere.ui.common.Wordmark
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope

data class TrailData(
    val trail: List<Exchange>,
    val myOpenings: List<Opening>,
    val following: List<PersonRef>,
    /** Demo spheres, when the member is in none of them yet: the invitation. */
    val demoInvite: DemoStatus? = null,
)

class TrailViewModel(private val app: AppContainer) : LoadViewModel<TrailData>() {
    val viewerId: String? get() = app.session.user?.id

    init {
        load()
        reloadOn(app.changes, Change.Openings, Change.Exchanges)
    }

    override suspend fun fetch(force: Boolean): TrailData = coroutineScope {
        val trail = async { app.api.myTrail() }
        val openings = async { app.openings.list(force) }
        val following = async { app.api.following() }
        val demo = async { runCatching { app.api.demo() }.getOrNull() }
        val me = viewerId
        TrailData(
            trail = trail.await(),
            // Your own postings, including those you posted for a group.
            myOpenings = openings.await().filter { it.providerId == me || it.actingUserId == me },
            following = following.await(),
            demoInvite = demo.await()?.takeIf { it.spheres.isNotEmpty() && !it.joinedAny },
        )
    }

    /** Join every demo sphere at once (the invitation's main button). */
    fun joinDemo() = act(onSuccess = {
        app.openings.invalidate()
        app.changes.emit(Change.Communities)
        app.changes.emit(Change.Openings)
        update { it.copy(demoInvite = null) }
        say("You've joined the demo spheres. Try anything there.")
    }) { app.api.joinDemo() }

    fun likeExchange(exchange: Exchange) = toggleExchangeLike(app.api, exchange, LikeTarget.Exchange) { data, f ->
        data.copy(trail = data.trail.map(f))
    }

    fun likeOpening(opening: Opening) = toggleOpeningLike(app.api, opening) { data, f ->
        data.copy(myOpenings = data.myOpenings.map(f))
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TrailScreen() {
    val app = LocalAppContainer.current
    val vm: TrailViewModel = viewModel { TrailViewModel(app) }
    val navigator = LocalNavigator.current
    val state by vm.state.collectAsStateWithLifecycle()
    val refreshing by vm.refreshing.collectAsStateWithLifecycle()
    var tab by rememberSaveable { mutableIntStateOf(1) } // Openings, though Trail comes first
    // "Not now" on the demo invitation is remembered on this device.
    val context = LocalContext.current
    val prefs = remember { context.getSharedPreferences("logosphere", Context.MODE_PRIVATE) }
    var demoInviteDismissed by remember { mutableStateOf(prefs.getBoolean("demoInviteDismissed", false)) }
    fun dismissDemoInvite() {
        prefs.edit().putBoolean("demoInviteDismissed", true).apply()
        demoInviteDismissed = true
    }
    val snackbar = remember { SnackbarHostState() }
    SnackbarMessages(vm.messages, snackbar)

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Wordmark(fontSize = MaterialTheme.typography.titleLarge.fontSize) },
                actions = {
                    IconButton(onClick = navigator::search) { Icon(Icons.Filled.Search, contentDescription = "Search") }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background),
            )
        },
        floatingActionButton = {
            if (tab == 1) {
                ExtendedFloatingActionButton(
                    onClick = navigator::newOpening,
                    // The extended FAB keeps its text out of accessibility.
                    icon = { Icon(Icons.Filled.Add, contentDescription = "New opening") },
                    text = { Text("New opening") },
                    containerColor = MaterialTheme.colorScheme.tertiary,
                    contentColor = MaterialTheme.colorScheme.onTertiary,
                )
            }
        },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        LoadContent(state, onRetry = vm::load, modifier = Modifier.padding(padding)) { data ->
            Refreshable(refreshing, vm::refresh, Modifier.padding(padding)) {
                LazyColumn(
                    contentPadding = PaddingValues(start = ScreenPadding, end = ScreenPadding, top = 4.dp, bottom = 96.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    data.demoInvite?.let { invite ->
                        if (!demoInviteDismissed) {
                            item(key = "demo-invite") {
                                DemoInviteCard(invite, onJoin = vm::joinDemo, onLook = { navigator.tab(Tab.Communities) },
                                    onDismiss = { dismissDemoInvite() })
                            }
                        }
                    }
                    item(key = "tabs") {
                        ScrollingTabs(
                            options = listOf("Meaning Trail", "My openings", "Following (${data.following.size})"),
                            selected = tab,
                            onSelect = { tab = it },
                        )
                    }
                    when (tab) {
                        0 -> if (data.trail.isEmpty()) {
                            item {
                                EmptyNote("Your Meaning Trail is empty. Give a little — help a neighbour, share a skill — and your trail of trust will grow here.")
                            }
                        } else {
                            items(data.trail, key = { "x-" + it.id }) { exchange ->
                                ExchangeCard(
                                    exchange,
                                    viewerId = vm.viewerId,
                                    onClick = { navigator.exchange(exchange.id) },
                                    onLike = { vm.likeExchange(exchange) },
                                )
                            }
                        }
                        1 -> if (data.myOpenings.isEmpty()) {
                            item { EmptyNote("You haven't posted any offers or needs yet. Share something with your community.") }
                        } else {
                            items(data.myOpenings, key = { "o-" + it.id }) { opening ->
                                OpeningCard(
                                    opening,
                                    viewerId = vm.viewerId,
                                    onClick = { navigator.opening(opening.id) },
                                    onLike = { vm.likeOpening(opening) },
                                )
                            }
                        }
                        else -> if (data.following.isEmpty()) {
                            item { EmptyNote("You're not following anyone yet. Open a member's profile and tap Follow to see them here.") }
                        } else {
                            items(data.following, key = { "p-" + it.id }) { person ->
                                ListItem(
                                    headlineContent = { Text(person.name ?: "Member", style = MaterialTheme.typography.titleSmall) },
                                    leadingContent = { Avatar(person.id, person.name) },
                                    colors = ListItemDefaults.colors(containerColor = MaterialTheme.colorScheme.background),
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .clickable { navigator.person(person.id) },
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}
