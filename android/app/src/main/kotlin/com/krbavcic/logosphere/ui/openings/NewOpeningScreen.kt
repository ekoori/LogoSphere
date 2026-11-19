package com.krbavcic.logosphere.ui.openings

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
import com.krbavcic.logosphere.core.model.Community
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.NewOpening
import com.krbavcic.logosphere.data.Change
import com.krbavcic.logosphere.ui.LoadViewModel
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.common.BackTopBar
import com.krbavcic.logosphere.ui.common.Choice
import com.krbavcic.logosphere.ui.common.LoadContent
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.Picker
import com.krbavcic.logosphere.ui.common.PrimaryAction
import com.krbavcic.logosphere.ui.common.ScreenPadding
import com.krbavcic.logosphere.ui.common.SegmentedTabs
import com.krbavcic.logosphere.ui.common.SnackbarMessages
import com.krbavcic.logosphere.ui.common.readable
import kotlinx.coroutines.async
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.receiveAsFlow

data class PostingPlaces(val spheres: List<Community>, val projects: List<Community>)

class NewOpeningViewModel(private val app: AppContainer) : LoadViewModel<PostingPlaces>() {
    private val _posted = Channel<Unit>(Channel.BUFFERED)
    val posted = _posted.receiveAsFlow()

    init {
        load()
    }

    override suspend fun fetch(force: Boolean): PostingPlaces = coroutineScope {
        val user = app.session.user
        val spheres = async { app.communities.list(CommunityKind.Sphere, force) }
        val projects = async { app.communities.list(CommunityKind.Project, force) }
        PostingPlaces(
            // Post where you belong (a platform admin may post anywhere).
            spheres = spheres.await().filter { user?.isPlatformAdmin == true || Membership.isMember(it, user?.id) },
            // Closed projects take no new openings.
            projects = projects.await().filter { !it.isClosed },
        )
    }

    fun post(opening: NewOpening) {
        if (opening.title.isBlank()) {
            say("Give it a title.")
            return
        }
        act(onSuccess = {
            app.openings.invalidate()
            app.changes.emit(Change.Openings)
            _posted.send(Unit)
        }) { app.api.createOpening(opening) }
    }
}

@Composable
fun NewOpeningScreen() {
    val app = LocalAppContainer.current
    val vm: NewOpeningViewModel = viewModel { NewOpeningViewModel(app) }
    val navigator = LocalNavigator.current
    val state by vm.state.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    SnackbarMessages(vm.messages, snackbar)
    LaunchedEffect(vm) { vm.posted.collect { navigator.back() } }

    var type by rememberSaveable { mutableIntStateOf(0) }
    var cadence by rememberSaveable { mutableIntStateOf(0) }
    var title by rememberSaveable { mutableStateOf("") }
    var description by rememberSaveable { mutableStateOf("") }
    var sphereId by rememberSaveable { mutableStateOf<String?>(null) }
    var projectName by rememberSaveable { mutableStateOf<String?>(null) }

    Scaffold(
        topBar = { BackTopBar("New opening", navigator::back) },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        LoadContent(state, onRetry = vm::load, modifier = Modifier.padding(padding)) { places ->
            val sphere = places.spheres.firstOrNull { it.id == sphereId }
            // Projects of the chosen sphere; all open projects when none is chosen.
            val projects = places.projects.filter { sphereId == null || it.parentSphereId == sphereId }
            Column(
                Modifier
                    .padding(padding)
                    .imePadding()
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = ScreenPadding, vertical = 8.dp)
                    .readable(),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                SegmentedTabs(listOf("Offer", "Need"), type, { type = it })
                Text(
                    if (type == 0) "Something you can give — goods, skills or time." else "Something you or your community is asking for.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                OutlinedTextField(
                    value = title,
                    onValueChange = { title = it },
                    label = { Text("Title") },
                    placeholder = { Text(if (type == 0) "What are you offering?" else "What are you asking for?") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences),
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = description,
                    onValueChange = { description = it },
                    label = { Text("Description") },
                    placeholder = { Text("More details…") },
                    keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences),
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(min = 120.dp),
                )
                SegmentedTabs(listOf("One-time", "Ongoing"), cadence, { cadence = it })
                MetaText(
                    if (cadence == 0) "Closes once you confirm someone." else "Stays open and can be accepted again and again — like lessons.",
                    maxLines = 2,
                )
                Picker(
                    label = "Sphere",
                    choices = listOf(Choice(null, "None — visible to everyone")) + places.spheres.map { Choice(it.id, it.name) },
                    selected = sphereId,
                    onSelect = {
                        sphereId = it
                        // A project from another sphere no longer fits.
                        if (projectName != null && places.projects.none { p -> p.name == projectName && (it == null || p.parentSphereId == it) }) {
                            projectName = null
                        }
                    },
                )
                Picker(
                    label = "Project (optional)",
                    choices = listOf(Choice(null, "None")) + projects.map { Choice(it.name, it.name) },
                    selected = projectName,
                    onSelect = { projectName = it },
                )
                PrimaryAction(
                    "Post to Openings",
                    busy = busy,
                    enabled = title.isNotBlank(),
                    onClick = {
                        vm.post(
                            NewOpening(
                                type = if (type == 0) "offer" else "need",
                                cadence = if (cadence == 0) "single" else "perpetual",
                                title = title,
                                description = description,
                                sphereId = sphere?.id,
                                sphereName = sphere?.name,
                                projectName = projectName,
                            ),
                        )
                    },
                )
            }
        }
    }
}
