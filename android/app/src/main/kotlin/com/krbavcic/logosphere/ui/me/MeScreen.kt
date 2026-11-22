package com.krbavcic.logosphere.ui.me

import androidx.compose.foundation.clickable
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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.HelpOutline
import androidx.compose.material.icons.automirrored.outlined.Logout
import androidx.compose.foundation.selection.selectable
import androidx.compose.material.icons.outlined.AdminPanelSettings
import androidx.compose.material.icons.outlined.DarkMode
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material3.RadioButton
import androidx.compose.ui.semantics.Role
import com.krbavcic.logosphere.data.ThemeChoice
import androidx.compose.material.icons.outlined.Favorite
import androidx.compose.material.icons.outlined.Gavel
import androidx.compose.material.icons.outlined.Handshake
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material.icons.outlined.Language
import androidx.compose.material.icons.outlined.Hub
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material.icons.outlined.PrivacyTip
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.ListItem
import androidx.compose.material3.ListItemDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.krbavcic.logosphere.AppContainer
import com.krbavcic.logosphere.BuildConfig
import com.krbavcic.logosphere.core.logic.InfoPage
import com.krbavcic.logosphere.core.logic.Membership
import com.krbavcic.logosphere.core.model.Community
import com.krbavcic.logosphere.core.model.OwnProfile
import com.krbavcic.logosphere.core.model.ValueCard
import com.krbavcic.logosphere.data.Change
import com.krbavcic.logosphere.ui.LoadViewModel
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.common.Avatar
import com.krbavcic.logosphere.ui.common.EmptyNote
import com.krbavcic.logosphere.ui.common.GroupAvatar
import com.krbavcic.logosphere.ui.common.LoadContent
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.QuietPill
import com.krbavcic.logosphere.ui.common.Refreshable
import com.krbavcic.logosphere.ui.common.ScreenPadding
import com.krbavcic.logosphere.ui.common.SectionHeading
import com.krbavcic.logosphere.ui.common.SnackbarMessages
import com.krbavcic.logosphere.ui.values.FranklLegend
import com.krbavcic.logosphere.ui.values.ValueCardActions
import com.krbavcic.logosphere.ui.values.ValueCardItem
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope

data class MeData(val profile: OwnProfile?, val cards: List<ValueCard>, val communities: List<Community>)

class MeViewModel(private val app: AppContainer) : LoadViewModel<MeData>() {
    init {
        load()
        reloadOn(app.changes, Change.Communities, Change.ValueCards, Change.Profile)
    }

    override suspend fun fetch(force: Boolean): MeData = coroutineScope {
        val me = app.session.user?.id
        val profile = async { runCatching { app.api.ownProfile() }.getOrNull() }
        val cards = async { me?.let { app.api.valueCards(it) }.orEmpty() }
        val communities = async { runCatching { app.communities.all(force) }.getOrDefault(emptyList()) }
        MeData(profile.await(), cards.await(), communities.await().filter { Membership.isMember(it, me) })
    }

    private fun replace(card: ValueCard) = update { data -> data.copy(cards = data.cards.map { if (it.id == card.id) card else it }) }

    fun endorse(card: ValueCard) = card.id?.let { id -> act { replace(app.api.endorseValueCard(null, id)) } }

    fun review(card: ValueCard) = card.id?.let { id -> act { replace(app.api.reviewValueCard(null, id)) } }

    fun delete(card: ValueCard) = card.id?.let { id ->
        act(onSuccess = { say("The card was removed.") }) {
            app.api.deleteValueCard(null, id)
            update { data -> data.copy(cards = data.cards.filter { it.id != id }) }
        }
    }

    fun signOut() = app.session.signOut()
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MeScreen() {
    val app = LocalAppContainer.current
    val vm: MeViewModel = viewModel { MeViewModel(app) }
    val navigator = LocalNavigator.current
    val state by vm.state.collectAsStateWithLifecycle()
    val refreshing by vm.refreshing.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    val user = app.session.user
    var confirmSignOut by rememberSaveable { mutableStateOf(false) }
    var showLicences by rememberSaveable { mutableStateOf(false) }
    var showAppearance by rememberSaveable { mutableStateOf(false) }
    val theme by app.appearance.choice.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    SnackbarMessages(vm.messages, snackbar)
    val actions = remember(vm) {
        ValueCardActions(
            onEdit = { navigator.valueCardEditor(cardId = it.id) },
            onDelete = { vm.delete(it) },
            onEndorse = { vm.endorse(it) },
            onReview = { vm.review(it) },
        )
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Me", style = MaterialTheme.typography.headlineSmall) },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background),
            )
        },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        LoadContent(state, onRetry = vm::load, modifier = Modifier.padding(padding)) { data ->
            Refreshable(refreshing, vm::refresh, Modifier.padding(padding)) {
                LazyColumn(contentPadding = PaddingValues(bottom = 32.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    item(key = "head") {
                        Column(Modifier.padding(horizontal = ScreenPadding, vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Avatar(user?.id, user?.name, size = 72.dp)
                                Spacer(Modifier.width(16.dp))
                                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                    Text(data.profile?.displayName ?: user?.name.orEmpty(), style = MaterialTheme.typography.headlineSmall)
                                    data.profile?.location?.takeIf { it.isNotBlank() }?.let { MetaText("📍 $it") }
                                    if (user?.isPlatformAdmin == true) QuietPill("Platform admin")
                                }
                            }
                            OutlinedButton(onClick = navigator::editProfile, modifier = Modifier.fillMaxWidth()) { Text("Edit profile") }
                        }
                    }
                    item(key = "values-head") {
                        Column(Modifier.padding(horizontal = ScreenPadding, vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            SectionHeading("Your Meaning Graph") {
                                if (data.cards.isNotEmpty()) TextButton(onClick = { navigator.valueCardEditor() }) { Text("+ Add card") }
                            }
                            MetaText("What you care about and why, in a form that can't easily be optimised away.", maxLines = 2)
                        }
                    }
                    if (data.cards.isEmpty()) {
                        item(key = "values-empty") {
                            Column(Modifier.padding(horizontal = ScreenPadding), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                Text(
                                    "No value cards yet. A value card captures one thing you genuinely care about — not a hashtag, " +
                                        "but a reason, a behaviour, and a drift signal. Start with one value you'd recognise yourself by.",
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                                Button(onClick = { navigator.valueCardEditor() }) { Text("Write your first card") }
                            }
                        }
                    }
                    items(data.cards, key = { "card-" + it.id }) { card ->
                        ValueCardItem(card, "I care about", actions, busy, Modifier.padding(horizontal = ScreenPadding))
                    }
                    item(key = "whole-graph") {
                        LinkRow(
                            Icons.Outlined.Hub,
                            "The whole Meaning Graph",
                            "Where your values sit among everyone's, and why",
                        ) { navigator.meaningGraph() }
                    }
                    if (data.cards.isNotEmpty()) {
                        item(key = "legend") { FranklLegend(Modifier.padding(horizontal = ScreenPadding, vertical = 4.dp)) }
                    }
                    item(key = "communities-head") {
                        SectionHeading("Your communities", Modifier.padding(horizontal = ScreenPadding, vertical = 8.dp))
                    }
                    if (data.communities.isEmpty()) {
                        item { EmptyNote("You haven't joined a sphere, alliance or project yet.") }
                    }
                    items(data.communities, key = { it.kind.name + it.id }) { c ->
                        ListItem(
                            headlineContent = { Text(c.name, style = MaterialTheme.typography.titleSmall) },
                            supportingContent = {
                                val role = Membership.role(c, user?.id)?.let { com.krbavcic.logosphere.core.logic.Roles.label(c.kind, it) }
                                Text(listOfNotNull(c.kind.noun, role).joinToString(" · "))
                            },
                            leadingContent = { GroupAvatar(c.kind, size = 36.dp) },
                            colors = ListItemDefaults.colors(containerColor = MaterialTheme.colorScheme.background),
                            modifier = Modifier.clickable { navigator.community(c.kind, c.id) },
                        )
                    }
                    item(key = "links") {
                        Column {
                            HorizontalDivider(Modifier.padding(vertical = 8.dp), color = MaterialTheme.colorScheme.outlineVariant)
                            user?.id?.let { id ->
                                LinkRow(Icons.Outlined.Person, "Your public profile") { navigator.person(id) }
                            }
                            if (user?.isPlatformAdmin == true) {
                                LinkRow(Icons.Outlined.AdminPanelSettings, "Platform administration") { navigator.admin() }
                            }
                            LinkRow(Icons.Outlined.DarkMode, "Appearance", theme.label) { showAppearance = true }
                            LinkRow(Icons.Outlined.Lock, "Password, data & account") { navigator.account() }
                            LinkRow(Icons.Outlined.Language, InfoPage.About.title) { navigator.info(InfoPage.About) }
                            LinkRow(Icons.AutoMirrored.Outlined.HelpOutline, InfoPage.HowItWorks.title) { navigator.info(InfoPage.HowItWorks) }
                            LinkRow(Icons.Outlined.Handshake, InfoPage.Contribute.title) { navigator.info(InfoPage.Contribute) }
                            LinkRow(Icons.Outlined.Favorite, InfoPage.Donate.title) { navigator.info(InfoPage.Donate) }
                            LinkRow(Icons.Outlined.PrivacyTip, InfoPage.Privacy.title) { navigator.info(InfoPage.Privacy) }
                            LinkRow(Icons.Outlined.Gavel, InfoPage.Terms.title) { navigator.info(InfoPage.Terms) }
                            LinkRow(Icons.Outlined.Info, "Fonts & licences") { showLicences = true }
                            LinkRow(Icons.AutoMirrored.Outlined.Logout, "Sign out") { confirmSignOut = true }
                            MetaText(
                                "LogoSphere ${BuildConfig.VERSION_NAME}" + if (BuildConfig.DEBUG) " (debug) · ${app.session.server}" else "",
                                modifier = Modifier.padding(horizontal = ScreenPadding, vertical = 16.dp),
                            )
                        }
                    }
                }
            }
        }
    }

    if (confirmSignOut) {
        AlertDialog(
            onDismissRequest = { confirmSignOut = false },
            title = { Text("Sign out?") },
            text = { Text("You'll need your email and password to sign in again.") },
            confirmButton = { TextButton(onClick = { confirmSignOut = false; vm.signOut() }) { Text("Sign out") } },
            dismissButton = { TextButton(onClick = { confirmSignOut = false }) { Text("Stay") } },
        )
    }
    if (showAppearance) {
        AlertDialog(
            onDismissRequest = { showAppearance = false },
            title = { Text("Appearance") },
            text = {
                Column {
                    ThemeChoice.entries.forEach { choice ->
                        Row(
                            Modifier
                                .fillMaxWidth()
                                .selectable(selected = theme == choice, role = Role.RadioButton) {
                                    app.appearance.choose(choice)
                                    showAppearance = false
                                }
                                .padding(vertical = 10.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            RadioButton(selected = theme == choice, onClick = null)
                            Spacer(Modifier.width(12.dp))
                            Text(choice.label, style = MaterialTheme.typography.bodyLarge)
                        }
                    }
                }
            },
            confirmButton = { TextButton(onClick = { showAppearance = false }) { Text("Close") } },
        )
    }
    if (showLicences) {
        AlertDialog(
            onDismissRequest = { showLicences = false },
            title = { Text("Fonts & licences") },
            text = {
                Text(
                    "Fraunces — © 2018 The Fraunces Project Authors.\n" +
                        "Hanken Grotesk — © 2021 The Hanken Grotesk Project Authors.\n\n" +
                        "Both are licensed under the SIL Open Font License 1.1; the full texts ship with the app " +
                        "(assets/licenses).",
                )
            },
            confirmButton = { TextButton(onClick = { showLicences = false }) { Text("Close") } },
        )
    }
}

@Composable
private fun LinkRow(icon: ImageVector, label: String, detail: String? = null, onClick: () -> Unit) {
    ListItem(
        headlineContent = { Text(label) },
        supportingContent = detail?.let { { Text(it) } },
        leadingContent = { Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant) },
        colors = ListItemDefaults.colors(containerColor = MaterialTheme.colorScheme.background),
        modifier = Modifier.clickable(onClick = onClick),
    )
}
