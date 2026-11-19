package com.krbavcic.logosphere.ui.communities

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.ExperimentalMaterial3Api
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
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.krbavcic.logosphere.AppContainer
import com.krbavcic.logosphere.core.logic.Membership
import com.krbavcic.logosphere.core.model.Community
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.data.Change
import com.krbavcic.logosphere.ui.LoadViewModel
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.common.Banner
import com.krbavcic.logosphere.ui.common.BrandCard
import com.krbavcic.logosphere.ui.common.DonePill
import com.krbavcic.logosphere.ui.common.EmptyNote
import com.krbavcic.logosphere.ui.common.LoadContent
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.QuietPill
import com.krbavcic.logosphere.ui.common.Refreshable
import com.krbavcic.logosphere.ui.common.ScreenPadding
import com.krbavcic.logosphere.ui.common.SegmentedTabs
import com.krbavcic.logosphere.ui.common.SnackbarMessages
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope

class CommunitiesViewModel(private val app: AppContainer) : LoadViewModel<Map<CommunityKind, List<Community>>>() {
    val viewerId: String? get() = app.session.user?.id

    init {
        load()
        reloadOn(app.changes, Change.Communities)
    }

    override suspend fun fetch(force: Boolean) = coroutineScope {
        CommunityKind.entries.associateWith { kind -> async { app.communities.list(kind, force) } }
            .mapValues { it.value.await() }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CommunitiesScreen() {
    val app = LocalAppContainer.current
    val vm: CommunitiesViewModel = viewModel { CommunitiesViewModel(app) }
    val navigator = LocalNavigator.current
    val state by vm.state.collectAsStateWithLifecycle()
    val refreshing by vm.refreshing.collectAsStateWithLifecycle()
    var tab by rememberSaveable { mutableIntStateOf(0) }
    val snackbar = remember { SnackbarHostState() }
    SnackbarMessages(vm.messages, snackbar)

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Spheres", style = MaterialTheme.typography.headlineSmall) },
                actions = {
                    IconButton(onClick = navigator::search) { Icon(Icons.Filled.Search, contentDescription = "Search") }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background),
            )
        },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        LoadContent(state, onRetry = vm::load, modifier = Modifier.padding(padding)) { lists ->
            val kind = CommunityKind.entries[tab]
            // Your own communities first, then the rest.
            val shown = lists[kind].orEmpty().sortedByDescending { Membership.isMember(it, vm.viewerId) }
            Refreshable(refreshing, vm::refresh, Modifier.padding(padding)) {
                LazyColumn(
                    contentPadding = PaddingValues(start = ScreenPadding, end = ScreenPadding, top = 4.dp, bottom = 32.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    item(key = "tabs") {
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) {
                            SegmentedTabs(CommunityKind.entries.map { it.plural }, tab, { tab = it })
                        }
                    }
                    item(key = "intro") {
                        MetaText(
                            when (kind) {
                                CommunityKind.Sphere -> "Communities with shared norms and meaning. Join one to see its activity."
                                CommunityKind.Alliance -> "Federations and partnerships inside your spheres."
                                CommunityKind.Project -> "Shared work with a purpose, inside your spheres."
                            },
                            maxLines = 2,
                        )
                    }
                    if (shown.isEmpty()) item { EmptyNote("No ${kind.plural.lowercase()} to show yet.") }
                    items(shown, key = { kind.name + it.id }) { community ->
                        CommunityCard(community, vm.viewerId) { navigator.community(kind, community.id) }
                    }
                }
            }
        }
    }
}

@Composable
fun CommunityCard(community: Community, viewerId: String?, onClick: () -> Unit) {
    val app = LocalAppContainer.current
    BrandCard(Modifier.fillMaxWidth(), onClick = onClick) {
        Column {
            Banner(
                imageUrl = if (community.hasImage) app.api.communityImageUrl(community.kind, community.id) else null,
                kind = community.kind,
                height = 96.dp,
            )
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        community.name,
                        style = MaterialTheme.typography.titleMedium,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f),
                    )
                    Spacer(Modifier.padding(4.dp))
                    when {
                        Membership.isMember(community, viewerId) -> DonePill(text = "Member")
                        Membership.role(community, viewerId) == "pending" -> QuietPill("Requested")
                    }
                }
                community.description?.takeIf { it.isNotBlank() }?.let {
                    Text(
                        it,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                val members = community.members.count { it.role != "pending" }
                MetaText(
                    listOfNotNull(
                        "$members member${if (members == 1) "" else "s"}",
                        community.sphereName?.takeIf { community.kind != CommunityKind.Sphere }?.let { "✦ $it" },
                        community.location?.takeIf { community.kind == CommunityKind.Sphere },
                        if (community.isClosed) "Closed" else null,
                    ).joinToString("  ·  "),
                )
            }
        }
    }
}
