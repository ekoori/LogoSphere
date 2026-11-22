package com.krbavcic.logosphere.ui.communities

import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.krbavcic.logosphere.AppContainer
import com.krbavcic.logosphere.core.logic.Membership
import com.krbavcic.logosphere.core.logic.Roles
import com.krbavcic.logosphere.core.model.Community
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.NewCommunity
import com.krbavcic.logosphere.data.Change
import com.krbavcic.logosphere.ui.LoadViewModel
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.common.BackTopBar
import com.krbavcic.logosphere.ui.common.BannerField
import com.krbavcic.logosphere.ui.common.Choice
import com.krbavcic.logosphere.ui.common.LoadContent
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.Picker
import com.krbavcic.logosphere.ui.common.PrimaryAction
import com.krbavcic.logosphere.ui.common.ScreenPadding
import com.krbavcic.logosphere.ui.common.SegmentedTabs
import com.krbavcic.logosphere.ui.common.SnackbarMessages
import com.krbavcic.logosphere.ui.common.readable
import com.krbavcic.logosphere.ui.common.rememberPhotoTaker
import com.krbavcic.logosphere.ui.common.rememberPicturePicker
import kotlinx.coroutines.async
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.receiveAsFlow
import com.krbavcic.logosphere.ui.common.LocalSimple
import com.krbavcic.logosphere.ui.common.MoreInAdvanced

/** Spheres a new alliance or project may live in, and the alliances a project may be run for. */
data class FoundingPlaces(val spheres: List<Community>, val managedAlliances: List<Community>)

class NewCommunityViewModel(private val app: AppContainer) : LoadViewModel<FoundingPlaces>() {
    private val _created = Channel<Community>(Channel.BUFFERED)
    val created = _created.receiveAsFlow()

    init {
        load()
    }

    override suspend fun fetch(force: Boolean): FoundingPlaces = coroutineScope {
        val user = app.session.user
        val admin = user?.isPlatformAdmin == true
        val spheres = async { app.communities.list(CommunityKind.Sphere, force) }
        val alliances = async { app.communities.list(CommunityKind.Alliance, force) }
        FoundingPlaces(
            // An alliance or project lives in a sphere its founder belongs to.
            spheres = spheres.await().filter { admin || Membership.isMember(it, user?.id) },
            managedAlliances = Membership.managed(alliances.await(), user?.id, admin),
        )
    }

    fun create(new: NewCommunity, banner: Uri?) {
        when {
            new.name.isBlank() -> return say("Give it a name.")
            new.description.isBlank() -> return say("Say in a sentence or two what it's for.")
            new.kind != CommunityKind.Sphere && new.sphereId == null -> return say("Choose the sphere this ${new.kind.noun.lowercase()} belongs to.")
        }
        act {
            val created = app.api.createCommunity(new, banner?.let { app.pictures.read(it) })
            app.communities.invalidate(new.kind)
            app.changes.emit(Change.Communities)
            _created.send(created)
        }
    }
}

/** Starts a sphere, alliance or project (the web's EntityForm). */
@Composable
fun NewCommunityScreen(initialKind: CommunityKind) {
    val app = LocalAppContainer.current
    val vm: NewCommunityViewModel = viewModel { NewCommunityViewModel(app) }
    val navigator = LocalNavigator.current
    val state by vm.state.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    SnackbarMessages(vm.messages, snackbar)
    LaunchedEffect(vm) { vm.created.collect { c -> navigator.replace { community(c.kind, c.id) } } }

    var kindIndex by rememberSaveable { mutableIntStateOf(initialKind.ordinal) }
    val kind = CommunityKind.entries[kindIndex]
    var name by rememberSaveable { mutableStateOf("") }
    var description by rememberSaveable { mutableStateOf("") }
    var location by rememberSaveable { mutableStateOf("") }
    var sphereId by rememberSaveable { mutableStateOf<String?>(null) }
    var allianceId by rememberSaveable { mutableStateOf<String?>(null) }
    var joinPolicy by rememberSaveable { mutableStateOf("open") }
    val simple = LocalSimple.current
    var banner by rememberSaveable { mutableStateOf<Uri?>(null) }
    val pick = rememberPicturePicker { banner = it }
    val take = rememberPhotoTaker { banner = it }

    Scaffold(
        topBar = { BackTopBar("Start a ${kind.noun.lowercase()}", navigator::back) },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        LoadContent(state, onRetry = vm::load, modifier = Modifier.padding(padding)) { places ->
            val sphere = places.spheres.firstOrNull { it.id == sphereId }
            val alliances = places.managedAlliances.filter { sphereId == null || it.parentSphereId == sphereId }
            val noSphere = kind != CommunityKind.Sphere && places.spheres.isEmpty()
            Column(
                Modifier
                    .padding(padding)
                    .imePadding()
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = ScreenPadding, vertical = 8.dp)
                    .readable(),
                verticalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                SegmentedTabs(CommunityKind.entries.map { it.noun }, kindIndex, { kindIndex = it; allianceId = null })
                MetaText(
                    when (kind) {
                        CommunityKind.Sphere -> "A community with shared norms and meaning — a neighbourhood, a club, a congregation."
                        CommunityKind.Alliance -> "A federation or partnership inside a sphere."
                        CommunityKind.Project -> "Shared work with a purpose, inside a sphere."
                    },
                    maxLines = 2,
                )
                BannerField(banner, null, kind, onPick = pick, onTake = take)
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("${kind.noun} name") },
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
                if (kind != CommunityKind.Sphere) {
                    if (noSphere) {
                        MetaText("You need to join a sphere before you can start ${if (kind == CommunityKind.Alliance) "an alliance" else "a project"} in it.", maxLines = 2)
                    } else {
                        Picker(
                            label = if (kind == CommunityKind.Alliance) "Operating sphere" else "Sphere",
                            choices = listOf(Choice(null, "— choose a sphere —")) + places.spheres.map { Choice(it.id, it.name) },
                            selected = sphereId,
                            onSelect = { sphereId = it; allianceId = null },
                        )
                    }
                }
                if (kind == CommunityKind.Project && !simple && alliances.isNotEmpty()) {
                    Picker(
                        label = "On behalf of an alliance (optional)",
                        choices = listOf(Choice(null, "— just me —")) + alliances.map { Choice(it.id, it.name) },
                        selected = allianceId,
                        onSelect = { allianceId = it },
                    )
                }
                if (simple) MoreInAdvanced("Anyone can join. Asking people to wait for approval is")
                if (!simple) Picker(
                    label = "Membership join policy",
                    choices = listOf(
                        Choice("open", "Open — anyone can join directly"),
                        Choice("approval", "Approval required — ${Roles.managerWord(kind)} must approve"),
                    ),
                    selected = joinPolicy,
                    onSelect = { joinPolicy = it ?: "open" },
                )
                OutlinedTextField(
                    value = location,
                    onValueChange = { location = it },
                    label = { Text("Geographical location") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Words),
                    modifier = Modifier.fillMaxWidth(),
                )
                PrimaryAction(
                    "Start the ${kind.noun.lowercase()}",
                    busy = busy,
                    enabled = !noSphere && name.isNotBlank() && description.isNotBlank(),
                    onClick = {
                        vm.create(
                            NewCommunity(
                                kind = kind,
                                name = name,
                                description = description,
                                location = location,
                                sphereId = sphere?.id,
                                sphereName = sphere?.name,
                                ownerAllianceId = allianceId.takeIf { kind == CommunityKind.Project },
                                joinPolicy = joinPolicy,
                            ),
                            banner,
                        )
                    },
                )
                MetaText("You'll be its ${Roles.label(kind, Roles.founderRole(kind)).lowercase()}.", maxLines = 2)
            }
        }
    }
}
