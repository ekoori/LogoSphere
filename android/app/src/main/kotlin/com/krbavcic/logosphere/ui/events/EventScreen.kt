package com.krbavcic.logosphere.ui.events

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.AssistChip
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.krbavcic.logosphere.AppContainer
import com.krbavcic.logosphere.core.logic.EventAnswer
import com.krbavcic.logosphere.core.logic.Events
import com.krbavcic.logosphere.core.logic.Repeats
import com.krbavcic.logosphere.core.model.CommunityEvent
import com.krbavcic.logosphere.core.model.EventTime
import com.krbavcic.logosphere.core.model.ReportOf
import com.krbavcic.logosphere.data.Change
import com.krbavcic.logosphere.ui.LoadViewModel
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.common.Avatar
import com.krbavcic.logosphere.ui.common.BackTopBar
import com.krbavcic.logosphere.ui.common.Banner
import com.krbavcic.logosphere.ui.common.BrandCard
import com.krbavcic.logosphere.ui.common.DemoTag
import com.krbavcic.logosphere.ui.common.ExactSpot
import com.krbavcic.logosphere.ui.common.LinkText
import com.krbavcic.logosphere.ui.common.LoadContent
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.QuietPill
import com.krbavcic.logosphere.ui.common.ReallyDialog
import com.krbavcic.logosphere.ui.common.Refreshable
import com.krbavcic.logosphere.ui.common.ReportLink
import com.krbavcic.logosphere.ui.common.ScreenPadding
import com.krbavcic.logosphere.ui.common.SectionHeading
import com.krbavcic.logosphere.ui.common.SnackbarMessages
import com.krbavcic.logosphere.ui.common.WhereLine

class EventViewModel(private val app: AppContainer, private val id: String) : LoadViewModel<CommunityEvent>() {
    val viewerId: String? get() = app.session.user?.id

    init {
        load()
        reloadOn(app.changes, Change.Events)
    }

    override suspend fun fetch(force: Boolean): CommunityEvent = app.api.event(id)

    private fun changeWith(call: suspend () -> CommunityEvent) = act {
        val saved = call()
        update { saved }
        app.changes.emit(Change.Events)
    }

    fun answer(day: String, answer: EventAnswer?) = changeWith { app.api.replyEvent(id, day, answer) }

    fun cancel(day: String? = null) = changeWith { app.api.cancelEvent(id, day) }

    fun putBack(day: String) = changeWith { app.api.cancelEvent(id, day, cancelled = false) }
}

/** One event: when, where, and who's coming to which date. */
@Composable
fun EventScreen(id: String) {
    val app = LocalAppContainer.current
    val vm: EventViewModel = viewModel(key = "event-$id") { EventViewModel(app, id) }
    val navigator = LocalNavigator.current
    val state by vm.state.collectAsStateWithLifecycle()
    val refreshing by vm.refreshing.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    SnackbarMessages(vm.messages, snackbar)

    Scaffold(
        topBar = { BackTopBar("Event", navigator::back) },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        LoadContent(state, onRetry = vm::load, modifier = Modifier.padding(padding)) { event ->
            Refreshable(refreshing, vm::refresh, Modifier.padding(padding)) { EventContent(event, vm, busy) }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun EventContent(event: CommunityEvent, vm: EventViewModel, busy: Boolean) {
    val app = LocalAppContainer.current
    val navigator = LocalNavigator.current
    val repeats = Repeats.of(event.repeats)
    var cancelAll by rememberSaveable { mutableStateOf(false) }
    var cancelDay by rememberSaveable { mutableStateOf<String?>(null) }
    val inset = Modifier.padding(horizontal = ScreenPadding)

    LazyColumn(contentPadding = PaddingValues(bottom = 32.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item(key = "banner") {
            Banner(
                imageUrl = if (event.hasImage) app.api.eventImageUrl(event.id) else null,
                kind = null,
                height = 180.dp,
                isAi = event.imageIsAi,
                glyph = "◷",
            ) {
                Column(Modifier.align(Alignment.BottomStart).padding(ScreenPadding)) {
                    Text("EVENT", style = MaterialTheme.typography.labelMedium, color = Color(0xFFF3ECDA))
                    Text(event.title, style = MaterialTheme.typography.headlineMedium, color = Color(0xFFFDFAF2))
                }
            }
        }
        item(key = "about") {
            Column(inset, verticalArrangement = Arrangement.spacedBy(8.dp)) {
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    if (event.isDemo) DemoTag()
                    if (event.cancelled) QuietPill("Cancelled") else if (event.over) QuietPill("It's over")
                    if (event.host == null) QuietPill("For everyone")
                }
                event.host?.let { host ->
                    AssistChip(
                        onClick = { navigator.community(host.communityKind, host.id) },
                        label = { Text("${host.communityKind.glyph} ${host.name}") },
                    )
                }
                if (repeats != Repeats.Never) {
                    val last = Events.date(event.until)?.let { ", until ${Events.dateText(it)}" }.orEmpty()
                    Text(Events.repeatText(repeats, Events.date(event.starts)) + last, style = MaterialTheme.typography.titleSmall)
                }
                WhereLine(event.location, event.distance, maxLines = 3)
                if (event.description.isNotBlank()) Text(event.description, style = MaterialTheme.typography.bodyLarge)
                ExactSpot(event.point)
            }
        }
        item(key = "dates") { SectionHeading(if (repeats == Repeats.Never) "When" else "The next dates", inset) }
        itemsIndexed(event.times, key = { _, time -> time.day }) { index, time ->
            DateCard(
                event = event,
                time = time,
                busy = busy,
                first = index == 0,
                onAnswer = { vm.answer(time.day, it) },
                onCancel = { cancelDay = time.day },
                onPutBack = { vm.putBack(time.day) },
                modifier = inset,
            )
        }
        item(key = "foot") {
            Column(inset, verticalArrangement = Arrangement.spacedBy(6.dp)) {
                if (!event.cancelled && !event.over) {
                    MetaText(
                        if (event.host == null) "Every signed-in member can see this event, and who's coming."
                        else "Whoever can see this event sees who's coming.",
                        maxLines = 2,
                    )
                }
                event.creator?.let { who -> LinkText("Put on by ${who.name ?: "a member"}", { navigator.person(who.id) }) }
                event.creator?.takeIf { it.id != vm.viewerId }?.let { who ->
                    OutlinedButton(
                        onClick = { navigator.conversation(who.id, about = "event:${event.id}") },
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text("Message ${who.name ?: "who puts it on"}") }
                }
                if (event.canManage && !event.cancelled) {
                    OutlinedButton(onClick = { navigator.editEvent(event.id) }, modifier = Modifier.fillMaxWidth()) { Text("Change it") }
                    OutlinedButton(onClick = { cancelAll = true }, enabled = !busy, modifier = Modifier.fillMaxWidth()) {
                        Text(if (repeats == Repeats.Never) "Cancel the event" else "Cancel all dates", color = MaterialTheme.colorScheme.error)
                    }
                }
                event.creator?.takeIf { it.id != vm.viewerId }?.let {
                    ReportLink(ReportOf.event(event.id), label = "Report this event")
                }
            }
        }
    }

    if (cancelAll) {
        ReallyDialog(
            title = "Cancel ${event.title}?",
            text = "Those coming are told. A cancelled event stays cancelled.",
            confirm = "Cancel it",
            onConfirm = { vm.cancel() },
            onClose = { cancelAll = false },
        )
    }
    cancelDay?.let { day ->
        ReallyDialog(
            title = "Cancel this date?",
            text = "Those coming that day are told. The other dates stay on.",
            confirm = "Cancel the date",
            onConfirm = { vm.cancel(day) },
            onClose = { cancelDay = null },
        )
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun DateCard(
    event: CommunityEvent,
    time: EventTime,
    busy: Boolean,
    first: Boolean,
    onAnswer: (EventAnswer?) -> Unit,
    onCancel: () -> Unit,
    onPutBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val navigator = LocalNavigator.current
    val told = Events.whenText(time, event.tz)
    val ahead = !event.cancelled && !Events.hasEnded(time)
    val coming = Events.comingText(time)
    var showPeople by rememberSaveable(time.day) { mutableStateOf(first) }

    BrandCard(modifier.fillMaxWidth()) {
        Column(Modifier.padding(horizontal = 14.dp, vertical = 10.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(
                told.text,
                style = MaterialTheme.typography.titleSmall,
                textDecoration = if (time.skipped) TextDecoration.LineThrough else null,
            )
            told.zoneNote?.let { MetaText(it) }
            if (time.skipped) Text("Not on", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.error)
            if (ahead && !time.skipped) {
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    EventAnswer.entries.forEach { answer ->
                        val mine = time.myAnswer == answer.key
                        FilterChip(
                            selected = mine,
                            enabled = !busy,
                            onClick = { onAnswer(if (mine) null else answer) },
                            label = { Text(answer.label) },
                        )
                    }
                }
            }
            if (coming.isNotEmpty()) {
                LinkText(coming + if (showPeople) "  ▴" else "  ▾", { showPeople = !showPeople })
                if (showPeople) {
                    FlowRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        time.people.forEach { person ->
                            Row(
                                Modifier
                                    .clickable(role = Role.Button) { navigator.person(person.id) }
                                    .padding(vertical = 8.dp),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(6.dp),
                            ) {
                                Avatar(person.id, person.name, size = 28.dp)
                                Text(person.name, style = MaterialTheme.typography.bodyMedium)
                                if (person.answer == EventAnswer.Maybe.key) MetaText("maybe")
                            }
                        }
                    }
                }
            }
            if (event.canManage && ahead && event.repeats != Repeats.Never.key) {
                if (time.skipped) {
                    LinkText("It's on after all", onPutBack, enabled = !busy)
                } else {
                    LinkText("Cancel this date", onCancel, enabled = !busy)
                }
            }
        }
    }
}
