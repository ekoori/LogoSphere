package com.krbavcic.logosphere.ui.communities

import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateMapOf
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
import com.krbavcic.logosphere.core.logic.Membership
import com.krbavcic.logosphere.core.logic.Policies
import com.krbavcic.logosphere.core.logic.Roles
import com.krbavcic.logosphere.core.model.Community
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.ValueCard
import com.krbavcic.logosphere.data.Change
import com.krbavcic.logosphere.ui.LoadViewModel
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.common.BackTopBar
import com.krbavcic.logosphere.ui.common.BannerField
import com.krbavcic.logosphere.ui.common.Choice
import com.krbavcic.logosphere.ui.common.EmptyNote
import com.krbavcic.logosphere.ui.common.LoadContent
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.Picker
import com.krbavcic.logosphere.ui.common.PrimaryAction
import com.krbavcic.logosphere.ui.common.Refreshable
import com.krbavcic.logosphere.ui.common.ScreenPadding
import com.krbavcic.logosphere.ui.common.ScrollingTabs
import com.krbavcic.logosphere.ui.common.SnackbarMessages
import com.krbavcic.logosphere.ui.common.rememberPhotoTaker
import com.krbavcic.logosphere.ui.common.rememberPicturePicker
import com.krbavcic.logosphere.ui.values.ValueCardActions
import com.krbavcic.logosphere.ui.values.ValueCardItem
import com.krbavcic.logosphere.ui.common.LocalSimple
import com.krbavcic.logosphere.ui.common.MoreInAdvanced
import com.krbavcic.logosphere.ui.common.AiPictureButton

class ManageCommunityViewModel(
    private val app: AppContainer,
    private val kind: CommunityKind,
    private val id: String,
) : LoadViewModel<Community>() {
    val viewerId: String? get() = app.session.user?.id
    val isPlatformAdmin: Boolean get() = app.session.user?.isPlatformAdmin == true

    init {
        load()
        reloadOn(app.changes, Change.ValueCards, Change.Communities)
    }

    override suspend fun fetch(force: Boolean): Community = app.api.community(kind, id)

    private suspend fun changed() {
        app.communities.invalidate(kind)
        app.changes.emit(Change.Communities)
        reload()
    }

    /** [changes]: name, description and policies that differ; a sphere's flags only when they changed. */
    fun save(changes: Map<String, String>, isPublic: Boolean?, isSandbox: Boolean?) {
        if (changes["name"]?.isBlank() == true) {
            say("The name can't be empty.")
            return
        }
        if (changes.isEmpty() && isPublic == null && isSandbox == null) {
            say("Nothing has changed.")
            return
        }
        act(onSuccess = {
            changed()
            say("Saved.")
        }) {
            if (changes.isNotEmpty()) app.api.updateCommunity(kind, id, changes)
            if (kind == CommunityKind.Sphere && (isPublic != null || isSandbox != null)) app.api.setSphereFlags(id, isPublic, isSandbox)
        }
    }

    fun setPicture(uri: Uri) = act(onSuccess = {
        changed()
        say("The picture was updated.")
    }) {
        app.api.setCommunityImage(kind, id, app.pictures.read(uri))
        app.pictures.replaced(app.api.communityImageUrl(kind, id))
    }

    fun setRole(memberId: String, role: String) = act(onSuccess = { changed() }) { app.api.setMemberRole(kind, id, memberId, role) }

    private fun replace(card: ValueCard) = update { c -> c.copy(valueCards = c.valueCards.map { if (it.id == card.id) card else it }) }

    fun endorse(card: ValueCard) = card.id?.let { cardId -> act { replace(app.api.endorseValueCard(id, cardId)) } }

    fun review(card: ValueCard) = card.id?.let { cardId -> act { replace(app.api.reviewValueCard(id, cardId)) } }

    fun delete(card: ValueCard) = card.id?.let { cardId ->
        act(onSuccess = {
            app.communities.invalidate(kind)
            app.changes.emit(Change.Communities)
            say("The card was removed.")
        }) {
            app.api.deleteValueCard(id, cardId)
            update { c -> c.copy(valueCards = c.valueCards.filter { it.id != cardId }) }
        }
    }
}

/** A group's own console (the web's EntityManagement): settings, its Meaning Graph and its people. */
@Composable
fun ManageCommunityScreen(kind: CommunityKind, id: String) {
    val app = LocalAppContainer.current
    val vm: ManageCommunityViewModel = viewModel(key = "manage-$kind-$id") { ManageCommunityViewModel(app, kind, id) }
    val navigator = LocalNavigator.current
    val state by vm.state.collectAsStateWithLifecycle()
    val refreshing by vm.refreshing.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    SnackbarMessages(vm.messages, snackbar)
    var tab by rememberSaveable { mutableIntStateOf(0) }
    val pickPicture = rememberPicturePicker { vm.setPicture(it) }
    val takePicture = rememberPhotoTaker { vm.setPicture(it) }

    Scaffold(
        topBar = { BackTopBar("Manage ${kind.noun.lowercase()}", navigator::back) },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        LoadContent(state, onRetry = vm::load, modifier = Modifier.padding(padding)) { c ->
            val me = vm.viewerId
            val canManage = Membership.canManage(c, me, vm.isPlatformAdmin)
            val canSetRoles = Membership.canSetRoles(c, me, vm.isPlatformAdmin)
            val actions = remember(vm, c.id) {
                ValueCardActions(
                    onEdit = { navigator.valueCardEditor(c, it.id) },
                    onDelete = { vm.delete(it) },
                    onEndorse = { vm.endorse(it) },
                    onReview = { vm.review(it) },
                )
            }
            val simple = LocalSimple.current
            Refreshable(refreshing, vm::refresh, Modifier.padding(padding).imePadding()) {
                LazyColumn(contentPadding = PaddingValues(bottom = 40.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    item(key = "head") {
                        Column(Modifier.padding(horizontal = ScreenPadding, vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text(c.name, style = MaterialTheme.typography.headlineSmall)
                            if (vm.isPlatformAdmin && !Membership.managesItself(c, me)) MetaText("You're managing this as a platform admin.", maxLines = 2)
                        }
                    }
                    if (!canManage) {
                        item { EmptyNote("Only ${Roles.managerWord(kind)} can manage this ${kind.noun.lowercase()}.") }
                        return@LazyColumn
                    }
                    item(key = "banner") {
                        BannerField(
                            picked = null,
                            currentUrl = if (c.hasImage) app.api.communityImageUrl(kind, c.id) else null,
                            kind = kind,
                            onPick = { if (!busy) pickPicture() },
                            onTake = takePicture?.let { take -> { if (!busy) take() } },
                            isAi = c.imageIsAi,
                            modifier = Modifier.padding(horizontal = ScreenPadding),
                        )
                    }
                    item(key = "banner-ai") {
                        AiPictureButton(
                            purpose = kind.name.lowercase(),
                            title = c.name,
                            description = c.description.orEmpty(),
                            onUse = { if (!busy) vm.setPicture(it) },
                            modifier = Modifier.padding(horizontal = ScreenPadding),
                        )
                    }
                    item(key = "tabs") {
                        ScrollingTabs(listOf("Settings", if (simple) "Values" else "Meaning Graph", Roles.peopleWord(kind)), tab, { tab = it }, Modifier.padding(horizontal = ScreenPadding))
                    }
                    when (tab) {
                        0 -> item(key = "settings") {
                            SettingsForm(c, vm.isPlatformAdmin, busy, onSave = vm::save, modifier = Modifier.padding(horizontal = ScreenPadding))
                        }
                        1 -> {
                            item(key = "graph-intro") {
                                Column(Modifier.padding(horizontal = ScreenPadding), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                    MetaText(
                                        if (simple) "What this ${kind.noun.lowercase()} cares about, for everyone to see."
                                        else "The values this ${kind.noun.lowercase()} holds itself to — what it cares about, why, and what drift looks like.",
                                        maxLines = 3,
                                    )
                                    Button(onClick = { navigator.valueCardEditor(c) }) { Text(if (simple) "+ Add a value card" else "+ Add to Meaning Graph") }
                                }
                            }
                            if (c.valueCards.isEmpty()) item { EmptyNote("No value cards yet. Add the values this group holds itself to.") }
                            items(c.valueCards, key = { "card-" + it.id }) { card ->
                                ValueCardItem(card, "We care about", actions, busy, Modifier.padding(horizontal = ScreenPadding))
                            }
                        }
                        else -> memberItems(c, me, canSetRoles, busy, onSetRole = vm::setRole, onOpen = navigator::person)
                    }
                }
            }
        }
    }
}

@Composable
private fun SettingsForm(
    c: Community,
    isPlatformAdmin: Boolean,
    busy: Boolean,
    onSave: (Map<String, String>, Boolean?, Boolean?) -> Unit,
    modifier: Modifier = Modifier,
) {
    var name by rememberSaveable(c.id) { mutableStateOf(c.name) }
    var description by rememberSaveable(c.id) { mutableStateOf(c.description.orEmpty()) }
    val fields = Policies.fields(c.kind)
    val values = remember(c.id) { mutableStateMapOf<String, String>().apply { fields.forEach { put(it.key, Policies.valueOf(c, it.key)) } } }
    var isPublic by rememberSaveable(c.id) { mutableStateOf(c.isPublic) }
    var isSandbox by rememberSaveable(c.id) { mutableStateOf(c.isSandbox) }
    val simple = LocalSimple.current

    Column(modifier, verticalArrangement = Arrangement.spacedBy(14.dp)) {
        OutlinedTextField(
            value = name,
            onValueChange = { name = it },
            label = { Text("Name") },
            singleLine = true,
            keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Words),
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = description,
            onValueChange = { description = it },
            label = { Text("Description") },
            keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences),
            modifier = Modifier.fillMaxWidth().heightIn(min = 110.dp),
        )
        // Hidden isn't cleared: only what changed is sent.
        fields.filter { !simple || it.key == "phase" }.forEach { field ->
            Picker(
                label = field.label,
                choices = field.options.map { (value, label) ->
                    Choice(value, if (value == "approval") "Approval required — ${Roles.managerWord(c.kind)} must approve" else label)
                },
                selected = values[field.key],
                onSelect = { v -> v?.let { values[field.key] = it } },
            )
        }
        if (!simple) MetaText(
            "Members vote on proposals from the ${c.kind.noun.lowercase()}'s Governance tab (liquid democracy: anyone can lend " +
                "their vote to a member they trust, and a direct vote always overrides it). A policy change that passes is applied automatically.",
            maxLines = 5,
        )
        if (c.kind == CommunityKind.Sphere) {
            Toggle(
                "Public activity",
                "When on, anyone — even visitors without an account — can see this sphere's projects, alliances and openings.",
                isPublic,
                enabled = true,
            ) { isPublic = it }
            if (!simple) Toggle(
                "Sandbox sphere",
                "Every new member who registers is enrolled into this sphere." + if (!isPlatformAdmin) " Only a platform administrator can change this." else "",
                isSandbox,
                enabled = isPlatformAdmin,
            ) { isSandbox = it }
        }
        MoreInAdvanced("Who can join and how decisions are made are")
        PrimaryAction("Save changes", busy = busy, enabled = name.isNotBlank(), onClick = {
            val changes = buildMap {
                if (name.trim() != c.name) put("name", name.trim())
                if (description.trim() != c.description.orEmpty()) put("description", description.trim())
                fields.forEach { f ->
                    val v = values[f.key]
                    if (v != null && v != Policies.valueOf(c, f.key)) put(f.key, v)
                }
            }
            onSave(
                changes,
                isPublic.takeIf { c.kind == CommunityKind.Sphere && it != c.isPublic },
                isSandbox.takeIf { c.kind == CommunityKind.Sphere && isPlatformAdmin && it != c.isSandbox },
            )
        })
    }
}

@Composable
private fun Toggle(label: String, explanation: String, checked: Boolean, enabled: Boolean, onChange: (Boolean) -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(label, style = MaterialTheme.typography.titleSmall)
            MetaText(explanation, maxLines = 4)
        }
        Switch(checked = checked, onCheckedChange = onChange, enabled = enabled)
    }
}
