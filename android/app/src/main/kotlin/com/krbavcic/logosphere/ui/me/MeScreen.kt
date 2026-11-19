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
import androidx.compose.material.icons.automirrored.outlined.Logout
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material.icons.outlined.Language
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material.icons.outlined.Tune
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.ListItem
import androidx.compose.material3.ListItemDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
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
import com.krbavcic.logosphere.core.logic.Membership
import com.krbavcic.logosphere.core.model.Community
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
import com.krbavcic.logosphere.ui.common.ValueChips
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope

data class MeData(val cards: List<ValueCard>, val communities: List<Community>)

class MeViewModel(private val app: AppContainer) : LoadViewModel<MeData>() {
    init {
        load()
        reloadOn(app.changes, Change.Communities)
    }

    override suspend fun fetch(force: Boolean): MeData = coroutineScope {
        val me = app.session.user?.id
        val cards = async { me?.let { app.api.valueCards(it) }.orEmpty() }
        val communities = async { runCatching { app.communities.all(force) }.getOrDefault(emptyList()) }
        MeData(cards.await(), communities.await().filter { Membership.isMember(it, me) })
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
    val user = app.session.user
    var confirmSignOut by rememberSaveable { mutableStateOf(false) }
    var showLicences by rememberSaveable { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Me", style = MaterialTheme.typography.headlineSmall) },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background),
            )
        },
    ) { padding ->
        LoadContent(state, onRetry = vm::load, modifier = Modifier.padding(padding)) { data ->
            Refreshable(refreshing, vm::refresh, Modifier.padding(padding)) {
                LazyColumn(contentPadding = PaddingValues(bottom = 32.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    item(key = "head") {
                        Row(Modifier.padding(horizontal = ScreenPadding, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
                            Avatar(user?.id, user?.name, size = 64.dp)
                            Spacer(Modifier.width(16.dp))
                            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                Text(user?.name ?: "", style = MaterialTheme.typography.headlineSmall)
                                if (user?.isPlatformAdmin == true) QuietPill("Platform admin")
                            }
                        }
                    }
                    item(key = "values") {
                        Column(Modifier.padding(horizontal = ScreenPadding, vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            SectionHeading("Your values") {
                                TextButton(onClick = { navigator.web("/profile") }) { Text("Edit on the web") }
                            }
                            if (data.cards.isEmpty()) {
                                MetaText("No value cards yet. A value card says what you care about, and why.", maxLines = 2)
                            } else {
                                ValueChips(data.cards)
                            }
                        }
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
                                val role = Membership.role(c, user?.id)?.replaceFirstChar { it.uppercase() }
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
                            LinkRow(Icons.Outlined.Tune, "Profile, values & settings on the web") { navigator.web("/settings") }
                            LinkRow(Icons.Outlined.Language, "About LogoSphere") { navigator.web("/about") }
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
private fun LinkRow(icon: ImageVector, label: String, onClick: () -> Unit) {
    ListItem(
        headlineContent = { Text(label) },
        leadingContent = { Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant) },
        colors = ListItemDefaults.colors(containerColor = MaterialTheme.colorScheme.background),
        modifier = Modifier.clickable(onClick = onClick),
    )
}
