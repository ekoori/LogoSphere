package com.krbavcic.logosphere.ui.admin

import android.content.Intent
import androidx.compose.foundation.clickable
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import kotlinx.coroutines.flow.MutableStateFlow
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Switch
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
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.krbavcic.logosphere.AppContainer
import com.krbavcic.logosphere.core.logic.Dates
import com.krbavcic.logosphere.core.logic.Policies
import com.krbavcic.logosphere.core.model.AdminGroup
import com.krbavcic.logosphere.core.model.AdminOpening
import com.krbavcic.logosphere.core.model.AdminOverview
import com.krbavcic.logosphere.core.model.AdminUser
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.data.Change
import com.krbavcic.logosphere.ui.LoadViewModel
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.common.BackTopBar
import com.krbavcic.logosphere.ui.common.BrandCard
import com.krbavcic.logosphere.ui.common.Choice
import com.krbavcic.logosphere.ui.common.DemoTag
import com.krbavcic.logosphere.ui.common.EmptyNote
import com.krbavcic.logosphere.ui.common.LoadContent
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.OpeningTypePill
import com.krbavcic.logosphere.ui.common.PersonaTag
import com.krbavcic.logosphere.ui.common.Picker
import com.krbavcic.logosphere.ui.common.QuietPill
import com.krbavcic.logosphere.ui.common.Refreshable
import com.krbavcic.logosphere.ui.common.ScreenPadding
import com.krbavcic.logosphere.ui.common.ScrollingTabs
import com.krbavcic.logosphere.ui.common.SectionHeading
import com.krbavcic.logosphere.ui.common.SnackbarMessages

// ── View models: one per tab, each a list and its actions ──────────────────

class AdminOverviewViewModel(private val app: AppContainer) : LoadViewModel<AdminOverview>() {
    init { load() }

    override suspend fun fetch(force: Boolean): AdminOverview = app.api.adminOverview()
}

class AdminUsersViewModel(private val app: AppContainer) : LoadViewModel<List<AdminUser>>() {
    init { load() }

    override suspend fun fetch(force: Boolean): List<AdminUser> = app.api.adminUsers()

    private fun run(done: String, block: suspend () -> Unit) = act(onSuccess = {
        say(done)
        reload()
    }, block = block)

    fun setAdmin(u: AdminUser, admin: Boolean) = run(
        if (admin) "${u.label} is now a platform administrator." else "${u.label} is no longer an administrator.",
    ) { app.api.adminSetUserFlags(u.id, isPlatformAdmin = admin) }

    fun setPersona(u: AdminUser, persona: Boolean) = run(
        if (persona) "${u.label} is now an AI persona." else "${u.label} is no longer an AI persona.",
    ) { app.api.adminSetUserFlags(u.id, isAgent = persona) }

    fun edit(u: AdminUser, name: String, surname: String, location: String) = run("Profile updated.") {
        app.api.adminEditUser(u.id, name, surname, location)
    }

    fun delete(u: AdminUser) = run("Deleted ${u.label}'s account.") { app.api.adminDeleteUser(u.id) }

    /** The last reset link made here: whose, and the whole address to pass on. */
    val resetLink = MutableStateFlow<Pair<AdminUser, String>?>(null)

    fun makeResetLink(u: AdminUser) = act {
        val link = app.api.adminResetLink(u.id)
        resetLink.value = u to app.api.webUrl(link.path)
    }
}

class AdminGroupsViewModel(private val app: AppContainer, private val kind: CommunityKind) : LoadViewModel<List<AdminGroup>>() {
    init { load() }

    override suspend fun fetch(force: Boolean): List<AdminGroup> = app.api.adminGroups(kind)

    private fun run(done: String, block: suspend () -> Unit) = act(onSuccess = {
        app.communities.invalidate(kind)
        app.changes.emit(Change.Communities)
        say(done)
        reload()
    }, block = block)

    fun setPolicy(g: AdminGroup, key: String, value: String) = run("${g.name}: ${key.replace('_', ' ')} set to ${Policies.valueLabel(value).lowercase()}.") {
        app.api.updateCommunity(kind, g.id, mapOf(key to value))
    }

    fun setPublic(g: AdminGroup, on: Boolean) = run("${g.name} is ${if (on) "now" else "no longer"} public.") { app.api.setSphereFlags(g.id, isPublic = on) }

    fun setSandbox(g: AdminGroup, on: Boolean) = run("${g.name} is ${if (on) "now" else "no longer"} a sandbox.") { app.api.setSphereFlags(g.id, isSandbox = on) }

    fun setDemo(g: AdminGroup, on: Boolean) = run("${g.name} is ${if (on) "now" else "no longer"} a demo sphere.") { app.api.adminSetDemo(g.id, on) }

    fun edit(g: AdminGroup, name: String, description: String) = run("$name updated.") {
        app.api.updateCommunity(kind, g.id, mapOf("name" to name.trim(), "description" to description.trim()))
    }

    fun delete(g: AdminGroup) = run("Deleted ${g.name}.") { app.api.adminDeleteGroup(kind, g.id) }
}

class AdminOpeningsViewModel(private val app: AppContainer) : LoadViewModel<List<AdminOpening>>() {
    init { load() }

    override suspend fun fetch(force: Boolean): List<AdminOpening> = app.api.adminOpenings()

    private fun run(done: String, block: suspend () -> Unit) = act(onSuccess = {
        app.openings.invalidate()
        app.changes.emit(Change.Openings)
        say(done)
        reload()
    }, block = block)

    fun withdraw(o: AdminOpening) = run("Withdrew “${o.title}”.") { app.api.withdrawOpening(o.id) }

    fun delete(o: AdminOpening) = run("Deleted “${o.title}”.") { app.api.adminDeleteOpening(o.id) }
}

// ── The console ─────────────────────────────────────────────────────────────

private val TABS = listOf("Overview", "Users", "Spheres", "Alliances", "Projects", "Openings", "Reports")

/** Platform administration (the web's AdminPage): everything on the platform, in one place. */
@Composable
fun AdminScreen() {
    val app = LocalAppContainer.current
    val navigator = LocalNavigator.current
    val snackbar = remember { SnackbarHostState() }
    var tab by rememberSaveable { mutableIntStateOf(0) }
    Scaffold(
        topBar = { BackTopBar("Platform administration", navigator::back) },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        Column(Modifier.padding(padding).fillMaxSize()) {
            if (app.session.user?.isPlatformAdmin != true) {
                EmptyNote("This page is for platform administrators only.")
                return@Column
            }
            ScrollingTabs(TABS, tab, { tab = it }, Modifier.padding(horizontal = ScreenPadding, vertical = 8.dp))
            when (tab) {
                0 -> OverviewTab()
                1 -> UsersTab(snackbar)
                2 -> GroupsTab(CommunityKind.Sphere, snackbar)
                3 -> GroupsTab(CommunityKind.Alliance, snackbar)
                4 -> GroupsTab(CommunityKind.Project, snackbar)
                5 -> OpeningsTab(snackbar)
                else -> ReportsTab(snackbar)
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun OverviewTab() {
    val app = LocalAppContainer.current
    val navigator = LocalNavigator.current
    val vm: AdminOverviewViewModel = viewModel { AdminOverviewViewModel(app) }
    val state by vm.state.collectAsStateWithLifecycle()
    val refreshing by vm.refreshing.collectAsStateWithLifecycle()
    LoadContent(state, onRetry = vm::load) { data ->
        val c = data.counts
        Refreshable(refreshing, vm::refresh) {
            LazyColumn(contentPadding = PaddingValues(start = ScreenPadding, end = ScreenPadding, bottom = 32.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                item {
                    FlowRow(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalArrangement = Arrangement.spacedBy(10.dp), maxItemsInEachRow = 2) {
                        Stat("Users", c.users, "${c.platformAdmins} platform admin${if (c.platformAdmins == 1) "" else "s"}", Modifier.weight(1f).fillMaxRowHeight())
                        Stat("Spheres", c.spheres, "${c.publicSpheres} public · ${c.sandboxSpheres} sandbox", Modifier.weight(1f).fillMaxRowHeight())
                        Stat("Alliances", c.alliances, null, Modifier.weight(1f).fillMaxRowHeight())
                        Stat("Projects", c.projects, null, Modifier.weight(1f).fillMaxRowHeight())
                        Stat("Openings", c.openings, "${c.openingsOpen} open now", Modifier.weight(1f).fillMaxRowHeight())
                        Stat("Exchanges", c.exchanges, null, Modifier.weight(1f).fillMaxRowHeight())
                    }
                }
                item { SectionHeading("Platform administrators") }
                items(data.platformAdmins, key = { it.id }) { a ->
                    Column(Modifier.fillMaxWidth().clickable { navigator.person(a.id) }.padding(vertical = 4.dp)) {
                        Text(a.name ?: "Member", style = MaterialTheme.typography.titleSmall)
                        a.email?.let { MetaText(it) }
                    }
                }
                item {
                    MetaText(
                        "Grant or revoke the flag from the Users tab. There must always be at least one administrator, and nobody can change their own flag.",
                        maxLines = 4,
                    )
                }
            }
        }
    }
}

@Composable
private fun Stat(label: String, n: Int, sub: String?, modifier: Modifier = Modifier) {
    BrandCard(modifier) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(n.toString(), style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.primary)
            Text(label, style = MaterialTheme.typography.titleSmall)
            sub?.let { MetaText(it, maxLines = 2) }
        }
    }
}

/** Filter box and "shown of all", above each list. */
@Composable
private fun FilterRow(filter: String, onFilter: (String) -> Unit, placeholder: String, shown: Int, all: Int, trailing: @Composable () -> Unit = {}) {
    Column(Modifier.padding(horizontal = ScreenPadding), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        OutlinedTextField(
            value = filter,
            onValueChange = onFilter,
            placeholder = { Text(placeholder) },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Row(verticalAlignment = Alignment.CenterVertically) {
            MetaText("$shown of $all", Modifier.weight(1f))
            trailing()
        }
    }
}

private fun matches(needle: String, vararg hay: String?): Boolean {
    val n = needle.trim().lowercase()
    return n.isEmpty() || hay.any { it?.lowercase()?.contains(n) == true }
}

/** A destructive or weighty action, asked about first. */
private data class Ask(val title: String, val text: String, val confirm: String, val run: () -> Unit)

@Composable
private fun AskDialog(ask: Ask?, onDismiss: () -> Unit) {
    if (ask == null) return
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(ask.title) },
        text = { Text(ask.text) },
        confirmButton = { TextButton(onClick = { onDismiss(); ask.run() }) { Text(ask.confirm) } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    )
}

@Composable
private fun UsersTab(snackbar: SnackbarHostState) {
    val app = LocalAppContainer.current
    val navigator = LocalNavigator.current
    val vm: AdminUsersViewModel = viewModel { AdminUsersViewModel(app) }
    val state by vm.state.collectAsStateWithLifecycle()
    val refreshing by vm.refreshing.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    SnackbarMessages(vm.messages, snackbar)
    var filter by rememberSaveable { mutableStateOf("") }
    var ask by remember { mutableStateOf<Ask?>(null) }
    var editing by remember { mutableStateOf<AdminUser?>(null) }

    LoadContent(state, onRetry = vm::load) { users ->
        val rows = users.filter { matches(filter, it.label, it.email, it.location) }
        Column {
            FilterRow(filter, { filter = it }, "Filter by name, email or location…", rows.size, users.size)
            Refreshable(refreshing, vm::refresh) {
                LazyColumn(contentPadding = PaddingValues(start = ScreenPadding, end = ScreenPadding, top = 8.dp, bottom = 32.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    items(rows, key = { it.id }) { u ->
                        RowCard(
                            onOpen = { navigator.person(u.id) },
                            title = u.label,
                            tags = {
                                if (u.isYou) QuietPill("you")
                                if (u.isPlatformAdmin) QuietPill("admin")
                                if (u.isAgent) PersonaTag(compact = true)
                            },
                            lines = listOfNotNull(
                                u.email,
                                listOfNotNull(
                                    Dates.day(u.joinedAt).takeIf { it.isNotEmpty() }?.let { "Joined $it" },
                                    "${u.sphereCount} sphere${if (u.sphereCount == 1) "" else "s"}",
                                    "${u.cardCount} card${if (u.cardCount == 1) "" else "s"}",
                                ).joinToString(" · "),
                            ),
                            busy = busy,
                            menu = buildList {
                                add("Edit profile" to { editing = u })
                                add("Password reset link" to {
                                    ask = Ask(
                                        "Make a password reset link for ${u.label}?",
                                        "For when they've forgotten their password. The link works once, for 24 hours, and signs them out everywhere when used. You pass it on to them yourself.",
                                        "Make link",
                                    ) { vm.makeResetLink(u) }
                                })
                                if (!u.isYou) {
                                    add(
                                        (if (u.isPlatformAdmin) "Revoke admin" else "Make admin") to {
                                            ask = Ask(
                                                if (u.isPlatformAdmin) "Revoke ${u.label}'s administrator flag?" else "Make ${u.label} a platform administrator?",
                                                if (u.isPlatformAdmin) "They lose the admin console and the override on every group." else "They can manage everything on the platform, including this console.",
                                                if (u.isPlatformAdmin) "Revoke" else "Make admin",
                                            ) { vm.setAdmin(u, !u.isPlatformAdmin) }
                                        },
                                    )
                                }
                                if (!u.isYou && !u.isPlatformAdmin) {
                                    add(
                                        (if (u.isAgent) "Make a person" else "Make AI persona") to {
                                            ask = Ask(
                                                if (u.isAgent) "Mark ${u.label} as a real person?" else "Mark ${u.label} as an AI persona?",
                                                if (u.isAgent) "The AI persona label comes off everywhere they appear." else "They're labelled an AI persona everywhere they appear.",
                                                "Confirm",
                                            ) { vm.setPersona(u, !u.isAgent) }
                                        },
                                    )
                                    add(
                                        "Delete account" to {
                                            ask = Ask("Delete ${u.label}'s account?", "This removes the account for good.", "Delete") { vm.delete(u) }
                                        },
                                    )
                                }
                            },
                        )
                    }
                }
            }
        }
    }
    AskDialog(ask) { ask = null }
    val link by vm.resetLink.collectAsStateWithLifecycle()
    link?.let { (u, url) -> ResetLinkDialog(u.label, url) { vm.resetLink.value = null } }
    editing?.let { u ->
        var name by remember(u.id) { mutableStateOf(u.name.orEmpty()) }
        var surname by remember(u.id) { mutableStateOf(u.surname.orEmpty()) }
        var location by remember(u.id) { mutableStateOf(u.location.orEmpty()) }
        AlertDialog(
            onDismissRequest = { editing = null },
            title = { Text("Edit ${u.label}") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    DialogField(name, { name = it }, "Name")
                    DialogField(surname, { surname = it }, "Surname")
                    DialogField(location, { location = it }, "Location")
                }
            },
            confirmButton = {
                TextButton(onClick = { editing = null; vm.edit(u, name, surname, location) }, enabled = name.isNotBlank()) { Text("Save") }
            },
            dismissButton = { TextButton(onClick = { editing = null }) { Text("Cancel") } },
        )
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun GroupsTab(kind: CommunityKind, snackbar: SnackbarHostState) {
    val app = LocalAppContainer.current
    val navigator = LocalNavigator.current
    val vm: AdminGroupsViewModel = viewModel(key = "admin-groups-$kind") { AdminGroupsViewModel(app, kind) }
    val state by vm.state.collectAsStateWithLifecycle()
    val refreshing by vm.refreshing.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    SnackbarMessages(vm.messages, snackbar)
    var filter by rememberSaveable(kind) { mutableStateOf("") }
    var ask by remember { mutableStateOf<Ask?>(null) }
    var editing by remember { mutableStateOf<AdminGroup?>(null) }

    LoadContent(state, onRetry = vm::load) { groups ->
        val rows = groups.filter { matches(filter, it.name, it.description, it.sphereName, it.ownerAlliance, it.ownerName) }
        Column {
            FilterRow(filter, { filter = it }, "Filter ${kind.plural.lowercase()}…", rows.size, groups.size)
            Refreshable(refreshing, vm::refresh) {
                LazyColumn(contentPadding = PaddingValues(start = ScreenPadding, end = ScreenPadding, top = 8.dp, bottom = 32.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    items(rows, key = { it.id }) { g ->
                        RowCard(
                            onOpen = { navigator.community(kind, g.id) },
                            title = g.name,
                            tags = {
                                if (g.pendingCount > 0) QuietPill("${g.pendingCount} pending")
                                if (g.isDemo) DemoTag()
                            },
                            lines = listOfNotNull(
                                g.sphereName?.takeIf { kind != CommunityKind.Sphere }?.let { "✦ $it" },
                                (g.ownerAlliance ?: g.ownerName)?.takeIf { kind == CommunityKind.Project }?.let { "Run by $it" },
                                listOfNotNull(
                                    "${g.memberCount} member${if (g.memberCount == 1) "" else "s"}",
                                    if (kind == CommunityKind.Sphere) "${g.allianceCount} alliance${if (g.allianceCount == 1) "" else "s"} · ${g.projectCount} project${if (g.projectCount == 1) "" else "s"}" else null,
                                    "${g.cardCount} card${if (g.cardCount == 1) "" else "s"}",
                                ).joinToString(" · "),
                            ),
                            busy = busy,
                            menu = listOf(
                                "Edit name & description" to { editing = g },
                                "Delete ${kind.noun.lowercase()}" to {
                                    ask = Ask("Delete ${g.name}?", "It's removed for good, with its membership. Its openings are withdrawn.", "Delete") { vm.delete(g) }
                                },
                            ),
                        ) {
                            Policies.fields(kind).forEach { field ->
                                Picker(
                                    label = field.label,
                                    choices = field.options.map { (value, _) -> Choice(value, Policies.valueLabel(value)) },
                                    selected = g.policy(field.key) ?: Policies.default(field.key),
                                    onSelect = { v -> if (v != null && v != (g.policy(field.key) ?: Policies.default(field.key))) vm.setPolicy(g, field.key, v) },
                                    enabled = !busy,
                                )
                            }
                            if (kind == CommunityKind.Sphere) {
                                Flag("Public", g.isPublic, busy) { vm.setPublic(g, it) }
                                Flag("Sandbox — new members join it", g.isSandbox, busy) { vm.setSandbox(g, it) }
                                Flag("Demo — its members are AI personas", g.isDemo, busy) { vm.setDemo(g, it) }
                            }
                        }
                    }
                }
            }
        }
    }
    AskDialog(ask) { ask = null }
    editing?.let { g ->
        var name by remember(g.id) { mutableStateOf(g.name) }
        var description by remember(g.id) { mutableStateOf(g.description.orEmpty()) }
        AlertDialog(
            onDismissRequest = { editing = null },
            title = { Text("Edit ${g.name}") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    DialogField(name, { name = it }, "Name")
                    DialogField(description, { description = it }, "Description", singleLine = false)
                }
            },
            confirmButton = {
                TextButton(onClick = { editing = null; vm.edit(g, name, description) }, enabled = name.isNotBlank()) { Text("Save") }
            },
            dismissButton = { TextButton(onClick = { editing = null }) { Text("Cancel") } },
        )
    }
}

@Composable
private fun OpeningsTab(snackbar: SnackbarHostState) {
    val app = LocalAppContainer.current
    val navigator = LocalNavigator.current
    val vm: AdminOpeningsViewModel = viewModel { AdminOpeningsViewModel(app) }
    val state by vm.state.collectAsStateWithLifecycle()
    val refreshing by vm.refreshing.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    SnackbarMessages(vm.messages, snackbar)
    var filter by rememberSaveable { mutableStateOf("") }
    var onlyOpen by rememberSaveable { mutableStateOf(true) }
    var ask by remember { mutableStateOf<Ask?>(null) }

    LoadContent(state, onRetry = vm::load) { openings ->
        val rows = openings.filter { !onlyOpen || it.isOpen }
            .filter { matches(filter, it.title, it.description, it.provider, it.spheres.firstOrNull(), it.projectName, it.status) }
        Column {
            FilterRow(filter, { filter = it }, "Filter by title, provider, sphere, status…", rows.size, openings.size) {
                MetaText("Open only")
                Switch(checked = onlyOpen, onCheckedChange = { onlyOpen = it }, modifier = Modifier.padding(start = 8.dp))
            }
            Refreshable(refreshing, vm::refresh) {
                LazyColumn(contentPadding = PaddingValues(start = ScreenPadding, end = ScreenPadding, top = 8.dp, bottom = 32.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    items(rows, key = { it.id }) { o ->
                        RowCard(
                            onOpen = { navigator.opening(o.id) },
                            title = o.title,
                            tags = { OpeningTypePill(o.isOffer) },
                            lines = listOf(
                                listOfNotNull(o.providerLabel, o.spheres.firstOrNull()).joinToString(" · "),
                                listOf(
                                    o.status,
                                    if (o.cadence == "perpetual") "ongoing" else "one-time",
                                    "v${o.version}",
                                    "${o.pendingCount} pending / ${o.confirmedCount} confirmed",
                                ).joinToString(" · "),
                            ),
                            busy = busy,
                            menu = buildList {
                                if (o.isOpen) {
                                    add("Withdraw" to {
                                        ask = Ask("Withdraw “${o.title}”?", "It leaves Openings for everyone, and anyone waiting on a confirmation is told.", "Withdraw") { vm.withdraw(o) }
                                    })
                                }
                                if (o.confirmedCount == 0) {
                                    add("Delete" to {
                                        ask = Ask("Delete “${o.title}”?", "It's removed for good. (One an exchange came from can only be withdrawn.)", "Delete") { vm.delete(o) }
                                    })
                                }
                            },
                        )
                    }
                }
            }
        }
    }
    AskDialog(ask) { ask = null }
}

/** One row of a console list: what it is, its facts, an actions menu and (optionally) inline controls. */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun RowCard(
    onOpen: () -> Unit,
    title: String,
    tags: @Composable () -> Unit,
    lines: List<String>,
    busy: Boolean,
    menu: List<Pair<String, () -> Unit>>,
    controls: (@Composable () -> Unit)? = null,
) {
    var open by remember { mutableStateOf(false) }
    BrandCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(start = 14.dp, top = 10.dp, bottom = 12.dp, end = 4.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f).clickable(onClick = onOpen), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(title, style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.primary)
                    FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) { tags() }
                }
                if (menu.isNotEmpty()) {
                    Box {
                        IconButton(onClick = { open = true }, enabled = !busy) { Icon(Icons.Filled.MoreVert, contentDescription = "Actions for $title") }
                        DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
                            menu.forEach { (label, action) ->
                                DropdownMenuItem(text = { Text(label) }, onClick = { open = false; action() })
                            }
                        }
                    }
                }
            }
            lines.filter { it.isNotBlank() }.forEach { MetaText(it, Modifier.padding(end = 10.dp), maxLines = 2) }
            if (controls != null) {
                Column(Modifier.padding(end = 10.dp, top = 4.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) { controls() }
            }
        }
    }
}

/** The link, to copy or send on; it isn't shown again once closed. */
@Composable
private fun ResetLinkDialog(who: String, url: String, onClose: () -> Unit) {
    val clipboard = LocalClipboardManager.current
    val context = LocalContext.current
    AlertDialog(
        onDismissRequest = onClose,
        title = { Text("Reset link for $who") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("Send it to them yourself — it works once, for the next 24 hours.", style = MaterialTheme.typography.bodyMedium)
                SelectionContainer {
                    Text(url, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.primary)
                }
            }
        },
        confirmButton = {
            TextButton(onClick = {
                val send = Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, url)
                context.startActivity(Intent.createChooser(send, "Send the reset link"))
            }) { Text("Share") }
        },
        dismissButton = {
            Row {
                TextButton(onClick = { clipboard.setText(AnnotatedString(url)) }) { Text("Copy") }
                TextButton(onClick = onClose) { Text("Close") }
            }
        },
    )
}

@Composable
private fun Flag(label: String, on: Boolean, busy: Boolean, onChange: (Boolean) -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text(label, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.weight(1f))
        Switch(checked = on, onCheckedChange = onChange, enabled = !busy)
    }
}

@Composable
private fun DialogField(value: String, onChange: (String) -> Unit, label: String, singleLine: Boolean = true) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        label = { Text(label) },
        singleLine = singleLine,
        keyboardOptions = KeyboardOptions(capitalization = if (singleLine) KeyboardCapitalization.Words else KeyboardCapitalization.Sentences),
        modifier = Modifier.fillMaxWidth().width(320.dp),
    )
}
