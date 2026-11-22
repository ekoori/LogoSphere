package com.krbavcic.logosphere.ui.messages

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
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
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.repeatOnLifecycle
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.krbavcic.logosphere.AppContainer
import com.krbavcic.logosphere.core.logic.Dates
import com.krbavcic.logosphere.core.logic.Messaging
import com.krbavcic.logosphere.core.model.Conversation
import com.krbavcic.logosphere.core.model.DirectMessage
import com.krbavcic.logosphere.core.model.ReportOf
import com.krbavcic.logosphere.data.Change
import com.krbavcic.logosphere.ui.Load
import com.krbavcic.logosphere.ui.LoadViewModel
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.common.BackTopBar
import com.krbavcic.logosphere.ui.common.BlockDialog
import com.krbavcic.logosphere.ui.common.EmptyNote
import com.krbavcic.logosphere.ui.common.LinkText
import com.krbavcic.logosphere.ui.common.LoadContent
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.ReportDialog
import com.krbavcic.logosphere.ui.common.ReportLink
import com.krbavcic.logosphere.ui.common.ScreenPadding
import com.krbavcic.logosphere.ui.common.SnackbarMessages
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlin.coroutines.cancellation.CancellationException

private const val POLL_MS = 15_000L

class ConversationViewModel(
    private val app: AppContainer,
    private val personId: String,
    private val openingId: String?,
) : LoadViewModel<Conversation>() {
    private var lastRead: String? = null
    private var pagedBack = false
    private var named = false

    init {
        load()
    }

    /** The newest page, over whatever older ones were loaded. */
    override suspend fun fetch(force: Boolean): Conversation {
        val page = app.api.conversation(personId, openingId)
        val before = current
        return page.copy(
            messages = Messaging.merge(before?.messages.orEmpty(), page.messages),
            more = if (pagedBack && before != null) before.more else page.more,
            about = page.about.takeUnless { named },
        )
    }

    fun poll() {
        if (state.value !is Load.Ready) return
        viewModelScope.launch {
            try {
                val page = app.api.conversation(personId, openingId)
                update {
                    it.copy(
                        messages = Messaging.merge(it.messages, page.messages),
                        canSend = page.canSend,
                        whyNot = page.whyNot,
                        blocked = page.blocked,
                    )
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                logFailure("poll", e) // the next one may do better
            }
        }
    }

    fun markRead(messages: List<DirectMessage>) {
        val newest = Messaging.lastOfTheirs(messages) ?: return
        if (newest == lastRead) return
        lastRead = newest
        viewModelScope.launch {
            try {
                app.api.readConversation(personId, newest)
                app.inbox.refreshCount() // its notification went with it
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                lastRead = null // again with the next change
                logFailure("read", e)
            }
        }
    }

    fun earlier() {
        val oldest = current?.messages?.firstOrNull() ?: return
        act {
            val page = app.api.conversation(personId, before = oldest.id)
            pagedBack = true
            update { it.copy(messages = Messaging.merge(it.messages, page.messages), more = page.more) }
        }
    }

    fun send(text: String, onSent: () -> Unit) {
        val about = current?.about
        act {
            val sent = app.api.sendMessage(personId, text, about?.id)
            named = true // the opening goes with the first message only
            update { it.copy(messages = Messaging.merge(it.messages, listOf(sent)), about = null) }
            onSent()
        }
    }

    fun setBlocked(blocked: Boolean) = act(onSuccess = {
        app.changes.emit(Change.Profile)
        reload()
    }) { app.api.setBlocked(personId, blocked) }
}

/** One conversation: between the two of them, and read by nobody else. */
@Composable
fun ConversationScreen(personId: String, openingId: String? = null) {
    val app = LocalAppContainer.current
    val vm: ConversationViewModel = viewModel(key = "conversation-$personId-$openingId") {
        ConversationViewModel(app, personId, openingId)
    }
    val navigator = LocalNavigator.current
    val state by vm.state.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    SnackbarMessages(vm.messages, snackbar)
    var menu by remember { mutableStateOf(false) }
    var blocking by rememberSaveable { mutableStateOf(false) }
    var reporting by rememberSaveable { mutableStateOf(false) }

    val owner = LocalLifecycleOwner.current
    LaunchedEffect(vm, owner) {
        owner.repeatOnLifecycle(Lifecycle.State.RESUMED) {
            while (true) {
                vm.poll()
                delay(POLL_MS)
            }
        }
    }

    val conversation = (state as? Load.Ready)?.value
    Scaffold(
        topBar = {
            BackTopBar(conversation?.person?.name ?: "Messages", navigator::back, actions = {
                if (conversation != null) {
                    Box {
                        IconButton(onClick = { menu = true }) { Icon(Icons.Filled.MoreVert, contentDescription = "More") }
                        DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                            DropdownMenuItem(text = { Text("Their profile") }, onClick = { menu = false; navigator.person(personId) })
                            DropdownMenuItem(
                                text = { Text(if (conversation.blocked) "Unblock" else "Block") },
                                onClick = {
                                    menu = false
                                    if (conversation.blocked) vm.setBlocked(false) else blocking = true
                                },
                            )
                            DropdownMenuItem(text = { Text("Report") }, onClick = { menu = false; reporting = true })
                        }
                    }
                }
            })
        },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        LoadContent(state, onRetry = vm::load, modifier = Modifier.padding(padding)) { data ->
            val newest = data.messages.lastOrNull()?.id
            val list = rememberLazyListState()
            LaunchedEffect(newest) {
                vm.markRead(data.messages)
                if (newest != null) list.scrollToItem(0)
            }
            Column(Modifier.padding(padding).fillMaxSize().imePadding()) {
                data.about?.let { about ->
                    LinkText(
                        "About: ${about.title}",
                        onClick = { navigator.opening(about.id) },
                        modifier = Modifier.padding(horizontal = ScreenPadding),
                    )
                }
                if (data.messages.isEmpty()) {
                    Box(Modifier.weight(1f).fillMaxWidth(), contentAlignment = Alignment.Center) {
                        EmptyNote("Only the two of you can read what you write here.")
                    }
                } else {
                    // Newest first and upside down, so the keyboard pushes the newest up with it.
                    LazyColumn(
                        state = list,
                        reverseLayout = true,
                        modifier = Modifier.weight(1f).fillMaxWidth(),
                        contentPadding = PaddingValues(horizontal = ScreenPadding, vertical = 10.dp),
                        verticalArrangement = Arrangement.spacedBy(10.dp, Alignment.Bottom),
                    ) {
                        items(data.messages.asReversed(), key = { it.id }) { message ->
                            MessageRow(message, personId) { navigator.opening(it) }
                        }
                        if (data.more) {
                            item(key = "earlier") {
                                TextButton(onClick = vm::earlier, enabled = !busy) { Text("Show earlier messages") }
                            }
                        }
                    }
                }
                if (data.canSend) {
                    Composer(busy, onSend = vm::send)
                } else {
                    MetaText(data.whyNot.orEmpty(), Modifier.padding(ScreenPadding), maxLines = 5)
                }
            }
        }
    }

    if (blocking && conversation != null) {
        BlockDialog(conversation.person.name, onBlock = { vm.setBlocked(true) }, onClose = { blocking = false })
    }
    if (reporting) ReportDialog(ReportOf.person(personId)) { reporting = false }
}

@Composable
private fun MessageRow(message: DirectMessage, personId: String, onOpening: (String) -> Unit) {
    val colors = MaterialTheme.colorScheme
    Box(Modifier.fillMaxWidth(), contentAlignment = if (message.mine) Alignment.CenterEnd else Alignment.CenterStart) {
        Column(Modifier.widthIn(max = 300.dp), horizontalAlignment = if (message.mine) Alignment.End else Alignment.Start) {
            message.opening?.let { about ->
                Text(
                    about.title,
                    style = MaterialTheme.typography.labelMedium,
                    color = colors.primary,
                    modifier = Modifier.clickable { onOpening(about.id) }.padding(vertical = 4.dp),
                )
            }
            Surface(
                shape = MaterialTheme.shapes.large,
                color = if (message.mine) colors.primary else colors.surfaceContainerHighest,
                contentColor = if (message.mine) colors.onPrimary else colors.onSurface,
            ) {
                Text(message.text, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.padding(horizontal = 14.dp, vertical = 9.dp))
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                MetaText(Dates.ago(message.at))
                if (!message.mine) ReportLink(ReportOf.message(message.id, with = personId))
            }
        }
    }
}

@Composable
private fun Composer(busy: Boolean, onSend: (String, () -> Unit) -> Unit) {
    var text by rememberSaveable { mutableStateOf("") }
    Row(
        Modifier.fillMaxWidth().padding(horizontal = 8.dp, vertical = 6.dp),
        verticalAlignment = Alignment.Bottom,
    ) {
        OutlinedTextField(
            value = text,
            onValueChange = { text = it.take(Messaging.TEXT_MAX) },
            placeholder = { Text("Write a message…") },
            maxLines = 4,
            keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences),
            modifier = Modifier.weight(1f),
        )
        IconButton(onClick = { onSend(text) { text = "" } }, enabled = !busy && text.isNotBlank()) {
            Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "Send")
        }
    }
}
