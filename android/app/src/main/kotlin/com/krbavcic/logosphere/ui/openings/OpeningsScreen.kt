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
import kotlinx.coroutines.coroutineScope
import androidx.compose.material.icons.outlined.CalendarMonth
import androidx.compose.material.icons.outlined.NearMe
import com.krbavcic.logosphere.core.logic.Places
import com.krbavcic.logosphere.ui.common.LinkText

/** [canMeasure]: whether the member's own place gives distances; null when that didn't load. */
data class OpeningsData(val openings: List<Opening>, val spheres: List<Community>, val canMeasure: Boolean? = null)

// Sphere filter choices that aren't a single sphere.
private const val REAL_SPHERES = "real-spheres"
private const val DEMO_SPHERES = "demo-spheres"

class OpeningsViewModel(private val app: AppContainer) : LoadViewModel<OpeningsData>() {
    val viewerId: String? get() = app.session.user?.id

    init {
        load()
        reloadOn(app.changes, Change.Openings)
    }

    override suspend fun fetch(force: Boolean): OpeningsData = coroutineScope {
        val openings = async { app.openings.list(force) }
        val spheres = async { runCatching { app.communities.list(CommunityKind.Sphere, force) }.getOrDefault(emptyList()) }
        val mine = async {
            viewerId?.let { me -> runCatching { Places.canMeasure(app.api.place(Places.PEOPLE, me).place) }.getOrNull() }
        }
        OpeningsData(openings.await(), spheres.await(), mine.await())
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
    var type by rememberSaveable { mutableIntStateOf(0) } // all, offers, needs
    var sphereId by rememberSaveable { mutableStateOf<String?>(null) }
    var near by rememberSaveable { mutableStateOf<String?>(null) } // km from your place
    val snackbar = remember { SnackbarHostState() }
    SnackbarMessages(vm.messages, snackbar)

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Openings", style = MaterialTheme.typography.headlineSmall) },
                actions = {
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
            val noPlace = within != null && data.canMeasure == false
            val shown = data.openings
                .filter { when (type) { 1 -> it.isOffer; 2 -> !it.isOffer; else -> true } }
                .filter {
                    when (sphereId) {
                        null -> true
                        REAL_SPHERES -> !it.isDemo
                        DEMO_SPHERES -> it.isDemo
                        else -> it.sphereId == sphereId
                    }
                }
                .filter { within == null || (it.distance?.km ?: Int.MAX_VALUE) <= within }
                // Nearest band first, each still in the order it came.
                .let { list -> if (within == null) list else list.sortedBy { it.distance?.km } }
            Refreshable(refreshing, vm::refresh, Modifier.padding(padding)) {
                LazyColumn(
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
                            SegmentedTabs(listOf("All", "Offers", "Needs"), type, { type = it })
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
                }
            }
        }
    }
}
