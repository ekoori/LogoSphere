package com.krbavcic.logosphere.ui.exchange

import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.listSaver
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.runtime.toMutableStateList
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import coil.compose.AsyncImage
import com.krbavcic.logosphere.AppContainer
import com.krbavcic.logosphere.core.logic.Dates
import com.krbavcic.logosphere.core.logic.Effort
import com.krbavcic.logosphere.core.logic.ExchangeRules
import com.krbavcic.logosphere.core.logic.Parties
import com.krbavcic.logosphere.core.logic.Party
import com.krbavcic.logosphere.core.model.CommentType
import com.krbavcic.logosphere.core.model.ExchangeDetail
import com.krbavcic.logosphere.core.model.FranklMode
import com.krbavcic.logosphere.core.model.LikeTarget
import com.krbavcic.logosphere.core.model.LikeInfo
import android.net.Uri
import com.krbavcic.logosphere.core.model.Exchange
import com.krbavcic.logosphere.core.model.NewComment
import com.krbavcic.logosphere.core.model.ValueCard
import com.krbavcic.logosphere.ui.common.BannerField
import com.krbavcic.logosphere.ui.common.LinkText
import com.krbavcic.logosphere.ui.common.rememberPhotoTaker
import com.krbavcic.logosphere.ui.common.rememberPicturePicker
import com.krbavcic.logosphere.ui.common.rememberPicturesPicker
import com.krbavcic.logosphere.data.Change
import com.krbavcic.logosphere.ui.Load
import com.krbavcic.logosphere.ui.LoadViewModel
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.Navigator
import com.krbavcic.logosphere.ui.common.Avatar
import com.krbavcic.logosphere.ui.common.BackTopBar
import com.krbavcic.logosphere.ui.common.BrandCard
import com.krbavcic.logosphere.ui.common.DemoTag
import com.krbavcic.logosphere.ui.common.ExchangeStatusPill
import com.krbavcic.logosphere.ui.common.GroupAvatar
import com.krbavcic.logosphere.ui.common.LikeControl
import com.krbavcic.logosphere.ui.common.LoadContent
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.PersonaTag
import com.krbavcic.logosphere.ui.common.PrimaryAction
import com.krbavcic.logosphere.ui.common.ProgressTimeline
import com.krbavcic.logosphere.ui.common.QuietPill
import com.krbavcic.logosphere.ui.common.QuoteLine
import com.krbavcic.logosphere.ui.common.Refreshable
import com.krbavcic.logosphere.ui.common.ScreenPadding
import com.krbavcic.logosphere.ui.common.SectionHeading
import com.krbavcic.logosphere.ui.common.SnackbarMessages
import com.krbavcic.logosphere.ui.common.ValueChip
import com.krbavcic.logosphere.ui.common.ValueChips
import com.krbavcic.logosphere.ui.theme.Brand
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import com.krbavcic.logosphere.ui.trail.AcknowledgeButton
import com.krbavcic.logosphere.ui.trail.AcknowledgementRun
import com.krbavcic.logosphere.ui.trail.CardOwner
import com.krbavcic.logosphere.ui.common.LocalSimple
import com.krbavcic.logosphere.ui.common.AiPictureTag
import androidx.compose.foundation.layout.Box
import com.krbavcic.logosphere.core.api.userMessage
import kotlin.coroutines.cancellation.CancellationException
import com.krbavcic.logosphere.core.logic.Messaging
import com.krbavcic.logosphere.core.logic.Sharing

data class ExchangeData(
    val detail: ExchangeDetail,
    /** The viewer's own value cards, to name in what they write. */
    val myCards: List<ValueCard>,
    /** The initiator's cards — a receipt may say it expressed *their* value. */
    val theirCards: List<ValueCard>,
)

class ExchangeViewModel(private val app: AppContainer, private val id: String) : LoadViewModel<ExchangeData>() {
    val viewerId: String? get() = app.session.user?.id
    val acknowledgements = acknowledgementActions(app.api)

    init {
        load()
    }

    override suspend fun fetch(force: Boolean): ExchangeData = coroutineScope {
        val me = viewerId
        val mine = async { me?.let { runCatching { app.api.valueCards(it) }.getOrNull() }.orEmpty() }
        val detail = app.api.exchange(id)
        val initiator = detail.exchange.initiatorId ?: detail.exchange.userId
        val theirs = if (ExchangeRules.canAddReceipt(detail) && initiator != null && initiator != me) {
            runCatching { app.api.valueCards(initiator) }.getOrDefault(emptyList())
        } else {
            emptyList()
        }
        ExchangeData(detail, mine.await(), theirs)
    }

    private suspend fun changed() {
        app.changes.emit(Change.Exchanges)
        reload()
    }

    fun advance() {
        val next = current?.detail?.exchange?.let(ExchangeRules::nextStatus) ?: return
        act(onSuccess = { changed() }) { app.api.setExchangeStatus(id, next) }
    }

    fun cancel() = act(onSuccess = { changed() }) { app.api.setExchangeStatus(id, ExchangeRules.CANCELLED) }

    /** Adds what was written; a receipt may bring up to three photos (read first, so a bad file stops it all). */
    fun write(comment: NewComment, photos: List<Uri>, onDone: () -> Unit) {
        var photoProblem: String? = null
        act(onSuccess = {
            onDone()
            changed()
            photoProblem?.let { say("Your receipt was saved, but not its photos. $it") }
        }) {
            val uploads = photos.take(3).map { app.pictures.read(it) }
            app.api.addComment(id, comment)
            if (uploads.isNotEmpty()) {
                try {
                    app.api.addReceiptPhotos(id, uploads)
                    repeat(3) { app.pictures.replaced(app.api.receiptPhotoUrl(id, it)) }
                } catch (e: CancellationException) {
                    throw e
                } catch (e: Exception) {
                    // The receipt is in: sending it all again would only be refused as a second one.
                    photoProblem = e.userMessage()
                }
            }
        }
    }

    fun edit(title: String, description: String, banner: Uri?, onDone: () -> Unit) {
        if (title.isBlank()) {
            say("The title can't be empty.")
            return
        }
        act(onSuccess = {
            onDone()
            changed()
            say("Exchange updated.")
        }) {
            val upload = banner?.let { app.pictures.read(it) }
            app.api.editExchange(id, title, description, upload)
            if (upload != null) app.pictures.replaced(app.api.exchangeImageUrl(id))
        }
    }

    fun like(target: LikeTarget) {
        val exchange = current?.detail?.exchange ?: return
        toggleExchangeLike(app.api, exchange, target) { data, f ->
            data.copy(detail = data.detail.copy(exchange = f(data.detail.exchange)))
        }
    }
}

@Composable
fun ExchangeScreen(id: String) {
    val app = LocalAppContainer.current
    val vm: ExchangeViewModel = viewModel(key = "exchange-$id") { ExchangeViewModel(app, id) }
    val navigator = LocalNavigator.current
    val state by vm.state.collectAsStateWithLifecycle()
    val refreshing by vm.refreshing.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    SnackbarMessages(vm.messages, snackbar)

    Scaffold(
        topBar = { BackTopBar("Exchange", navigator::back) },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        LoadContent(state, onRetry = vm::load, modifier = Modifier.padding(padding)) { data ->
            Refreshable(refreshing, vm::refresh, Modifier.padding(padding).imePadding()) {
                ExchangeContent(data, vm, busy)
            }
        }
    }
}

private fun Navigator.party(party: Party) {
    val id = party.id ?: return
    val group = party.group
    if (group != null) community(group, id) else person(id)
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun ExchangeContent(data: ExchangeData, vm: ExchangeViewModel, busy: Boolean) {
    val app = LocalAppContainer.current
    val navigator = LocalNavigator.current
    val detail = data.detail
    val x = detail.exchange
    val me = vm.viewerId
    val initiator = Parties.initiator(x, me)
    val recipient = Parties.recipient(x, me)
    val cancelled = ExchangeRules.isCancelled(x)
    var confirmCancel by rememberSaveable { mutableStateOf(false) }
    var editing by rememberSaveable { mutableStateOf(false) }

    LazyColumn(
        contentPadding = PaddingValues(start = ScreenPadding, end = ScreenPadding, top = 4.dp, bottom = 32.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        item(key = "head") {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    ExchangeStatusPill(x)
                    if (x.isDemo) DemoTag()
                    Spacer(Modifier.weight(1f))
                    LikeControl(x.likesFor(LikeTarget.Exchange), { vm.like(LikeTarget.Exchange) })
                }
                if (editing) {
                    EditExchangeForm(x, busy, onSave = { title, description, banner -> vm.edit(title, description, banner) { editing = false } }, onCancel = { editing = false })
                    return@Column
                }
                Text(x.title ?: "An exchange of trust", style = MaterialTheme.typography.headlineSmall)
                MetaText(
                    listOfNotNull(Dates.day(x.startedAt).ifEmpty { null }, x.projectName?.let { "Part of $it" }).joinToString("  ·  "),
                )
                if (ExchangeRules.canEdit(detail)) {
                    LinkText("✎ Edit title, description and picture", onClick = { editing = true })
                }
                if (x.hasImage) {
                    Box {
                        AsyncImage(
                            model = app.pictures.of(app.api.exchangeImageUrl(x.id)),
                            contentDescription = null,
                            contentScale = ContentScale.Crop,
                            modifier = Modifier
                                .fillMaxWidth()
                                .aspectRatio(16f / 9f)
                                .clip(MaterialTheme.shapes.large),
                        )
                        if (x.imageIsAi) AiPictureTag(Modifier.align(Alignment.TopStart))
                    }
                }
                // Only what the people wrote - no generated stand-in.
                x.longDescription?.takeIf { it.isNotBlank() }?.let {
                    Text(it, style = MaterialTheme.typography.bodyLarge)
                }
                Sharing.loanNote(x)?.let {
                    Text(it, style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.primary)
                }
                if (x.isFinished) MetaText("✓ This exchange is finished — its details are locked.", maxLines = 2)
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (x.projectId != null && x.projectName != null) {
                        TextButton(onClick = { navigator.community(com.krbavcic.logosphere.core.model.CommunityKind.Project, x.projectId!!) }) {
                            Text("${com.krbavcic.logosphere.core.model.CommunityKind.Project.glyph} ${x.projectName}")
                        }
                    }
                    x.sourceOpeningId?.let { opening ->
                        TextButton(onClick = { navigator.opening(opening) }) { Text("From an opening →") }
                    }
                }
            }
        }

        item(key = "people") {
            BrandCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    SectionHeading("Participants")
                    PartyRow(initiator, "Initiator") { navigator.party(initiator) }
                    recipient?.let { PartyRow(it, "Recipient") { navigator.party(it) } }
                    Messaging.otherSide(x, me, detail.isInitiator, detail.isOther)?.let { who ->
                        TextButton(onClick = { navigator.conversation(who, x.sourceOpeningId) }) { Text("Send a message") }
                    }
                }
            }
        }

        item(key = "progress") {
            BrandCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    SectionHeading("Where it stands")
                    ProgressTimeline(ExchangeRules.progress(x))
                    val next = ExchangeRules.nextStatus(x)
                    if (ExchangeRules.canAdvance(detail) && next != null) {
                        PrimaryAction("Mark as $next", onClick = vm::advance, busy = busy)
                    }
                    if (ExchangeRules.canCancel(detail)) {
                        OutlinedButton(
                            onClick = { confirmCancel = true },
                            enabled = !busy,
                            modifier = Modifier.fillMaxWidth(),
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error),
                        ) { Text("Cancel exchange") }
                    }
                    if (cancelled) Text("This exchange was cancelled.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.error)
                }
            }
        }

        item(key = "receipts") {
            BrandCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                    SectionHeading("✓ Receipts")
                    val simple = LocalSimple.current
                    MetaText(
                        if (simple) "Thanks, in their own words." else "Endorsed records of what happened and why it mattered.",
                        maxLines = 2,
                    )
                    if (x.receipt == null && x.initiatorNote == null) {
                        Text("No receipts yet.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    x.receipt?.let { text ->
                        Written(
                            author = recipient?.label ?: "Recipient",
                            authorParty = recipient,
                            badge = FranklMode.of(x.receiptFranklMode)?.takeUnless { simple }?.let { "${it.glyph} ${it.label.lowercase()}" },
                            text = text,
                            cards = x.receiptCards,
                            context = x.receiptContext,
                            at = x.receiptAt,
                            hours = x.effortHours,
                            accent = Brand.colors.receiptAccent,
                            likes = x.likesFor(LikeTarget.Receipt),
                            onLike = { vm.like(LikeTarget.Receipt) },
                        )
                        if (x.receiptPhotoCount > 0) {
                            Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                repeat(x.receiptPhotoCount) { index ->
                                    AsyncImage(
                                        model = app.pictures.of(app.api.receiptPhotoUrl(x.id, index)),
                                        contentDescription = "Receipt photo ${index + 1}",
                                        contentScale = ContentScale.Crop,
                                        modifier = Modifier
                                            .size(120.dp)
                                            .clip(MaterialTheme.shapes.medium),
                                    )
                                }
                            }
                        }
                    }
                    x.initiatorNote?.let { text ->
                        Written(
                            author = initiator.label,
                            authorParty = initiator,
                            badge = "note",
                            text = text,
                            cards = x.initiatorNoteCards,
                            context = null,
                            at = x.initiatorNoteAt,
                            accent = Brand.colors.receiptAccent,
                            likes = x.likesFor(LikeTarget.InitiatorNote),
                            onLike = { vm.like(LikeTarget.InitiatorNote) },
                        )
                    }
                    if (ExchangeRules.canAddReceipt(detail)) {
                        Composer(
                            type = CommentType.Receipt,
                            open = "Add your receipt",
                            prompt = "How did this exchange feel? What did it mean to you?",
                            myCards = data.myCards,
                            theirCards = data.theirCards,
                            theirLabel = "${initiator.name}'s values",
                            realPhotosOnly = !x.isDemo,
                            busy = busy,
                            onSubmit = vm::write,
                        )
                    }
                    if (ExchangeRules.canAddNote(detail)) {
                        Composer(
                            type = CommentType.InitiatorNote,
                            open = "Add your note",
                            prompt = "Reflect on this exchange — what did you give and learn?",
                            myCards = data.myCards,
                            busy = busy,
                            onSubmit = vm::write,
                        )
                    }
                    val followUps = listOfNotNull(
                        x.initiatorFollowUp?.let { Triple(initiator.label, it, x.initiatorFollowUpAt) },
                        x.recipientFollowUp?.let { Triple(recipient?.label ?: "Recipient", it, x.recipientFollowUpAt) },
                    )
                    if (followUps.isNotEmpty() || ExchangeRules.canAddFollowUp(detail)) {
                        SectionHeading("Follow-up")
                        followUps.forEach { (who, text, at) ->
                            QuoteLine(author = listOf(who, Dates.day(at)).filter { it.isNotEmpty() }.joinToString(" · "), text = text, accent = MaterialTheme.colorScheme.outline, maxLines = 8)
                        }
                        if (ExchangeRules.canAddFollowUp(detail)) {
                            Composer(
                                type = CommentType.FollowUp,
                                open = "Add a follow-up",
                                prompt = "A brief follow-up comment…",
                                myCards = emptyList(),
                                busy = busy,
                                onSubmit = vm::write,
                            )
                        }
                    }
                }
            }
        }

        item(key = "acks") {
            BrandCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                    SectionHeading("Acknowledgements")
                    MetaText("Public thanks — warmth, not currency.")
                    if (x.acknowledgements.isEmpty()) {
                        Text("No acknowledgements yet.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    } else {
                        AcknowledgementRun(x.acknowledgements, me, vm.acknowledgements, busy)
                    }
                    if (ExchangeRules.canAcknowledge(detail)) {
                        val sides = listOfNotNull(
                            x.userId?.let { CardOwner(it, "${x.initiatorName ?: "The initiator"}'s values") },
                            x.otherUserId?.let { CardOwner(it, "${x.otherUserName ?: "The recipient"}'s values") },
                        )
                        AcknowledgeButton(x.id, sides, vm.acknowledgements, busy)
                    }
                }
            }
        }
    }

    if (confirmCancel) {
        AlertDialog(
            onDismissRequest = { confirmCancel = false },
            title = { Text("Cancel this exchange?") },
            text = { Text("Both of you will see it as cancelled. This can't be undone.") },
            confirmButton = { TextButton(onClick = { confirmCancel = false; vm.cancel() }) { Text("Cancel exchange") } },
            dismissButton = { TextButton(onClick = { confirmCancel = false }) { Text("Keep it") } },
        )
    }
}

@Composable
private fun PartyRow(party: Party, role: String, onClick: () -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .clickable(enabled = party.id != null, onClick = onClick),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        val group = party.group
        if (group != null) GroupAvatar(group, size = 36.dp) else Avatar(party.id, party.name, size = 36.dp)
        Spacer(Modifier.width(12.dp))
        Column(Modifier.weight(1f)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                Text(party.label, style = MaterialTheme.typography.titleSmall, modifier = Modifier.weight(1f, fill = false))
                if (party.personaByName) PersonaTag()
            }
            val via = party.actingUserName?.let { " · via $it" }.orEmpty()
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                MetaText((group?.noun ?: "Person") + via, modifier = Modifier.weight(1f, fill = false))
                if (party.personaActsForGroup) PersonaTag(compact = true)
            }
        }
        QuietPill(role)
    }
}

private const val MAX_RECEIPT_PHOTOS = 3

/** Title, description and banner picture, edited in place by either side until the exchange is finished. */
@Composable
private fun EditExchangeForm(x: Exchange, busy: Boolean, onSave: (String, String, Uri?) -> Unit, onCancel: () -> Unit) {
    val app = LocalAppContainer.current
    var title by rememberSaveable(x.id) { mutableStateOf(x.title.orEmpty()) }
    var description by rememberSaveable(x.id) { mutableStateOf(x.longDescription.orEmpty()) }
    var banner by rememberSaveable(x.id) { mutableStateOf<Uri?>(null) }
    val pick = rememberPicturePicker { banner = it }
    val take = rememberPhotoTaker { banner = it }
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
            modifier = Modifier.fillMaxWidth().heightIn(min = 100.dp),
        )
        BannerField(banner, if (x.hasImage) app.api.exchangeImageUrl(x.id) else null, kind = null, onPick = pick, onTake = take)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { onSave(title, description, banner) }, enabled = title.isNotBlank() && !busy) { Text("Save changes") }
            TextButton(onClick = onCancel, enabled = !busy) { Text("Cancel") }
        }
    }
}

/** A receipt, note or acknowledgement as written. */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun Written(
    author: String,
    authorParty: Party?,
    badge: String?,
    text: String,
    cards: List<ValueCard>,
    context: String?,
    at: String?,
    accent: androidx.compose.ui.graphics.Color,
    hours: Double? = null,
    likes: LikeInfo,
    onLike: () -> Unit,
) {
    val navigator = LocalNavigator.current
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Row(
                Modifier
                    .weight(1f)
                    .clickable(enabled = authorParty?.id != null) { authorParty?.let { navigator.party(it) } },
                verticalAlignment = Alignment.CenterVertically,
            ) {
                val group = authorParty?.group
                if (group != null) GroupAvatar(group, size = 24.dp) else Avatar(authorParty?.id, author, size = 24.dp)
                Spacer(Modifier.width(8.dp))
                Text(author, style = MaterialTheme.typography.titleSmall)
                badge?.let {
                    Spacer(Modifier.width(8.dp))
                    QuietPill(it)
                }
            }
            LikeControl(likes, onLike)
        }
        QuoteLine(author = Dates.day(at), text = text, accent = accent, maxLines = 20)
        if (cards.isNotEmpty()) ValueChips(cards)
        Effort.text(hours)?.let { MetaText(it) }
        context?.takeIf { it.isNotBlank() }?.let {
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text("CONTEXT", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text(it, style = MaterialTheme.typography.bodyMedium, fontFamily = FontFamily.Monospace)
            }
        }
    }
}

/**
 * The form for adding a receipt, note, follow-up or acknowledgement: closed to a button until
 * asked for, then text, the values it expressed and — for a receipt — Frankl's kind of meaning
 * and an optional context note.
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun Composer(
    type: CommentType,
    open: String,
    prompt: String,
    myCards: List<ValueCard>,
    busy: Boolean,
    onSubmit: (NewComment, List<Uri>, () -> Unit) -> Unit,
    theirCards: List<ValueCard> = emptyList(),
    theirLabel: String = "Their values",
    /** Outside demo spheres a receipt's photos can't be AI pictures. */
    realPhotosOnly: Boolean = false,
) {
    val simple = LocalSimple.current
    var expanded by rememberSaveable { mutableStateOf(false) }
    var text by rememberSaveable { mutableStateOf("") }
    var context by rememberSaveable { mutableStateOf("") }
    var hours by rememberSaveable { mutableStateOf("") }
    var mode by rememberSaveable { mutableStateOf<String?>(null) }
    // Saved, as all of the form is: the camera can push the app out of memory.
    val selected = rememberSaveable(saver = listSaver(save = { it.toList() }, restore = { it.toMutableStateList() })) {
        mutableStateListOf<String>()
    }
    val photos = rememberSaveable(
        saver = listSaver(save = { it.map(Uri::toString) }, restore = { it.map(Uri::parse).toMutableStateList() }),
    ) { mutableStateListOf<Uri>() }
    fun add(picked: List<Uri>) {
        val room = MAX_RECEIPT_PHOTOS - photos.size
        if (room > 0) photos.addAll(picked.take(room))
    }
    val pickPhotos = rememberPicturesPicker(MAX_RECEIPT_PHOTOS) { add(it) }
    // A receipt is evidence: photos taken or chosen, and never an AI picture.
    val takePhoto = rememberPhotoTaker { add(listOf(it)) }

    if (!expanded) {
        Button(
            onClick = { expanded = true },
            colors = if (type == CommentType.Acknowledgement) {
                ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondaryContainer, contentColor = MaterialTheme.colorScheme.onSecondaryContainer)
            } else {
                ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primaryContainer, contentColor = MaterialTheme.colorScheme.onPrimaryContainer)
            },
            modifier = Modifier.fillMaxWidth(),
        ) { Text("+ $open") }
        return
    }

    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        OutlinedTextField(
            value = text,
            onValueChange = { text = it },
            placeholder = { Text(prompt) },
            keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences),
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 110.dp),
        )
        if (type == CommentType.Receipt && !simple) {
            Text("What kind of meaning was this?", style = MaterialTheme.typography.labelLarge)
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                FranklMode.entries.forEach { m ->
                    FilterChip(
                        selected = mode == m.key,
                        onClick = { mode = if (mode == m.key) null else m.key },
                        label = { Text("${m.glyph} ${m.label}") },
                    )
                }
            }
            FranklMode.of(mode)?.let { MetaText("${it.label}: ${it.hint}") }
        }
        val groups = listOfNotNull(
            myCards.takeIf { it.isNotEmpty() }?.let { "Your values" to it },
            theirCards.takeIf { it.isNotEmpty() }?.let { theirLabel to it },
        )
        if (groups.isNotEmpty()) {
            Text("Which values did this express?", style = MaterialTheme.typography.labelLarge)
            groups.forEach { (label, cards) ->
                if (groups.size > 1) MetaText(label)
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    cards.forEach { card ->
                        val cardId = card.id ?: return@forEach
                        ValueChip(card, selected = cardId in selected, onClick = {
                            if (cardId in selected) selected.remove(cardId) else selected.add(cardId)
                        })
                    }
                }
            }
        }
        if (type == CommentType.Receipt) {
            OutlinedTextField(
                value = hours,
                onValueChange = { typed -> hours = typed.filter { it.isDigit() || it == '.' || it == ',' }.take(6) },
                label = { Text("About how many hours did it take? (optional)") },
                singleLine = true,
                isError = hours.isNotBlank() && Effort.parse(hours) == null,
                supportingText = if (hours.isNotBlank() && Effort.parse(hours) == null) {
                    { Text("From a quarter of an hour to 100 hours.") }
                } else {
                    null
                },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                modifier = Modifier.fillMaxWidth(),
            )
            if (!simple) OutlinedTextField(
                value = context,
                onValueChange = { context = it },
                label = { Text("Context (optional)") },
                placeholder = { Text("Effort: moderate\nCare: high") },
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 100.dp),
            )
            Text("Photos (up to 3)", style = MaterialTheme.typography.labelLarge)
            if (realPhotosOnly) MetaText("A receipt is evidence: real photos only, no AI pictures.", maxLines = 2)
            if (photos.isNotEmpty()) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    photos.forEach { uri ->
                        AsyncImage(
                            model = uri,
                            contentDescription = null,
                            contentScale = ContentScale.Crop,
                            modifier = Modifier.size(72.dp).clip(MaterialTheme.shapes.medium),
                        )
                    }
                }
            }
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                val room = photos.size < MAX_RECEIPT_PHOTOS
                if (takePhoto != null) OutlinedButton(onClick = takePhoto, enabled = room) { Text("Take a photo") }
                OutlinedButton(onClick = pickPhotos, enabled = room) { Text("Choose photos") }
                if (photos.isNotEmpty()) TextButton(onClick = { photos.clear() }) { Text("Remove") }
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
            Button(
                onClick = {
                    val all = (myCards + theirCards).filter { it.id in selected }.distinctBy { it.id }
                    onSubmit(
                        NewComment(
                            type = type,
                            text = text,
                            cards = all,
                            franklMode = FranklMode.of(mode).takeUnless { simple },
                            context = context.takeIf { type == CommentType.Receipt && !simple },
                            hours = Effort.parse(hours).takeIf { type == CommentType.Receipt },
                        ),
                        if (type == CommentType.Receipt) photos.toList() else emptyList(),
                    ) {
                        text = ""
                        context = ""
                        hours = ""
                        mode = null
                        selected.clear()
                        photos.clear()
                        expanded = false
                    }
                },
                enabled = text.isNotBlank() && !busy && (hours.isBlank() || Effort.parse(hours) != null),
            ) { Text(if (type == CommentType.Acknowledgement) "Post acknowledgement" else "Add") }
            TextButton(onClick = { expanded = false }) { Text("Cancel") }
        }
    }
}
