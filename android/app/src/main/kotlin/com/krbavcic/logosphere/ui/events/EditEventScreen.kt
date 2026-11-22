package com.krbavcic.logosphere.ui.events

import android.net.Uri
import android.widget.Toast
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.Saver
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.krbavcic.logosphere.AppContainer
import com.krbavcic.logosphere.core.api.AppProblem
import com.krbavcic.logosphere.core.api.LogoSphereJson
import com.krbavcic.logosphere.core.logic.EventDraft
import com.krbavcic.logosphere.core.logic.Events
import com.krbavcic.logosphere.core.logic.Membership
import com.krbavcic.logosphere.core.logic.PlaceDraft
import com.krbavcic.logosphere.core.logic.Places
import com.krbavcic.logosphere.core.logic.Repeats
import com.krbavcic.logosphere.core.model.Community
import com.krbavcic.logosphere.core.model.CommunityEvent
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.PlaceSettings
import com.krbavcic.logosphere.data.Change
import com.krbavcic.logosphere.ui.LoadViewModel
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.common.AiPictureButton
import com.krbavcic.logosphere.ui.common.BackTopBar
import com.krbavcic.logosphere.ui.common.BannerField
import com.krbavcic.logosphere.ui.common.Choice
import com.krbavcic.logosphere.ui.common.DateField
import com.krbavcic.logosphere.ui.common.LinkText
import com.krbavcic.logosphere.ui.common.LoadContent
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.Picker
import com.krbavcic.logosphere.ui.common.PlaceDraftSaver
import com.krbavcic.logosphere.ui.common.PlaceFields
import com.krbavcic.logosphere.ui.common.PrimaryAction
import com.krbavcic.logosphere.ui.common.ScreenPadding
import com.krbavcic.logosphere.ui.common.SnackbarMessages
import com.krbavcic.logosphere.ui.common.TimeField
import com.krbavcic.logosphere.ui.common.ZoneDialog
import com.krbavcic.logosphere.ui.common.readable
import com.krbavcic.logosphere.ui.common.rememberPhotoTaker
import com.krbavcic.logosphere.ui.common.rememberPicturePicker
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.receiveAsFlow
import kotlin.coroutines.cancellation.CancellationException

private const val EVERYONE = "everyone"
private const val TITLE_MAX = 120
private const val DESCRIPTION_MAX = 4000

private val EventDraftSaver: Saver<EventDraft, String> = Saver(
    save = { LogoSphereJson.encodeToString(EventDraft.serializer(), it) },
    restore = { LogoSphereJson.decodeFromString(EventDraft.serializer(), it) },
)

data class EventFormData(
    val event: CommunityEvent?,
    /** An existing one's place; null when that didn't load. */
    val storedPlace: PlaceSettings?,
    /** The group it was started from. */
    val group: Community?,
    /** Else the groups to choose from. */
    val groups: List<Community>,
)

/** Saved, with what of it didn't (its place, its picture). */
data class SavedEvent(val id: String, val lost: List<String>)

class EditEventViewModel(
    private val app: AppContainer,
    private val eventId: String?,
    private val groupKind: CommunityKind?,
    private val groupId: String?,
) : LoadViewModel<EventFormData>() {
    private val _saved = Channel<SavedEvent>(Channel.BUFFERED)
    val saved = _saved.receiveAsFlow()

    init {
        load()
    }

    override suspend fun fetch(force: Boolean): EventFormData {
        if (eventId != null) {
            val event = app.api.event(eventId)
            if (event.cancelled) throw AppProblem("It was cancelled, so it can't be changed.")
            if (!event.canManage) throw AppProblem("Only whoever put it on, or the group's managers, can change it.")
            val place = try {
                app.api.place(Places.EVENTS, eventId)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                logFailure("event place", e)
                null
            }
            return EventFormData(event, place, null, emptyList())
        }
        if (groupKind != null && groupId != null) {
            return EventFormData(null, null, app.api.community(groupKind, groupId), emptyList())
        }
        val me = app.session.user?.id
        val mine = app.communities.all(force).filter { !it.isClosed && Membership.isMember(it, me) }
        return EventFormData(null, null, null, mine)
    }

    fun save(draft: EventDraft, hostId: String?, place: PlaceDraft, picture: Uri?) {
        draft.problem?.let { return say(it) }
        place.problem?.let { return say(it) }
        val lost = mutableListOf<String>()
        var id = eventId
        act(onSuccess = {
            app.changes.emit(Change.Events)
            id?.let { _saved.send(SavedEvent(it, lost)) }
        }) {
            // Read first, so a bad file stops it before anything is saved.
            val upload = picture?.let { app.pictures.read(it) }
            val saved = if (eventId == null) app.api.createEvent(draft, hostId) else app.api.editEvent(eventId, draft)
            id = saved.id
            // It's saved from here: what follows can fail without it being made twice.
            if (place.changed) {
                try {
                    app.api.savePlace(Places.EVENTS, saved.id, place)
                } catch (e: CancellationException) {
                    throw e
                } catch (e: Exception) {
                    logFailure("event place", e)
                    lost += "where it is"
                }
            }
            if (upload != null) {
                try {
                    app.api.setEventImage(saved.id, upload)
                    app.pictures.replaced(app.api.eventImageUrl(saved.id))
                } catch (e: CancellationException) {
                    throw e
                } catch (e: Exception) {
                    logFailure("event picture", e)
                    lost += "the picture"
                }
            }
        }
    }
}

/** Putting on an event ([groupId]'s, when it began there), or changing one. */
@Composable
fun EditEventScreen(eventId: String? = null, groupKind: CommunityKind? = null, groupId: String? = null) {
    val app = LocalAppContainer.current
    val vm: EditEventViewModel = viewModel(key = "edit-event-$eventId-$groupId") {
        EditEventViewModel(app, eventId, groupKind, groupId)
    }
    val navigator = LocalNavigator.current
    val state by vm.state.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    SnackbarMessages(vm.messages, snackbar)
    val context = LocalContext.current
    LaunchedEffect(vm) {
        vm.saved.collect { saved ->
            if (saved.lost.isNotEmpty()) {
                val what = saved.lost.joinToString(" and ")
                Toast.makeText(context, "Saved, but $what didn't. Press Change it to try again.", Toast.LENGTH_LONG).show()
            }
            if (eventId != null) navigator.back() else navigator.replace { event(saved.id) }
        }
    }

    Scaffold(
        topBar = { BackTopBar(if (eventId == null) "Put on an event" else "Change the event", navigator::back) },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        LoadContent(state, onRetry = vm::load, modifier = Modifier.padding(padding)) { data ->
            EventForm(data, vm, busy, Modifier.padding(padding))
        }
    }
}

@Composable
private fun EventForm(data: EventFormData, vm: EditEventViewModel, busy: Boolean, modifier: Modifier = Modifier) {
    val app = LocalAppContainer.current
    val event = data.event
    var draft by rememberSaveable(stateSaver = EventDraftSaver) {
        mutableStateOf(event?.let { EventDraft.of(it) } ?: EventDraft(tz = Events.deviceZone()))
    }
    var place by rememberSaveable(stateSaver = PlaceDraftSaver) {
        mutableStateOf(data.storedPlace?.let { PlaceDraft.of(it) } ?: PlaceDraft())
    }
    var chosen by rememberSaveable { mutableStateOf<String?>(null) }
    var picture by rememberSaveable { mutableStateOf<Uri?>(null) }
    var pictureIsAi by rememberSaveable { mutableStateOf(false) }
    var zoneOpen by rememberSaveable { mutableStateOf(false) }
    val pick = rememberPicturePicker { picture = it; pictureIsAi = false }
    val take = rememberPhotoTaker { picture = it; pictureIsAi = false }

    val choosing = event == null && data.group == null && data.groups.isNotEmpty()
    // With no groups there's only everyone; otherwise it's chosen, never assumed.
    val host = event?.host?.id ?: data.group?.id ?: chosen ?: EVERYONE.takeIf { !choosing }
    val hostKind = event?.host?.communityKind ?: data.group?.kind ?: data.groups.firstOrNull { it.id == host }?.kind
    val repeats = Repeats.of(draft.repeats)
    val first = Events.date(draft.day)

    Column(
        modifier
            .imePadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = ScreenPadding, vertical = 8.dp)
            .readable(),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        (event?.host?.name ?: data.group?.name)?.let {
            Text("For $it", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary)
        }
        if (choosing) {
            Picker(
                label = "Who is it for?",
                choices = listOf(Choice(null, "Choose…")) +
                    data.groups.map { Choice(it.id, "${it.name} (${it.kind.noun.lowercase()})") } +
                    Choice(EVERYONE, "Everyone on LogoSphere"),
                selected = chosen,
                onSelect = { chosen = it },
            )
        }
        if (host != null) {
            MetaText(
                when (hostKind) {
                    null -> "Every signed-in member will see it, where it is and who is coming."
                    CommunityKind.Sphere -> "The sphere's members will see it, and who is coming."
                    else -> "The members of the ${hostKind.noun.lowercase()}'s sphere will see it, and who is coming."
                },
                maxLines = 3,
            )
        }
        OutlinedTextField(
            value = draft.title,
            onValueChange = { draft = draft.copy(title = it.take(TITLE_MAX)) },
            label = { Text("What is it?") },
            placeholder = { Text("e.g. Mending night") },
            singleLine = true,
            keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences),
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = draft.description,
            onValueChange = { draft = draft.copy(description = it.take(DESCRIPTION_MAX)) },
            label = { Text("More about it (optional)") },
            placeholder = { Text("What to bring, who it suits, how to get in") },
            keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences),
            modifier = Modifier.fillMaxWidth().heightIn(min = 110.dp),
        )
        DateField("Day", first, { draft = draft.copy(day = it.toString()) })
        TimeField("Starts at", Events.clock(draft.clock), { draft = draft.copy(clock = "%02d:%02d".format(java.util.Locale.ROOT, it.hour, it.minute)) })
        Picker(
            label = "Lasts",
            choices = Events.lengthChoices(draft.lengthMin).map { Choice(it.toString(), Events.lengthText(it)) },
            selected = draft.lengthMin.toString(),
            onSelect = { value -> value?.toIntOrNull()?.let { draft = draft.copy(lengthMin = it) } },
        )
        Picker(
            label = "Repeats",
            choices = Repeats.entries.map { Choice(it.key, Events.repeatText(it, first)) },
            selected = draft.repeats,
            onSelect = { value -> value?.let { draft = draft.copy(repeats = it) } },
        )
        if (repeats != Repeats.Never) {
            DateField(
                label = "Until (optional)",
                value = Events.date(draft.until),
                onChange = { draft = draft.copy(until = it.toString()) },
                empty = "No last date",
                onClear = { draft = draft.copy(until = null) },
            )
        }
        LinkText("Times are ${draft.tz.replace('_', ' ')} time. Change", { zoneOpen = true })
        PlaceFields(if (event != null && data.storedPlace == null) null else place, { place = it }, "Where (optional)")
        BannerField(
            picked = picture,
            currentUrl = if (event?.hasImage == true) app.api.eventImageUrl(event.id) else null,
            kind = null,
            onPick = pick,
            onTake = take,
            label = "picture",
            isAi = if (picture != null) pictureIsAi else event?.imageIsAi == true,
        )
        AiPictureButton("event", draft.title, draft.description, onUse = { picture = it; pictureIsAi = true })
        PrimaryAction(
            if (event == null) "Put it on" else "Save the changes",
            busy = busy,
            enabled = draft.title.isNotBlank() && host != null,
            onClick = { vm.save(draft, host?.takeIf { it != EVERYONE }, place, picture) },
        )
    }

    if (zoneOpen) {
        ZoneDialog(draft.tz, onChoose = { draft = draft.copy(tz = it); zoneOpen = false }, onClose = { zoneOpen = false })
    }
}
