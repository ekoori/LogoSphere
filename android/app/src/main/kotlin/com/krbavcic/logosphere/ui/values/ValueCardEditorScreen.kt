package com.krbavcic.logosphere.ui.values

import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.krbavcic.logosphere.AppContainer
import com.krbavcic.logosphere.core.api.AppProblem
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.FranklMode
import com.krbavcic.logosphere.core.model.ValueCardDraft
import com.krbavcic.logosphere.data.Change
import com.krbavcic.logosphere.ui.LoadViewModel
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.common.BackTopBar
import com.krbavcic.logosphere.ui.common.LoadContent
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.PrimaryAction
import com.krbavcic.logosphere.ui.common.ScreenPadding
import com.krbavcic.logosphere.ui.common.SnackbarMessages
import com.krbavcic.logosphere.ui.common.readable
import com.krbavcic.logosphere.ui.theme.valueCardAccent
import kotlinx.coroutines.async
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.receiveAsFlow
import com.krbavcic.logosphere.ui.common.LocalSimple
import com.krbavcic.logosphere.ui.common.MoreInAdvanced
import com.krbavcic.logosphere.ui.common.AiCardButton

/** The card being written: blank, or an existing one's words; and whose graph it's for. */
data class CardToWrite(val draft: ValueCardDraft, val groupName: String?)

class ValueCardEditorViewModel(
    private val app: AppContainer,
    private val groupKind: CommunityKind?,
    private val groupId: String?,
    private val cardId: String?,
) : LoadViewModel<CardToWrite>() {
    private val _saved = Channel<Unit>(Channel.BUFFERED)
    val saved = _saved.receiveAsFlow()

    init {
        load()
    }

    override suspend fun fetch(force: Boolean): CardToWrite = coroutineScope {
        val name = async { if (groupKind != null && groupId != null) app.api.community(groupKind, groupId).name else null }
        val owner = groupId ?: app.session.user?.id
        val draft = if (cardId == null || owner == null) {
            ValueCardDraft()
        } else {
            app.api.valueCards(owner).firstOrNull { it.id == cardId }?.let(ValueCardDraft::of)
                ?: throw AppProblem("That card is no longer on the Meaning Graph.")
        }
        CardToWrite(draft, name.await())
    }

    fun save(draft: ValueCardDraft) {
        if (draft.careAbout.isBlank()) {
            say(if (groupId != null) "Say what this group cares about." else "Say what you care about.")
            return
        }
        act(onSuccess = {
            app.changes.emit(Change.ValueCards)
            if (groupKind != null) {
                app.communities.invalidate(groupKind)
                app.changes.emit(Change.Communities)
            }
            _saved.send(Unit)
        }) { app.api.saveValueCard(groupId, cardId, draft) }
    }
}

/**
 * Writes or edits a value card — CLEAR's fields: what is cared about and why, what it looks like
 * and what drift looks like, the trade-off in conflict, the hard boundary, and Frankl's mode.
 */
@Composable
fun ValueCardEditorScreen(groupKind: CommunityKind?, groupId: String?, cardId: String?) {
    val app = LocalAppContainer.current
    val vm: ValueCardEditorViewModel = viewModel(key = "card-$groupId-$cardId") { ValueCardEditorViewModel(app, groupKind, groupId, cardId) }
    val navigator = LocalNavigator.current
    val state by vm.state.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    SnackbarMessages(vm.messages, snackbar)
    LaunchedEffect(vm) { vm.saved.collect { navigator.back() } }

    Scaffold(
        topBar = { BackTopBar(if (cardId == null) "New value card" else "Edit value card", navigator::back) },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        LoadContent(state, onRetry = vm::load, modifier = Modifier.padding(padding)) { start ->
            CardForm(start, isGroup = groupId != null, busy = busy, isNew = cardId == null, onSave = vm::save, modifier = Modifier.padding(padding))
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun CardForm(start: CardToWrite, isGroup: Boolean, busy: Boolean, isNew: Boolean, onSave: (ValueCardDraft) -> Unit, modifier: Modifier) {
    val d = start.draft
    var title by rememberSaveable { mutableStateOf(d.title) }
    var careAbout by rememberSaveable { mutableStateOf(d.careAbout) }
    var because by rememberSaveable { mutableStateOf(d.because) }
    var looksLike by rememberSaveable { mutableStateOf(d.looksLike) }
    var drift by rememberSaveable { mutableStateOf(d.driftLooksLike) }
    var conflict by rememberSaveable { mutableStateOf(d.inConflict) }
    var never by rememberSaveable { mutableStateOf(d.neverDo) }
    var mode by rememberSaveable { mutableStateOf(d.franklMode) }
    var colour by rememberSaveable { mutableStateOf(d.colorKey) }
    val we = if (isGroup) "we" else "you"
    val simple = LocalSimple.current

    Column(
        modifier
            .imePadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = ScreenPadding, vertical = 8.dp)
            .readable(),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        start.groupName?.let { MetaText("For the Meaning Graph of $it", maxLines = 2) }
        if (isNew && !isGroup) {
            MetaText(
                if (simple) "A value card says one thing you care about, in your own words. One is plenty to start with."
                else "A value card captures one thing you genuinely care about — not a hashtag, but a reason, " +
                    "a behaviour, and a drift signal.",
                maxLines = 4,
            )
        }
        AiCardButton(
            current = ValueCardDraft(title, careAbout, because, looksLike, drift, conflict, never, mode, colour),
            brief = simple,
            group = isGroup,
            onUse = {
                title = it.title
                careAbout = it.careAbout
                because = it.because
                looksLike = it.looksLike
                drift = it.driftLooksLike
                conflict = it.inConflict
                never = it.neverDo
                mode = it.franklMode
            },
        )
        Field(title, { title = it }, "Title", "e.g. Honest dialogue", singleLine = true)
        Field(careAbout, { careAbout = it }, if (isGroup) "We care about *" else "I care about *",
            if (isGroup) "What specifically does this group care about?" else "What specifically do you care about?", minHeight = 80)
        Field(because, { because = it }, "Because", if (simple) "Why it matters" else "The reason underneath it", minHeight = 80)
        // Hidden isn't cleared: what's already on a card is saved back as it was.
        if (simple) MoreInAdvanced("More can be said about a value")
        if (!simple) {
        Field(looksLike, { looksLike = it }, "Looks like — one behaviour per line", "Observable actions that express this value", minHeight = 100)
        Field(drift, { drift = it }, "Drift looks like", "Anti-signals — how $we'd know $we've drifted")
        Field(conflict, { conflict = it }, "In conflict, $we prioritise", "The trade-off $we make")
        Field(never, { never = it }, "Never", "A hard boundary")

        Text("Frankl mode", style = MaterialTheme.typography.labelLarge)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            FranklMode.entries.forEach { m ->
                FilterChip(selected = mode == m.key, onClick = { mode = m.key }, label = { Text("${m.glyph} ${m.label}") })
            }
        }
        MetaText(
            when (mode) {
                "experiential" -> "Experiential — what $we receive & encounter"
                "attitudinal" -> "Attitudinal — the stance $we take under constraint"
                else -> "Creative — what $we make & give"
            },
        )
        Text("Card colour", style = MaterialTheme.typography.labelLarge)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            ValueCardDraft.COLOURS.forEach { key ->
                val accent = valueCardAccent(key)
                Surface(
                    onClick = { colour = key },
                    shape = CircleShape,
                    color = accent,
                    modifier = Modifier
                        .size(40.dp)
                        .border(if (colour == key) 3.dp else 0.dp, MaterialTheme.colorScheme.onSurface, CircleShape)
                        .semantics { contentDescription = key.replaceFirstChar { it.uppercase() } + if (colour == key) ", chosen" else "" },
                ) { Box(Modifier.size(40.dp)) }
            }
        }
        }
        PrimaryAction(
            if (!isNew) "Save changes" else if (simple) "Save this card" else "Add to Meaning Graph",
            busy = busy,
            enabled = careAbout.isNotBlank(),
            onClick = {
                onSave(ValueCardDraft(title, careAbout, because, looksLike, drift, conflict, never, mode, colour))
            },
        )
        if (!isNew) MetaText("Saving keeps the old wording as history: receipts that named this card still show it.", maxLines = 3)
    }
}

@Composable
private fun Field(
    value: String,
    onChange: (String) -> Unit,
    label: String,
    placeholder: String,
    singleLine: Boolean = false,
    minHeight: Int = 0,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        label = { Text(label) },
        placeholder = { Text(placeholder) },
        singleLine = singleLine,
        keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences),
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = minHeight.dp),
    )
}
