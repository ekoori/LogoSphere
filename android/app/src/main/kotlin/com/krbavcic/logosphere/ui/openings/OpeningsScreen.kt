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

data class OpeningsData(val openings: List<Opening>, val spheres: List<Community>)

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
        OpeningsData(openings.await(), spheres.await())
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
    val snackbar = remember { SnackbarHostState() }
    SnackbarMessages(vm.messages, snackbar)

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Openings", style = MaterialTheme.typography.headlineSmall) },
                actions = {
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
                        }
                    }
                    if (shown.isEmpty()) {
                        item { EmptyNote("No offers or needs here yet. Share something with your community.") }
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
