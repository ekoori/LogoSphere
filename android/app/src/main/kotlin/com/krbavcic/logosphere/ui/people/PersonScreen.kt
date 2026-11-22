package com.krbavcic.logosphere.ui.people

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.krbavcic.logosphere.AppContainer
import com.krbavcic.logosphere.core.model.Exchange
import com.krbavcic.logosphere.core.model.LikeTarget
import com.krbavcic.logosphere.core.model.Opening
import com.krbavcic.logosphere.core.model.PublicUser
import com.krbavcic.logosphere.core.model.ValueCard
import com.krbavcic.logosphere.data.Change
import com.krbavcic.logosphere.ui.Load
import com.krbavcic.logosphere.ui.LoadViewModel
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.common.Avatar
import com.krbavcic.logosphere.ui.common.BackTopBar
import com.krbavcic.logosphere.ui.common.EmptyNote
import com.krbavcic.logosphere.ui.common.LoadContent
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.OpeningCard
import com.krbavcic.logosphere.ui.common.PersonaTag
import com.krbavcic.logosphere.ui.common.Refreshable
import com.krbavcic.logosphere.ui.common.ScreenPadding
import com.krbavcic.logosphere.ui.common.SectionHeading
import com.krbavcic.logosphere.ui.common.SegmentedTabs
import com.krbavcic.logosphere.ui.common.SnackbarMessages
import com.krbavcic.logosphere.ui.common.LinkText
import com.krbavcic.logosphere.ui.common.ValueChips
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import com.krbavcic.logosphere.core.model.MeaningTrail
import com.krbavcic.logosphere.core.logic.Tabs
import com.krbavcic.logosphere.ui.trail.trailItems
import androidx.compose.material3.TextButton
import com.krbavcic.logosphere.core.model.ReportOf
import com.krbavcic.logosphere.ui.common.BlockDialog
import androidx.compose.runtime.mutableStateOf
import com.krbavcic.logosphere.ui.common.ReportLink

data class PersonData(
    val user: PublicUser,
    val cards: List<ValueCard>,
    val trail: MeaningTrail,
    val openings: List<Opening>,
)

class PersonViewModel(private val app: AppContainer, private val id: String) : LoadViewModel<PersonData>() {
    val viewerId: String? get() = app.session.user?.id
    val isSelf: Boolean get() = viewerId == id
    val acknowledgements = acknowledgementActions(app.api)

    init {
        load()
        reloadOn(app.changes, Change.Openings, Change.Exchanges)
    }

    override suspend fun fetch(force: Boolean): PersonData = coroutineScope {
        val user = async { app.api.user(id) }
        val cards = async { runCatching { app.api.valueCards(id) }.getOrDefault(emptyList()) }
        val trail = async { runCatching { app.api.trail(id) }.getOrDefault(MeaningTrail(id = id)) }
        val openings = async { runCatching { app.openings.list(force) }.getOrDefault(emptyList()) }
        PersonData(
            user = user.await(),
            cards = cards.await(),
            trail = trail.await(),
            openings = openings.await().filter { it.providerId == id || it.actingUserId == id },
        )
    }

    fun setBlocked(blocked: Boolean) = act(onSuccess = {
        app.changes.emit(Change.Profile) // who's nearby follows from it
        reload()
        say(if (blocked) "Blocked. They aren't told." else "Unblocked.")
    }) { app.api.setBlocked(id, blocked) }

    fun toggleFollow() = act {
        val following = app.api.toggleFollow(id)
        update { it.copy(user = it.user.copy(isFollowing = following)) }
    }

    fun likeExchange(exchange: Exchange) = toggleExchangeLike(app.api, exchange, LikeTarget.Exchange) { data, f ->
        data.copy(trail = data.trail.mapExchanges(f))
    }

    fun likeOpening(opening: Opening) = toggleOpeningLike(app.api, opening) { data, f ->
        data.copy(openings = data.openings.map(f))
    }
}

@Composable
fun PersonScreen(id: String, initialTab: String? = null) {
    val app = LocalAppContainer.current
    val vm: PersonViewModel = viewModel(key = "person-$id") { PersonViewModel(app, id) }
    val navigator = LocalNavigator.current
    val state by vm.state.collectAsStateWithLifecycle()
    val refreshing by vm.refreshing.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    var blocking by rememberSaveable { mutableStateOf(false) }
    var tab by rememberSaveable { mutableIntStateOf(Tabs.indexOf(initialTab, listOf(Tabs.TRAIL, Tabs.OPENINGS))) }
    val snackbar = remember { SnackbarHostState() }
    SnackbarMessages(vm.messages, snackbar)

    Scaffold(
        topBar = { BackTopBar("Member", navigator::back) },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        LoadContent(state, onRetry = vm::load, modifier = Modifier.padding(padding)) { data ->
            Refreshable(refreshing, vm::refresh, Modifier.padding(padding)) {
                LazyColumn(
                    contentPadding = PaddingValues(start = ScreenPadding, end = ScreenPadding, top = 8.dp, bottom = 32.dp),
                    verticalArrangement = Arrangement.spacedBy(14.dp),
                ) {
                    item(key = "head") {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Avatar(data.user.userId, data.user.displayName, size = 72.dp)
                            Spacer(Modifier.width(16.dp))
                            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                                Text(data.user.displayName, style = MaterialTheme.typography.headlineSmall)
                                if (data.user.isAgent) PersonaTag()
                                data.user.location?.let { MetaText("📍 $it") }
                                MetaText("${data.trail.exchanges.size} exchanges  ·  ${data.openings.size} openings")
                            }
                        }
                    }
                    if (data.user.isAgent) {
                        item(key = "persona") {
                            MetaText("A famous name playing an everyday neighbour in the demo spheres. Their posts are written by AI.", maxLines = 3)
                        }
                    }
                    item(key = "follow") {
                        if (vm.isSelf) {
                            MetaText("This is your public profile, as others see it.")
                        } else if (data.user.isFollowing) {
                            OutlinedButton(onClick = vm::toggleFollow, enabled = !busy, modifier = Modifier.fillMaxWidth()) { Text("✓ Following") }
                        } else {
                            Button(onClick = vm::toggleFollow, enabled = !busy, modifier = Modifier.fillMaxWidth()) { Text("+ Follow") }
                        }
                    }
                    if (!vm.isSelf) {
                        item(key = "contact") {
                            Column {
                                if (data.user.canMessage) {
                                    OutlinedButton(onClick = { navigator.conversation(id) }, modifier = Modifier.fillMaxWidth()) {
                                        Text("Message")
                                    }
                                }
                                Row {
                                    TextButton(
                                        onClick = { if (data.user.blocked) vm.setBlocked(false) else blocking = true },
                                        enabled = !busy,
                                    ) { Text(if (data.user.blocked) "Unblock" else "Block") }
                                    ReportLink(ReportOf.person(id))
                                }
                                if (blocking) {
                                    BlockDialog(data.user.displayName, onBlock = { vm.setBlocked(true) }, onClose = { blocking = false })
                                }
                            }
                        }
                    }
                    if (data.cards.isNotEmpty()) {
                        item(key = "values") {
                            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                SectionHeading("Values")
                                ValueChips(data.cards)
                                LinkText("See them in the Meaning Graph", { navigator.meaningGraph(id) })
                            }
                        }
                    }
                    item(key = "tabs") {
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) {
                            SegmentedTabs(listOf("Meaning Trail", "Offers & Needs"), tab, { tab = it })
                        }
                    }
                    if (tab == 0) {
                        trailItems(
                            data.trail,
                            viewerId = vm.viewerId,
                            actions = vm.acknowledgements,
                            busy = busy,
                            empty = "No meaning trail recorded yet.",
                            onExchange = { navigator.exchange(it.id) },
                            onLike = vm::likeExchange,
                        )
                    } else {
                        if (data.openings.isEmpty()) item { EmptyNote("No offers or needs posted.") }
                        items(data.openings, key = { "o-" + it.id }) { opening ->
                            OpeningCard(opening, vm.viewerId, onClick = { navigator.opening(opening.id) }, onLike = { vm.likeOpening(opening) })
                        }
                    }
                }
            }
        }
    }
}
