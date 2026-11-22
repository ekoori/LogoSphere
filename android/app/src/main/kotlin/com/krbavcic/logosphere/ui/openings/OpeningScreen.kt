package com.krbavcic.logosphere.ui.openings

import android.net.Uri
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.OutlinedTextField
import androidx.compose.ui.text.input.KeyboardCapitalization
import com.krbavcic.logosphere.ui.common.rememberPhotoTaker
import com.krbavcic.logosphere.ui.common.rememberPicturePicker
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
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
import com.krbavcic.logosphere.core.logic.OpeningRules
import com.krbavcic.logosphere.core.model.Acceptance
import com.krbavcic.logosphere.core.model.Community
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.Opening
import com.krbavcic.logosphere.data.Change
import com.krbavcic.logosphere.ui.LoadViewModel
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.common.Avatar
import com.krbavcic.logosphere.ui.common.BackTopBar
import com.krbavcic.logosphere.ui.common.Banner
import com.krbavcic.logosphere.ui.common.BrandCard
import com.krbavcic.logosphere.ui.common.Choice
import com.krbavcic.logosphere.ui.common.DemoTag
import com.krbavcic.logosphere.ui.common.LikeButton
import com.krbavcic.logosphere.ui.common.LikeCount
import com.krbavcic.logosphere.ui.common.LoadContent
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.OpeningTypePill
import com.krbavcic.logosphere.ui.common.PersonaTag
import com.krbavcic.logosphere.ui.common.Picker
import com.krbavcic.logosphere.ui.common.PrimaryAction
import com.krbavcic.logosphere.ui.common.ProgressTimeline
import com.krbavcic.logosphere.ui.common.QuietPill
import com.krbavcic.logosphere.ui.common.Refreshable
import com.krbavcic.logosphere.ui.common.ScreenPadding
import com.krbavcic.logosphere.ui.common.SectionHeading
import com.krbavcic.logosphere.ui.common.SnackbarMessages
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.receiveAsFlow
import com.krbavcic.logosphere.ui.common.LocalSimple

data class OpeningData(
    val opening: Opening,
    /** Alliances and projects the viewer may accept this on behalf of. */
    val acceptAs: List<Community>,
    /** The opening names its project only by name; this is its id when known. */
    val projectId: String?,
)

class OpeningViewModel(private val app: AppContainer, private val id: String) : LoadViewModel<OpeningData>() {
    val viewerId: String? get() = app.session.user?.id

    private val _openExchange = Channel<String>(Channel.BUFFERED)
    val openExchange = _openExchange.receiveAsFlow()

    init {
        load()
    }

    override suspend fun fetch(force: Boolean): OpeningData {
        val opening = app.api.opening(id)
        val all = runCatching { app.communities.all(force) }.getOrDefault(emptyList())
        // As on the web: the groups you hold a managing role in (not everything a platform admin could manage).
        val managed = Membership.managed(all, viewerId, isPlatformAdmin = false)
        val projectId = opening.projectId ?: opening.projectName?.let { name ->
            all.firstOrNull { it.kind == CommunityKind.Project && it.name == name }?.id
        }
        return OpeningData(opening, OpeningRules.acceptAsOptions(opening, managed), projectId)
    }

    private suspend fun changed(vararg what: Change) {
        app.openings.invalidate()
        what.forEach { app.changes.emit(it) }
        reload()
    }

    fun accept(actingAsId: String?) = act(onSuccess = {
        changed(Change.Openings)
        say("Accepted. ${current?.opening?.provider ?: "The provider"} will confirm.")
    }) { app.api.acceptOpening(id, actingAsId) }

    fun confirm(acceptance: Acceptance) = act {
        val result = app.api.confirmAcceptance(id, acceptance.accepterId)
        changed(Change.Openings, Change.Exchanges)
        result.exchangeId?.let { _openExchange.send(it) }
    }

    fun decline(acceptance: Acceptance) = act(onSuccess = { changed(Change.Openings) }) {
        app.api.declineAcceptance(id, acceptance.accepterId)
    }

    /** The viewer's own pending acceptance, taken back before the provider confirms it. */
    fun takeBack() {
        val mine = current?.opening?.myAcceptance ?: return
        act(onSuccess = {
            changed(Change.Openings)
            say("Your acceptance was taken back.")
        }) { app.api.declineAcceptance(id, mine.accepterId) }
    }

    fun withdraw() = act(onSuccess = {
        changed(Change.Openings)
        say("The opening was withdrawn.")
    }) { app.api.withdrawOpening(id) }

    fun like() {
        val opening = current?.opening ?: return
        toggleOpeningLike(app.api, opening) { data, f -> data.copy(opening = f(data.opening)) }
    }

    private val _replaced = Channel<String>(Channel.BUFFERED)

    /** A new version replaced this one: the screen moves to it. */
    val replaced = _replaced.receiveAsFlow()

    /** Once an exchange links to the opening, the server keeps it as it was and saves the edit as a new version. */
    fun edit(title: String, description: String, onDone: () -> Unit) {
        if (title.isBlank()) {
            say("The title can't be empty.")
            return
        }
        act {
            val result = app.api.editOpening(id, title, description)
            onDone()
            app.openings.invalidate()
            app.changes.emit(Change.Openings)
            val newId = result.service?.id
            if (result.versioned && newId != null && newId != id) {
                _replaced.send(newId)
            } else {
                reload()
                say("Opening updated.")
            }
        }
    }

    fun setPicture(uri: Uri) = act(onSuccess = {
        app.openings.invalidate()
        app.changes.emit(Change.Openings)
        reload()
        say("The picture was updated.")
    }) {
        app.api.setOpeningImage(id, app.pictures.read(uri))
        app.pictures.replaced(app.api.openingImageUrl(id))
    }
}

@Composable
fun OpeningScreen(id: String) {
    val app = LocalAppContainer.current
    val vm: OpeningViewModel = viewModel(key = "opening-$id") { OpeningViewModel(app, id) }
    val navigator = LocalNavigator.current
    val state by vm.state.collectAsStateWithLifecycle()
    val refreshing by vm.refreshing.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    SnackbarMessages(vm.messages, snackbar)
    LaunchedEffect(vm) { vm.openExchange.collect { navigator.exchange(it) } }
    LaunchedEffect(vm) { vm.replaced.collect { newId -> navigator.replace { opening(newId) } } }

    Scaffold(
        // The title is the banner's; the bar names what this is.
        topBar = {
            val opening = (state as? com.krbavcic.logosphere.ui.Load.Ready)?.value?.opening
            BackTopBar(opening?.let { if (it.isOffer) "Offer" else "Need" } ?: "Opening", navigator::back)
        },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        LoadContent(state, onRetry = vm::load, modifier = Modifier.padding(padding)) { data ->
            Refreshable(refreshing, vm::refresh, Modifier.padding(padding)) {
                OpeningContent(data, vm, busy)
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun OpeningContent(data: OpeningData, vm: OpeningViewModel, busy: Boolean) {
    val app = LocalAppContainer.current
    val navigator = LocalNavigator.current
    val opening = data.opening
    val me = vm.viewerId
    var confirmWithdraw by rememberSaveable { mutableStateOf(false) }
    var editing by rememberSaveable { mutableStateOf(false) }
    val canManage = OpeningRules.mayManage(opening, me)
    val isOwn = OpeningRules.isOwn(opening, me)
    val cancelled = opening.status == "Cancelled"
    val pickPicture = rememberPicturePicker { vm.setPicture(it) }
    val takePicture = rememberPhotoTaker { vm.setPicture(it) }

    LazyColumn(contentPadding = PaddingValues(bottom = 32.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        item(key = "banner") {
            Banner(
                imageUrl = if (opening.hasImage) app.api.openingImageUrl(opening.id) else null,
                kind = null,
                height = 180.dp,
            ) {
                Column(
                    Modifier
                        .align(Alignment.BottomStart)
                        .padding(ScreenPadding),
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        OpeningTypePill(opening.isOffer)
                        if (opening.isPerpetual) QuietPill("↻ Ongoing")
                        if (opening.version > 1) QuietPill("Version ${opening.version}")
                        if (opening.isDemo) DemoTag()
                    }
                    Text(opening.title, style = MaterialTheme.typography.headlineSmall, color = Color(0xFFFDFAF2))
                }
            }
        }
        item(key = "who") {
            Column(Modifier.padding(horizontal = ScreenPadding), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                val personId = opening.actingUserId ?: opening.providerId
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.clickable(enabled = personId != null) { personId?.let(navigator::person) },
                ) {
                    Avatar(personId, opening.actingUser ?: opening.provider, size = 36.dp)
                    Spacer(Modifier.width(10.dp))
                    Column(Modifier.weight(1f)) {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            Text(
                                when {
                                    opening.actingUser != null -> "${opening.actingUser} for ${opening.provider}"
                                    OpeningRules.isOwn(opening, me) -> "You"
                                    else -> opening.provider ?: "A member"
                                },
                                style = MaterialTheme.typography.titleSmall,
                                modifier = Modifier.weight(1f, fill = false),
                            )
                            if (opening.providerIsAgent && !OpeningRules.isOwn(opening, me)) PersonaTag()
                        }
                        MetaText("Posted ${Dates.day(opening.createdAt)}")
                    }
                    // Your own opening isn't yours to appreciate (an old self-like can come off).
                    if (!OpeningRules.isOwn(opening, me) || opening.likedByMe) {
                        LikeButton(opening.likedByMe, opening.likes, vm::like)
                    } else {
                        LikeCount(opening.likes)
                    }
                }
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (opening.sphereId != null) {
                        AssistChip(
                            onClick = { navigator.community(CommunityKind.Sphere, opening.sphereId!!) },
                            label = { Text("✦ ${opening.sphereName ?: "Sphere"}") },
                        )
                    }
                    if (opening.projectName != null) {
                        AssistChip(
                            onClick = { data.projectId?.let { navigator.community(CommunityKind.Project, it) } },
                            enabled = data.projectId != null,
                            label = { Text("${CommunityKind.Project.glyph} ${opening.projectName}") },
                        )
                    }
                }
                if (editing) {
                    EditOpeningForm(opening, busy, onSave = { title, description -> vm.edit(title, description) { editing = false } }, onCancel = { editing = false })
                } else {
                    opening.description?.takeIf { it.isNotBlank() }?.let {
                        Text(it, style = MaterialTheme.typography.bodyLarge)
                    }
                    if (canManage && !cancelled) {
                        FlowRow(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                            // A platform admin may change anyone's opening: say so.
                            val asAdmin = if (isOwn || opening.isProvider) "" else " (admin)"
                            if (opening.isCurrent) TextButton(onClick = { editing = true }) { Text("✎ Edit$asAdmin") }
                            TextButton(onClick = pickPicture, enabled = !busy) {
                                Text((if (opening.hasImage) "Change picture" else "Add a picture") + asAdmin)
                            }
                            if (takePicture != null) {
                                TextButton(onClick = takePicture, enabled = !busy) { Text("Take a photo$asAdmin") }
                            }
                        }
                    }
                }
                if (opening.values.isNotEmpty()) {
                    FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        opening.values.forEach { QuietPill(it) }
                    }
                }
            }
        }
        item(key = "actions") {
            ActionsCard(data, vm, busy, onWithdraw = { confirmWithdraw = true })
        }
        if (OpeningRules.mayManage(opening, me) && opening.pendingAcceptances.isNotEmpty() && opening.status != "Cancelled") {
            item(key = "pending") {
                BrandCard(Modifier.padding(horizontal = ScreenPadding).fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        SectionHeading("Awaiting your confirmation")
                        opening.pendingAcceptances.forEachIndexed { index, acceptance ->
                            if (index > 0) HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                            PendingRow(acceptance, busy, onConfirm = { vm.confirm(acceptance) }, onDecline = { vm.decline(acceptance) })
                        }
                    }
                }
            }
        }
        item(key = "progress") {
            BrandCard(Modifier.padding(horizontal = ScreenPadding).fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    SectionHeading("Where it stands")
                    ProgressTimeline(OpeningRules.progress(opening))
                }
            }
        }
        if (opening.exchanges.isNotEmpty()) {
            item(key = "exchanges") {
                BrandCard(Modifier.padding(horizontal = ScreenPadding).fillMaxWidth()) {
                    Column(Modifier.padding(vertical = 8.dp)) {
                        SectionHeading("Exchanges from this opening", Modifier.padding(horizontal = 16.dp, vertical = 8.dp))
                        opening.exchanges.forEach { x ->
                            Row(
                                Modifier
                                    .fillMaxWidth()
                                    .clickable(enabled = x.exchangeId != null) { x.exchangeId?.let(navigator::exchange) }
                                    .padding(horizontal = 16.dp, vertical = 10.dp),
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                Avatar(x.actingUserId ?: x.accepterId, x.actingUserName ?: x.accepterName, size = 28.dp)
                                Spacer(Modifier.width(10.dp))
                                Column(Modifier.weight(1f)) {
                                    Text("With ${x.accepterName ?: "a member"}", style = MaterialTheme.typography.bodyMedium)
                                    MetaText(Dates.day(x.createdAt))
                                }
                                Text("View →", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.tertiary)
                            }
                        }
                    }
                }
            }
        }
    }

    if (confirmWithdraw) {
        AlertDialog(
            onDismissRequest = { confirmWithdraw = false },
            title = { Text("Withdraw this opening?") },
            text = { Text("It leaves Openings, and anyone waiting on a confirmation is told it was withdrawn.") },
            confirmButton = {
                TextButton(onClick = { confirmWithdraw = false; vm.withdraw() }) { Text("Withdraw") }
            },
            dismissButton = { TextButton(onClick = { confirmWithdraw = false }) { Text("Keep it") } },
        )
    }
}

@Composable
private fun ActionsCard(data: OpeningData, vm: OpeningViewModel, busy: Boolean, onWithdraw: () -> Unit) {
    val navigator = LocalNavigator.current
    val opening = data.opening
    val me = vm.viewerId
    val mine = opening.myAcceptance
    val canAccept = OpeningRules.canAccept(opening, me)
    val canWithdraw = OpeningRules.canWithdraw(opening, me)
    var acceptAs by rememberSaveable { mutableStateOf<String?>(null) }
    val simple = LocalSimple.current

    val hasSomething = canAccept || canWithdraw || mine != null || opening.status == "Cancelled"
    if (!hasSomething) return
    BrandCard(Modifier.padding(horizontal = ScreenPadding).fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            when {
                opening.status == "Cancelled" -> Text("This opening was withdrawn.", style = MaterialTheme.typography.bodyLarge)
                mine?.status == "pending" -> Text(
                    (if (mine.actingUserId != null) "You accepted this for ${mine.accepterName ?: "your group"}." else "You accepted this.") +
                        " Waiting for ${opening.provider ?: "the provider"} to confirm.",
                    style = MaterialTheme.typography.bodyLarge,
                )
                mine?.status == "confirmed" && mine.exchangeId != null -> Button(
                    onClick = { navigator.exchange(mine.exchangeId!!) },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("View your exchange") }
            }
            // Changed your mind? Until the provider confirms, it's yours to take back.
            if (OpeningRules.canTakeBack(opening)) {
                OutlinedButton(
                    onClick = vm::takeBack,
                    enabled = !busy,
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Take back my acceptance") }
            }
            if (canAccept) {
                if (!simple && data.acceptAs.isNotEmpty()) {
                    Picker(
                        label = "Accept as",
                        choices = listOf(Choice(null, "Myself")) + data.acceptAs.map { Choice(it.id, "${it.name} (${it.kind.noun.lowercase()})") },
                        selected = acceptAs,
                        onSelect = { acceptAs = it },
                    )
                }
                PrimaryAction(
                    if (opening.isOffer) "Accept this offer" else "Fulfil this need",
                    onClick = { vm.accept(acceptAs.takeUnless { simple }) },
                    busy = busy,
                )
                MetaText(
                    "${opening.provider ?: "The provider"} confirms before the exchange begins.",
                    maxLines = 2,
                )
            }
            if (canWithdraw) {
                OutlinedButton(
                    onClick = onWithdraw,
                    enabled = !busy,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error),
                ) {
                    // Someone else's opening is only withdrawable through the admin override: say so.
                    Text(if (OpeningRules.isOwn(opening, me)) "Withdraw opening" else "Withdraw (platform admin)")
                }
            }
        }
    }
}

/** Title and description, edited in place (the web's inline form). */
@Composable
private fun EditOpeningForm(opening: Opening, busy: Boolean, onSave: (String, String) -> Unit, onCancel: () -> Unit) {
    var title by rememberSaveable(opening.id) { mutableStateOf(opening.title) }
    var description by rememberSaveable(opening.id) { mutableStateOf(opening.description.orEmpty()) }
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        OutlinedTextField(
            value = title,
            onValueChange = { title = it },
            label = { Text("Title") },
            singleLine = true,
            keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences),
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = description,
            onValueChange = { description = it },
            label = { Text("Description") },
            keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences),
            modifier = Modifier.fillMaxWidth().heightIn(min = 120.dp),
        )
        MetaText(
            "Once an exchange has come from this opening, saving keeps this version as it was and makes a new one.",
            maxLines = 3,
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { onSave(title, description) }, enabled = title.isNotBlank() && !busy) { Text("Save changes") }
            TextButton(onClick = onCancel, enabled = !busy) { Text("Cancel") }
        }
    }
}

@Composable
private fun PendingRow(acceptance: Acceptance, busy: Boolean, onConfirm: () -> Unit, onDecline: () -> Unit) {
    val navigator = LocalNavigator.current
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        val personId = acceptance.actingUserId ?: acceptance.accepterId
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.clickable { navigator.person(personId) },
        ) {
            Avatar(personId, acceptance.actingUserName ?: acceptance.accepterName, size = 32.dp)
            Spacer(Modifier.width(10.dp))
            Column(Modifier.weight(1f)) {
                Text(acceptance.accepterName ?: "A member", style = MaterialTheme.typography.titleSmall)
                val via = acceptance.actingUserName?.let { "via $it · " }.orEmpty()
                MetaText(via + Dates.ago(acceptance.createdAt))
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = onConfirm, enabled = !busy, modifier = Modifier.weight(1f)) { Text("Confirm") }
            OutlinedButton(onClick = onDecline, enabled = !busy, modifier = Modifier.weight(1f)) { Text("Decline") }
        }
    }
}
