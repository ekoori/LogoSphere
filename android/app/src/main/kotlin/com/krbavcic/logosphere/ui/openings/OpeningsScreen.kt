package com.krbavcic.logosphere.ui.openings

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.outlined.Hub
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExtendedFloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
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
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.krbavcic.logosphere.AppContainer
import com.krbavcic.logosphere.core.model.Community
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.Opening
import com.krbavcic.logosphere.data.Change
import com.krbavcic.logosphere.ui.LoadViewModel
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.common.Choice
import com.krbavcic.logosphere.ui.common.EmptyNote
import com.krbavcic.logosphere.ui.common.FilterMenuChip
import com.krbavcic.logosphere.ui.common.LoadContent
import com.krbavcic.logosphere.ui.common.OpeningCard
import com.krbavcic.logosphere.ui.common.Refreshable
import com.krbavcic.logosphere.ui.common.ScreenPadding
import com.krbavcic.logosphere.ui.common.SegmentedTabs
import com.krbavcic.logosphere.ui.common.SnackbarMessages
import kotlinx.coroutines.async
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.TextButton
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.snapshotFlow
import androidx.lifecycle.viewModelScope
import com.krbavcic.logosphere.core.api.userMessage
import com.krbavcic.logosphere.core.logic.OpeningsQuery
import kotlinx.coroutines.coroutineScope
import androidx.compose.material.icons.outlined.CalendarMonth
import androidx.compose.material.icons.outlined.NearMe
import com.krbavcic.logosphere.core.logic.Places
import com.krbavcic.logosphere.core.logic.Sharing
import com.krbavcic.logosphere.ui.common.LinkText
import com.krbavcic.logosphere.ui.common.ProblemFlag

/**
 * The openings loaded so far, and [next], where the server carries on from (null at the end).
 * [canMeasure]: whether the member's own place gives distances; null when that didn't load.
 */
data class OpeningsData(
    val openings: List<Opening>,
    val spheres: List<Community>,
    val canMeasure: Boolean? = null,
    val next: String? = null,
    val noPlace: Boolean = false,
)

// Sphere filter choices that aren't a single sphere.
private const val REAL_SPHERES = OpeningsQuery.REAL
private const val DEMO_SPHERES = OpeningsQuery.DEMO

class OpeningsViewModel(private val app: AppContainer) : LoadViewModel<OpeningsData>() {
    val viewerId: String? get() = app.session.user?.id

    /** What the list is filtered by; the server applies it. */
    var query = OpeningsQuery()
        private set

    private val _loadingMore = MutableStateFlow(false)
    val loadingMore: StateFlow<Boolean> = _loadingMore.asStateFlow()

    init {
        load()
        reloadOn(app.changes, Change.Openings)
    }

    override suspend fun fetch(force: Boolean): OpeningsData = coroutineScope {
        val first = async { app.api.openingsPage(query) }
        val spheres = async { runCatching { app.communities.list(CommunityKind.Sphere, force) }.getOrDefault(emptyList()) }
        val mine = async {
            viewerId?.let { me -> runCatching { Places.canMeasure(app.api.place(Places.PEOPLE, me).place) }.getOrNull() }
        }
        val page = first.await()
        OpeningsData(page.openings, spheres.await(), mine.await(), page.next, page.noPlace)
    }

    fun choose(asked: OpeningsQuery) {
        if (asked == query) return
        query = asked
        load()
    }

    /** The next page, once; a page for filters since changed is dropped. */
    fun loadMore() {
        val next = current?.next ?: return
        if (_loadingMore.value) return
        _loadingMore.value = true
        val asked = query
        viewModelScope.launch {
            try {
                val page = app.api.openingsPage(asked, next)
                if (asked == query) {
                    update { it.copy(openings = (it.openings + page.openings).distinctBy { o -> o.id }, next = page.next) }
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                logFailure("more", e)
                say(e.userMessage())
            } finally {
                _loadingMore.value = false
            }
        }
    }

    fun like(opening: Opening) = toggleOpeningLike(app.api, opening) { data, f ->
        data.copy(openings = data.openings.map(f))
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OpeningsScreen() {
    val app = LocalAppContainer.current
    val vm: OpeningsViewModel = viewModel { OpeningsViewModel(app) }
    val navigator = LocalNavigator.current
    val state by vm.state.collectAsStateWithLifecycle()
    val refreshing by vm.refreshing.collectAsStateWithLifecycle()
    var type by rememberSaveable { mutableIntStateOf(0) } // all, offers, needs, loans
    var sphereId by rememberSaveable { mutableStateOf<String?>(null) }
    var near by rememberSaveable { mutableStateOf<String?>(null) } // km from your place
    LaunchedEffect(type, sphereId, near) { vm.choose(OpeningsQuery(type, sphereId, near?.toIntOrNull())) }
    val loadingMore by vm.loadingMore.collectAsStateWithLifecycle()
    val list = rememberLazyListState()
    val snackbar = remember { SnackbarHostState() }
    SnackbarMessages(vm.messages, snackbar)

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Openings", style = MaterialTheme.typography.headlineSmall) },
                actions = {
                    ProblemFlag()
                    IconButton(onClick = navigator::events) {
                        Icon(Icons.Outlined.CalendarMonth, contentDescription = "What's on: events")
                    }
                    IconButton(onClick = navigator::nearby) {
                        Icon(Icons.Outlined.NearMe, contentDescription = "Who and what is near you")
                    }
                    IconButton(onClick = { navigator.meaningGraph() }) {
                        Icon(Icons.Outlined.Hub, contentDescription = "Meaning Graph")
                    }
                    IconButton(onClick = navigator::search) { Icon(Icons.Filled.Search, contentDescription = "Search") }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background),
            )
        },
        floatingActionButton = {
            ExtendedFloatingActionButton(
                onClick = navigator::newOpening,
                // The extended FAB keeps its text out of accessibility, so the
                // icon carries the button's spoken label.
                icon = { Icon(Icons.Filled.Add, contentDescription = "New opening") },
                text = { Text("New opening") },
                containerColor = MaterialTheme.colorScheme.tertiary,
                contentColor = MaterialTheme.colorScheme.onTertiary,
            )
        },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        LoadContent(state, onRetry = vm::load, modifier = Modifier.padding(padding)) { data ->
            val within = near?.toIntOrNull()
            val noPlace = within != null && (data.canMeasure == false || data.noPlace)
            // The server filtered them, newest first.
            val shown = data.openings
            // The next page, as the end of the list comes near.
            LaunchedEffect(list, data.next) {
                if (data.next == null) return@LaunchedEffect
                snapshotFlow { list.layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: 0 }
                    .collect { last -> if (last >= list.layoutInfo.totalItemsCount - 6) vm.loadMore() }
            }
            Refreshable(refreshing, vm::refresh, Modifier.padding(padding)) {
                LazyColumn(
                    state = list,
                    contentPadding = PaddingValues(start = ScreenPadding, end = ScreenPadding, top = 4.dp, bottom = 96.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    item(key = "filters") {
                        Row(
                            Modifier
                                .fillMaxWidth()
                                .horizontalScroll(rememberScrollState()),
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            SegmentedTabs(listOf("All", "Offers", "Needs", "To lend or borrow"), type, { type = it })
                            if (data.spheres.isNotEmpty()) {
                                FilterMenuChip(
                                    choices = listOf(
                                        Choice(null, "All spheres"),
                                        Choice(REAL_SPHERES, "Real spheres only"),
                                        Choice(DEMO_SPHERES, "Demo spheres only"),
                                    ) + data.spheres.sortedBy { it.isDemo }
                                        .map { Choice(it.id, if (it.isDemo) "${it.name} (demo)" else it.name) },
                                    selected = sphereId,
                                    onSelect = { sphereId = it },
                                )
                            }
                            FilterMenuChip(
                                choices = listOf(Choice(null, "Any distance")) +
                                    Places.NEAR_KM.map { Choice(it.toString(), "Within $it km") },
                                selected = near,
                                onSelect = { near = it },
                            )
                        }
                    }
                    if (noPlace) {
                        item(key = "no-place") {
                            LinkText("To see what's near you, first say where you are →", navigator::editProfile)
                        }
                    } else if (shown.isEmpty()) {
                        item {
                            EmptyNote(
                                if (within == null) "No offers or needs here yet. Share something with your community."
                                else "Nothing this near. Openings that haven't said where they are, and whose sphere hasn't, are left out.",
                            )
                        }
                    }
                    items(shown, key = { it.id }) { opening ->
                        OpeningCard(
                            opening,
                            viewerId = vm.viewerId,
                            onClick = { navigator.opening(opening.id) },
                            onLike = { vm.like(opening) },
                        )
                    }
                    if (data.next != null) {
                        item(key = "more") {
                            TextButton(onClick = vm::loadMore, enabled = !loadingMore, modifier = Modifier.fillMaxWidth()) {
                                Text(if (loadingMore) "Loading more…" else "Show more")
                            }
                        }
                    }
                }
            }
        }
    }
}
