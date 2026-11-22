package com.krbavcic.logosphere.ui.common

import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.krbavcic.logosphere.core.api.userMessage
import com.krbavcic.logosphere.core.model.AiHelpStatus
import com.krbavcic.logosphere.core.model.SuggestedCard
import com.krbavcic.logosphere.core.model.ValueCardDraft
import com.krbavcic.logosphere.data.Captures
import com.krbavcic.logosphere.ui.LocalAppContainer
import kotlinx.coroutines.launch
import kotlin.coroutines.cancellation.CancellationException

private const val HINT_MAX = 300
private const val NOTES_MAX = 1500

/** On every picture known to be AI-made. */
@Composable
fun AiPictureTag(modifier: Modifier = Modifier, short: Boolean = false) {
    Text(
        if (short) "AI" else "AI picture",
        style = MaterialTheme.typography.labelSmall,
        color = Color(0xFFF7F4E8),
        modifier = modifier
            .padding(8.dp)
            .clip(CircleShape)
            .background(Color(0xC7181D14))
            .padding(horizontal = 9.dp, vertical = 3.dp)
            .semantics { contentDescription = "AI picture: made with AI" },
    )
}

/** What's switched on; nothing is offered until the server has said. */
@Composable
private fun rememberAiHelp(): AiHelpStatus? {
    val app = LocalAppContainer.current
    var status by remember { mutableStateOf<AiHelpStatus?>(null) }
    LaunchedEffect(app) {
        status = try {
            app.api.aiStatus()
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            null // no AI help to offer, and nothing else depends on it
        }
    }
    return status
}

/**
 * "Draw one with AI", beside a picture field: for openings and groups, never receipts. Nothing is
 * sent until Draw, and nothing saved until the picture is used.
 */
@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun AiPictureButton(purpose: String, title: String, description: String, onUse: (Uri) -> Unit, modifier: Modifier = Modifier) {
    if (rememberAiHelp()?.pictures?.on != true) return
    val app = LocalAppContainer.current
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var open by rememberSaveable { mutableStateOf(false) }
    var hint by rememberSaveable { mutableStateOf("") }
    var made by rememberSaveable { mutableStateOf<Uri?>(null) }
    var busy by remember { mutableStateOf(false) }
    var problem by remember { mutableStateOf<String?>(null) }

    OutlinedButton(onClick = { open = true }, modifier = modifier.fillMaxWidth()) { Text("✦ Draw one with AI") }
    if (!open) return

    fun close() {
        open = false
        made = null
        problem = null
    }

    fun draw() {
        scope.launch {
            busy = true
            problem = null
            try {
                val picture = app.api.drawPicture(purpose, title, description, hint)
                made = Captures.save(context, picture.bytes)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                problem = e.userMessage("The picture didn't come. Try again.")
            } finally {
                busy = false
            }
        }
    }

    ModalBottomSheet(
        onDismissRequest = ::close,
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
        containerColor = MaterialTheme.colorScheme.surfaceContainerLow,
    ) {
        Column(
            Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .imePadding()
                .padding(horizontal = 20.dp)
                .padding(bottom = 24.dp)
                .navigationBarsPadding(),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text("Draw one with AI", style = MaterialTheme.typography.headlineSmall)
            if (title.isBlank()) MetaText("Give it a title or name first, so there is something to draw.", maxLines = 2)
            OutlinedTextField(
                value = hint,
                onValueChange = { hint = it.take(HINT_MAX) },
                label = { Text("Anything it should show? (optional)") },
                placeholder = { Text("e.g. autumn light, an old wheelbarrow") },
                keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences),
                modifier = Modifier.fillMaxWidth(),
            )
            MetaText(
                "Sends the title, the description and your words to OpenAI, and nothing about who you are. " +
                    "AI pictures are labelled, and outside demo spheres they can't be evidence.",
                maxLines = 5,
            )
            made?.let { uri ->
                Box(Modifier.fillMaxWidth().aspectRatio(3f / 2f).clip(MaterialTheme.shapes.medium)) {
                    AsyncImage(uri, contentDescription = "Drawn for you", contentScale = ContentScale.Crop, modifier = Modifier.fillMaxSize())
                    AiPictureTag(Modifier.align(Alignment.BottomStart))
                }
            }
            if (busy) MetaText("Drawing. It takes about ten seconds…")
            problem?.let { Text(it, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.error) }
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                val picture = made
                if (picture == null) {
                    Button(onClick = ::draw, enabled = !busy && title.isNotBlank()) { Text("Draw") }
                } else {
                    Button(onClick = { onUse(picture); close() }, enabled = !busy) { Text("Use this picture") }
                    OutlinedButton(onClick = ::draw, enabled = !busy) { Text("Draw another") }
                }
            }
        }
    }
}

/**
 * "Help me word it", in the value-card editor. The suggestion is shown before it goes into the
 * card, and saving the card is still the member's own step.
 */
@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun AiCardButton(current: ValueCardDraft, brief: Boolean, group: Boolean, onUse: (ValueCardDraft) -> Unit, modifier: Modifier = Modifier) {
    if (rememberAiHelp()?.valueCards?.on != true) return
    val app = LocalAppContainer.current
    val scope = rememberCoroutineScope()
    var open by rememberSaveable { mutableStateOf(false) }
    var notes by rememberSaveable { mutableStateOf("") }
    var question by rememberSaveable { mutableStateOf("") }
    var suggested by remember { mutableStateOf<SuggestedCard?>(null) }
    var busy by remember { mutableStateOf(false) }
    var problem by remember { mutableStateOf<String?>(null) }

    Column(modifier, verticalArrangement = Arrangement.spacedBy(4.dp)) {
        OutlinedButton(onClick = { open = true }, modifier = Modifier.fillMaxWidth()) { Text("✦ Help me word it") }
        if (!open && question.isNotBlank()) {
            Text(
                "Something to ask yourself before saving: $question",
                style = MaterialTheme.typography.bodyMedium,
                fontStyle = FontStyle.Italic,
                color = MaterialTheme.colorScheme.onSurface,
            )
        }
    }
    if (!open) return

    val visible = listOf(current.title, current.careAbout, current.because) +
        if (brief) emptyList() else listOf(current.looksLike, current.driftLooksLike, current.inConflict, current.neverDo)
    val nothingYet = notes.isBlank() && visible.all { it.isBlank() }

    fun ask() {
        scope.launch {
            busy = true
            problem = null
            try {
                val reply = app.api.draftCard(notes, current, brief, group)
                suggested = reply.draft.takeIf { it.lines.isNotEmpty() }
                question = reply.question
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                problem = e.userMessage("The help didn't come. Try again.")
            } finally {
                busy = false
            }
        }
    }

    ModalBottomSheet(
        onDismissRequest = { open = false },
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
        containerColor = MaterialTheme.colorScheme.surfaceContainerLow,
    ) {
        Column(
            Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .imePadding()
                .padding(horizontal = 20.dp)
                .padding(bottom = 24.dp)
                .navigationBarsPadding(),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text("Help me word it", style = MaterialTheme.typography.headlineSmall)
            OutlinedTextField(
                value = notes,
                onValueChange = { notes = it.take(NOTES_MAX) },
                label = { Text(if (group) "What matters to the group? Any words will do." else "What matters to you? Any words will do.") },
                keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences),
                modifier = Modifier.fillMaxWidth().heightIn(min = 110.dp),
            )
            MetaText(
                "Sends what you write here and in the card to Claude, by Anthropic, and nothing about who you are. " +
                    "Nothing is saved until you save the card.",
                maxLines = 5,
            )
            suggested?.lines?.forEach { (label, words) ->
                Column {
                    MetaText(label)
                    Text(words, style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.onSurface)
                }
            }
            if (question.isNotBlank()) {
                Text(question, style = MaterialTheme.typography.bodyMedium, fontStyle = FontStyle.Italic, color = MaterialTheme.colorScheme.onSurface)
            }
            problem?.let { Text(it, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.error) }
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                val suggestion = suggested
                if (suggestion != null) {
                    Button(
                        onClick = {
                            onUse(suggestion.into(current, brief))
                            suggested = null
                            open = false
                        },
                        enabled = !busy,
                    ) { Text("Put it in the card") }
                    OutlinedButton(onClick = ::ask, enabled = !busy && !nothingYet) { Text("Try again") }
                } else {
                    Button(onClick = ::ask, enabled = !busy && !nothingYet) { Text(if (busy) "Thinking…" else "Suggest wording") }
                }
            }
        }
    }
}
