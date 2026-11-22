package com.krbavcic.logosphere.ui.me

import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
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
import com.krbavcic.logosphere.core.model.OwnProfile
import com.krbavcic.logosphere.data.Change
import com.krbavcic.logosphere.ui.LoadViewModel
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.common.BackTopBar
import com.krbavcic.logosphere.ui.common.LoadContent
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.PhotoField
import com.krbavcic.logosphere.ui.common.PrimaryAction
import com.krbavcic.logosphere.ui.common.ScreenPadding
import com.krbavcic.logosphere.ui.common.SnackbarMessages
import com.krbavcic.logosphere.ui.common.readable
import com.krbavcic.logosphere.ui.common.rememberPhotoTaker
import com.krbavcic.logosphere.ui.common.rememberPicturePicker
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.receiveAsFlow
import com.krbavcic.logosphere.core.logic.PlaceDraft
import com.krbavcic.logosphere.core.logic.Places
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.PlaceSettings
import com.krbavcic.logosphere.ui.common.PlaceDraftSaver
import com.krbavcic.logosphere.ui.common.PlaceFields

/** [place] is null when it didn't load: then it's left as it is. */
data class EditableProfile(val profile: OwnProfile, val place: PlaceSettings?)

class EditProfileViewModel(private val app: AppContainer) : LoadViewModel<EditableProfile>() {
    private val _saved = Channel<Unit>(Channel.BUFFERED)
    val saved = _saved.receiveAsFlow()

    init {
        load()
    }

    override suspend fun fetch(force: Boolean): EditableProfile {
        val profile = app.api.ownProfile()
        return EditableProfile(profile, runCatching { app.api.place(Places.PEOPLE, profile.userId) }.getOrNull())
    }

    fun save(name: String, surname: String, place: PlaceDraft?, photo: Uri?) {
        if (name.isBlank()) {
            say("Your first name can't be empty.")
            return
        }
        place?.problem?.let { return say(it) }
        val moved = place?.changed == true
        act(onSuccess = {
            app.session.refresh()
            app.changes.emit(Change.Profile)
            if (moved) {
                // Every distance follows from where you are.
                app.openings.invalidate()
                app.communities.invalidate(CommunityKind.Sphere)
                app.changes.emit(Change.Openings)
                app.changes.emit(Change.Communities)
            }
            _saved.send(Unit)
        }) {
            val me = current?.profile?.userId
            val picture = photo?.let { app.pictures.read(it) }
            app.api.updateProfile(name, surname, picture)
            if (moved && me != null) app.api.savePlace(Places.PEOPLE, me, place)
            if (me != null && picture != null) app.pictures.replaced(app.api.avatarUrl(me))
        }
    }
}

/** Your name, where you are and your photo (the web's Settings and profile editor in one). */
@Composable
fun EditProfileScreen() {
    val app = LocalAppContainer.current
    val vm: EditProfileViewModel = viewModel { EditProfileViewModel(app) }
    val navigator = LocalNavigator.current
    val state by vm.state.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    SnackbarMessages(vm.messages, snackbar)
    LaunchedEffect(vm) { vm.saved.collect { navigator.back() } }

    Scaffold(
        topBar = { BackTopBar("Edit profile", navigator::back) },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        LoadContent(state, onRetry = vm::load, modifier = Modifier.padding(padding)) { data ->
            val profile = data.profile
            var name by rememberSaveable { mutableStateOf(profile.name.orEmpty()) }
            var surname by rememberSaveable { mutableStateOf(profile.surname.orEmpty()) }
            var place by rememberSaveable(stateSaver = PlaceDraftSaver) {
                mutableStateOf(data.place?.let { PlaceDraft.of(it, person = true) } ?: PlaceDraft(person = true))
            }
            var photo by rememberSaveable { mutableStateOf<Uri?>(null) }
            val pick = rememberPicturePicker { photo = it }
            val take = rememberPhotoTaker { photo = it }
            Column(
                Modifier
                    .padding(padding)
                    .imePadding()
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = ScreenPadding, vertical = 8.dp)
                    .readable(),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                PhotoField(photo, profile.userId, profile.displayName, onPick = pick, onTake = take)
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("First name") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Words),
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = surname,
                    onValueChange = { surname = it },
                    label = { Text("Last name") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Words),
                    modifier = Modifier.fillMaxWidth(),
                )
                PlaceFields(place.takeIf { data.place != null }, { place = it }, "Where you are")
                OutlinedTextField(
                    value = profile.email.orEmpty(),
                    onValueChange = {},
                    label = { Text("Email") },
                    enabled = false,
                    singleLine = true,
                    supportingText = { Text("Email can't be changed here.") },
                    modifier = Modifier.fillMaxWidth(),
                )
                PrimaryAction("Save changes", busy = busy, enabled = name.isNotBlank(), onClick = { vm.save(name, surname, place.takeIf { data.place != null }, photo) })
                MetaText("Everything else about you lives on your Meaning Graph, on the Me tab.", maxLines = 2)
            }
        }
    }
}
