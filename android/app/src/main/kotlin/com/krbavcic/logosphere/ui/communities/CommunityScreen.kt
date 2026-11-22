package com.krbavcic.logosphere.ui.communities

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.AssistChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.krbavcic.logosphere.AppContainer
import com.krbavcic.logosphere.core.logic.Dates
import com.krbavcic.logosphere.core.logic.Membership
import com.krbavcic.logosphere.core.logic.Tabs
import com.krbavcic.logosphere.core.model.Community
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.Exchange
import com.krbavcic.logosphere.core.model.LikeTarget
import com.krbavcic.logosphere.core.model.Member
import com.krbavcic.logosphere.core.model.Opening
import com.krbavcic.logosphere.core.model.PersonRef
import com.krbavcic.logosphere.data.Change
import com.krbavcic.logosphere.ui.Load
import com.krbavcic.logosphere.ui.LoadViewModel
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.common.Avatar
import com.krbavcic.logosphere.ui.common.BackTopBar
import com.krbavcic.logosphere.ui.common.Banner
import com.krbavcic.logosphere.ui.common.DemoNote
import com.krbavcic.logosphere.ui.common.DemoTag
import com.krbavcic.logosphere.ui.common.EmptyNote
import com.krbavcic.logosphere.ui.common.ExchangeCard
import com.krbavcic.logosphere.ui.common.GroupAvatar
import com.krbavcic.logosphere.ui.common.LinkText
import com.krbavcic.logosphere.ui.common.LoadContent
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.OpeningCard
import com.krbavcic.logosphere.ui.common.PersonaTag
import com.krbavcic.logosphere.ui.common.PrimaryAction
import com.krbavcic.logosphere.ui.common.QuietPill
import com.krbavcic.logosphere.ui.common.Refreshable
import com.krbavcic.logosphere.ui.common.ScreenPadding
import com.krbavcic.logosphere.ui.common.ScrollingTabs
import com.krbavcic.logosphere.ui.common.SectionHeading
import com.krbavcic.logosphere.ui.common.SnackbarMessages
import com.krbavcic.logosphere.ui.common.ValueChips
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope

data class CommunityData(
    val community: Community,
    val canViewActivity: Boolean,
    val trail: List<Exchange>,
    val openings: List<Opening>,
    /** A sphere's alliances. */
    val alliances: List<PersonRef>,
    /** A sphere's or alliance's projects (ids resolved by name where needed). */
    val projects: List<PersonRef>,
    /** A project's lead alliance, when it has one. */
    val ownerAlliance: PersonRef?,
)

class CommunityViewModel(
    private val app: AppContainer,
    private val kind: CommunityKind,
    private val id: String,
) : LoadViewModel<CommunityData>() {
    val viewerId: String? get() = app.session.user?.id
    private val isPlatformAdmin: Boolean get() = app.session.user?.isPlatformAdmin == true

    init {
        load()
        reloadOn(app.changes, Change.Openings, Change.Exchanges, Change.Communities, Change.ValueCards)
    }

    override suspend fun fetch(force: Boolean): CommunityData = coroutineScope {
        val community = app.api.community(kind, id)
        val canView = Membership.canViewActivity(community, viewerId, isPlatformAdmin)
        val projectsList = async { runCatching { app.communities.list(CommunityKind.Project, force) }.getOrDefault(emptyList()) }
        val alliancesList = async { runCatching { app.communities.list(CommunityKind.Alliance, force) }.getOrDefault(emptyList()) }
        val projectIdByName = projectsList.await().associate { it.name to it.id }

        val alliances = if (kind == CommunityKind.Sphere) community.allianceList else emptyList()
        val projects = when (kind) {
            CommunityKind.Sphere -> community.projectList
            CommunityKind.Alliance -> community.projects.map { PersonRef(projectIdByName[it] ?: "", it) }
            CommunityKind.Project -> emptyList()
        }
        val ownerAlliance = community.ownerAlliance?.let { name ->
            alliancesList.await().firstOrNull { it.name == name }?.let { PersonRef(it.id, it.name) } ?: PersonRef("", name)
        }

        if (!canView) return@coroutineScope CommunityData(community, false, emptyList(), emptyList(), alliances, projects, ownerAlliance)

        // The trail of a group gathers its own exchanges, its alliances' (for a sphere) and
        // everything tagged with its projects — as the web's entity pages do.
        val own = listOf(id) + alliances.map { it.id }
        val projectIds = when (kind) {
            CommunityKind.Project -> listOf(id)
            else -> projects.map { it.id }.filter { it.isNotEmpty() }
        }
        val trailCalls = own.map { owner -> async { runCatching { app.api.trailOf(owner) }.getOrDefault(emptyList()) } } +
            projectIds.map { project -> async { runCatching { app.api.projectTrail(project) }.getOrDefault(emptyList()) } }
        val openings = async { app.openings.list(force) }

        val projectNames = projects.map { it.name }.toSet()
        val related = openings.await().filter {
            (kind == CommunityKind.Sphere && it.sphereId == id) ||
                it.providerId == id ||
                (kind != CommunityKind.Sphere && it.projectName != null && it.projectName in projectNames) ||
                (kind == CommunityKind.Project && it.projectName == community.name)
        }
        val trail = trailCalls.awaitAll().flatten().distinctBy { it.id }.sortedByDescending { Dates.parse(it.startedAt) }
        CommunityData(community, true, trail, related, alliances, projects, ownerAlliance)
    }

    fun join() = act {
        val result = app.api.join(kind, id)
        app.communities.invalidate(kind)
        app.changes.emit(Change.Communities)
        say(
            when {
                result.pending -> "Request sent — a manager will approve it."
                result.alreadyMember -> "You're already a member."
                else -> "Welcome! You've joined."
            },
        )
        reload()
    }

    /** Leaves the group, or withdraws a request to join it. */
    fun leave() = act {
        val message = app.api.leave(kind, id)
        app.communities.invalidate(kind)
        app.openings.invalidate()
        app.changes.emit(Change.Communities)
        say(message)
        reload()
    }

    /** Approves or declines a request, promotes, demotes or removes a member. */
    fun setRole(memberId: String, role: String) = act(onSuccess = {
        app.communities.invalidate(kind)
        app.changes.emit(Change.Communities)
        reload()
    }) { app.api.setMemberRole(kind, id, memberId, role) }

    fun likeExchange(exchange: Exchange) = toggleExchangeLike(app.api, exchange, LikeTarget.Exchange) { data, f ->
        data.copy(trail = data.trail.map(f))
    }

    fun likeOpening(opening: Opening) = toggleOpeningLike(app.api, opening) { data, f ->
        data.copy(openings = data.openings.map(f))
    }
}

@Composable
fun CommunityScreen(kind: CommunityKind, id: String, initialTab: String? = null) {
    val app = LocalAppContainer.current
    val vm: CommunityViewModel = viewModel(key = "community-$kind-$id") { CommunityViewModel(app, kind, id) }
    val navigator = LocalNavigator.current
    val state by vm.state.collectAsStateWithLifecycle()
    val refreshing by vm.refreshing.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    SnackbarMessages(vm.messages, snackbar)

    Scaffold(
        topBar = { BackTopBar(kind.noun, navigator::back) },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        LoadContent(state, onRetry = vm::load, modifier = Modifier.padding(padding)) { data ->
            Refreshable(refreshing, vm::refresh, Modifier.padding(padding)) {
                CommunityContent(data, vm, busy, snackbar, initialTab)
            }
        }
    }
}

/** The tabs, by the names links use (`?tab=governance`). */
private val TABS = listOf("trail", "openings", "people", "governance", "charter")

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun CommunityContent(data: CommunityData, vm: CommunityViewModel, busy: Boolean, snackbar: SnackbarHostState, initialTab: String?) {
    val app = LocalAppContainer.current
    val navigator = LocalNavigator.current
    val c = data.community
    val me = vm.viewerId
    val isAdmin = app.session.user?.isPlatformAdmin == true
    val role = Membership.role(c, me)
    val isMember = Membership.isMember(c, me)
    val canManage = Membership.canManage(c, me, isAdmin)
    val canSetRoles = Membership.canSetRoles(c, me, isAdmin)
    val members = c.members.filter { it.role != "pending" }
    var tab by rememberSaveable { mutableIntStateOf(Tabs.indexOf(initialTab, TABS)) }
    var confirmLeave by rememberSaveable { mutableStateOf(false) }

    LazyColumn(contentPadding = PaddingValues(bottom = 32.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        item(key = "banner") {
            Banner(
                imageUrl = if (c.hasImage) app.api.communityImageUrl(c.kind, c.id) else null,
                kind = c.kind,
                height = 180.dp,
            ) {
                Column(
                    Modifier
                        .align(Alignment.BottomStart)
                        .padding(ScreenPadding),
                ) {
                    Text(
                        "${c.kind.glyph} ${c.kind.noun.uppercase()}",
                        style = MaterialTheme.typography.labelMedium,
                        color = Color(0xFFF3ECDA),
                    )
                    Text(c.name, style = MaterialTheme.typography.headlineMedium, color = Color(0xFFFDFAF2))
                }
            }
        }
        item(key = "about") {
            Column(Modifier.padding(horizontal = ScreenPadding), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    if (c.isDemo) DemoTag()
                    QuietPill("${c.peopleCount} member${if (c.peopleCount == 1) "" else "s"}")
                    c.location?.takeIf { c.kind == CommunityKind.Sphere && it.isNotBlank() }?.let { QuietPill(it) }
                    if (c.kind == CommunityKind.Sphere && c.isPublic) QuietPill("Public")
                    if (c.kind == CommunityKind.Project) QuietPill(if (c.isClosed) "Closed" else c.status ?: "Ongoing")
                    if (c.joinPolicy == "approval") QuietPill("Joining needs approval")
                }
                if (c.isDemo) DemoNote("Demo ${c.kind.noun.lowercase()}")
                if (c.kind != CommunityKind.Sphere && c.parentSphereId != null) {
                    AssistChip(
                        onClick = { navigator.community(CommunityKind.Sphere, c.parentSphereId!!) },
                        label = { Text("✦ ${c.sphereName ?: "Its sphere"}") },
                    )
                }
                if (c.kind == CommunityKind.Project) {
                    val lead = data.ownerAlliance
                    when {
                        lead != null -> TextButton(
                            onClick = { if (lead.id.isNotEmpty()) navigator.community(CommunityKind.Alliance, lead.id) },
                            contentPadding = PaddingValues(0.dp),
                        ) { Text("Led by ◈ ${lead.name}") }
                        c.ownerName != null -> TextButton(
                            onClick = { c.ownerId?.let(navigator::person) },
                            contentPadding = PaddingValues(0.dp),
                        ) { Text("By ${c.ownerName}") }
                    }
                }
                c.description?.takeIf { it.isNotBlank() }?.let { Text(it, style = MaterialTheme.typography.bodyLarge) }
                when {
                    role == "pending" -> MetaText("Your request to join is waiting for a manager's approval.", maxLines = 2)
                    !isMember && me != null -> PrimaryAction(
                        if (c.joinPolicy == "approval") "Ask to join this ${c.kind.noun.lowercase()}" else "Join this ${c.kind.noun.lowercase()}",
                        onClick = vm::join,
                        busy = busy,
                    )
                }
                if (canManage) {
                    OutlinedButton(onClick = { navigator.manageCommunity(c.kind, c.id) }, modifier = Modifier.fillMaxWidth()) {
                        Text("⚙ Manage ${c.kind.noun.lowercase()}" + if (isAdmin && !Membership.managesItself(c, me)) " (platform admin)" else "")
                    }
                }
                if (Membership.canLeave(c, me)) {
                    LinkText(
                        if (role == "pending") "Withdraw my request to join" else "Leave this ${c.kind.noun.lowercase()}",
                        onClick = { confirmLeave = true },
                        enabled = !busy,
                    )
                }
                if (canSetRoles && c.pendingMembers.isNotEmpty()) {
                    TextButton(onClick = { tab = TABS.indexOf("people") }, contentPadding = PaddingValues(0.dp)) {
                        Text("${c.pendingMembers.size} waiting for approval →")
                    }
                }
            }
        }

        if (!data.canViewActivity) {
            item(key = "gate") {
                EmptyNote("Join this ${c.kind.noun.lowercase()} to see its meaning trail, openings and people.")
            }
            item(key = "charter-only") { Charter(data, Modifier.padding(horizontal = ScreenPadding)) }
            return@LazyColumn
        }

        item(key = "tabs") {
            ScrollingTabs(listOf("Trail", "Openings", "People (${members.size})", "Governance", "Charter"), tab, { tab = it }, Modifier.padding(horizontal = ScreenPadding))
        }
        when (tab) {
            0 -> if (data.trail.isEmpty()) {
                item { EmptyNote("No meaning trail recorded yet for this ${c.kind.noun.lowercase()}.") }
            } else {
                items(data.trail, key = { "x-" + it.id }) { exchange ->
                    ExchangeCard(
                        exchange,
                        viewerId = me,
                        onClick = { navigator.exchange(exchange.id) },
                        onLike = { vm.likeExchange(exchange) },
                        modifier = Modifier.padding(horizontal = ScreenPadding),
                    )
                }
            }
            1 -> {
                if (canManage && !c.isClosed) {
                    item(key = "post-as") {
                        OutlinedButton(onClick = { navigator.newOpening(c) }, modifier = Modifier.padding(horizontal = ScreenPadding).fillMaxWidth()) {
                            Text("+ Post an opening as ${c.name}")
                        }
                    }
                }
                if (data.openings.isEmpty()) item {
                    EmptyNote(
                        if (c.isClosed) "This project is closed — it takes no new openings."
                        else "No offers or needs posted for this ${c.kind.noun.lowercase()} yet.",
                    )
                }
                items(data.openings, key = { "o-" + it.id }) { opening ->
                    OpeningCard(
                        opening,
                        viewerId = me,
                        onClick = { navigator.opening(opening.id) },
                        onLike = { vm.likeOpening(opening) },
                        modifier = Modifier.padding(horizontal = ScreenPadding),
                    )
                }
            }
            2 -> memberItems(c, me, canSetRoles, busy, onSetRole = vm::setRole, onOpen = navigator::person)
            3 -> item(key = "governance") {
                GovernancePanel(
                    c.kind,
                    c.id,
                    snackbar,
                    onManage = if (canManage) ({ navigator.manageCommunity(c.kind, c.id) }) else null,
                    modifier = Modifier.padding(horizontal = ScreenPadding),
                )
            }
            else -> item(key = "charter") {
                Charter(data, Modifier.padding(horizontal = ScreenPadding), onEdit = if (canManage) ({ navigator.manageCommunity(c.kind, c.id) }) else null)
            }
        }
    }

    if (confirmLeave) {
        val noun = c.kind.noun.lowercase()
        AlertDialog(
            onDismissRequest = { confirmLeave = false },
            title = { Text(if (role == "pending") "Withdraw your request?" else "Leave ${c.name}?") },
            text = {
                Text(
                    if (role == "pending") "You can ask to join again later."
                    else "You'll stop seeing its members-only activity. You can join again later" +
                        if (c.joinPolicy == "approval") ", with a manager's approval." else ".",
                )
            },
            confirmButton = {
                TextButton(onClick = { confirmLeave = false; vm.leave() }) {
                    Text(if (role == "pending") "Withdraw" else "Leave the $noun")
                }
            },
            dismissButton = { TextButton(onClick = { confirmLeave = false }) { Text("Stay") } },
        )
    }
}

/** What the group stands for: its values, value cards, and (for a sphere) what it holds. */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun Charter(data: CommunityData, modifier: Modifier = Modifier, onEdit: (() -> Unit)? = null) {
    val navigator = LocalNavigator.current
    val c = data.community
    Column(modifier, verticalArrangement = Arrangement.spacedBy(12.dp)) {
        if (c.valueCards.isNotEmpty() || onEdit != null) {
            SectionHeading("Meaning Graph") {
                if (onEdit != null) TextButton(onClick = onEdit) { Text(if (c.valueCards.isEmpty()) "+ Add values" else "Edit") }
            }
            if (c.valueCards.isNotEmpty()) ValueChips(c.valueCards, subjectLabel = "We care about")
            else MetaText("No value cards yet. Add the values this group holds itself to.", maxLines = 2)
        }
        if (c.values.isNotEmpty()) {
            SectionHeading("Values")
            FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                c.values.forEach { QuietPill(it) }
            }
        }
        if (data.alliances.isNotEmpty()) {
            SectionHeading("Alliances")
            data.alliances.forEach { ref ->
                GroupRow(CommunityKind.Alliance, ref.name ?: "Alliance") { navigator.community(CommunityKind.Alliance, ref.id) }
            }
        }
        val projects = data.projects.filter { it.id.isNotEmpty() }
        if (projects.isNotEmpty()) {
            SectionHeading("Projects")
            projects.forEach { ref ->
                GroupRow(CommunityKind.Project, ref.name ?: "Project") { navigator.community(CommunityKind.Project, ref.id) }
            }
        }
        if (onEdit == null && c.valueCards.isEmpty() && c.values.isEmpty() && data.alliances.isEmpty() && projects.isEmpty()) {
            EmptyNote("No charter written yet.")
        }
    }
}

@Composable
private fun GroupRow(kind: CommunityKind, name: String, onClick: () -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        GroupAvatar(kind, size = 32.dp)
        Spacer(Modifier.width(12.dp))
        Text(name, style = MaterialTheme.typography.titleSmall, modifier = Modifier.weight(1f))
        Text("→", color = MaterialTheme.colorScheme.tertiary)
    }
}
