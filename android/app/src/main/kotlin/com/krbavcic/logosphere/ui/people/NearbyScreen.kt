package com.krbavcic.logosphere.ui.people

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.krbavcic.logosphere.AppContainer
import com.krbavcic.logosphere.core.logic.Places
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.Nearby
import com.krbavcic.logosphere.data.Change
import com.krbavcic.logosphere.ui.LoadViewModel
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.common.Avatar
import com.krbavcic.logosphere.ui.common.BackTopBar
import com.krbavcic.logosphere.ui.common.Choice
import com.krbavcic.logosphere.ui.common.DemoTag
import com.krbavcic.logosphere.ui.common.EmptyNote
import com.krbavcic.logosphere.ui.common.GroupAvatar
import com.krbavcic.logosphere.ui.common.LinkText
import com.krbavcic.logosphere.ui.common.LoadContent
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.PersonaTag
import com.krbavcic.logosphere.ui.common.Picker
import com.krbavcic.logosphere.ui.common.Refreshable
import com.krbavcic.logosphere.ui.common.ScreenPadding
import com.krbavcic.logosphere.ui.common.SectionHeading
import com.krbavcic.logosphere.ui.common.SnackbarMessages

class NearbyViewModel(private val app: AppContainer) : LoadViewModel<Nearby>() {
    private var km = 25

    init {
        load()
        reloadOn(app.changes, Change.Profile)
    }

    override suspend fun fetch(force: Boolean): Nearby = app.api.nearby(km)

    fun within(km: Int) {
        if (km == this.km) return
        this.km = km
        load()
    }
}

/** Who and what is near you: members who chose to be findable, and spheres, as rough distances. */
@Composable
fun NearbyScreen() {
    val app = LocalAppContainer.current
    val vm: NearbyViewModel = viewModel { NearbyViewModel(app) }
    val navigator = LocalNavigator.current
    val state by vm.state.collectAsStateWithLifecycle()
    val refreshing by vm.refreshing.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    SnackbarMessages(vm.messages, snackbar)

    Scaffold(
        topBar = { BackTopBar("Near you", navigator::back) },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        LoadContent(state, onRetry = vm::load, modifier = Modifier.padding(padding)) { data ->
            Refreshable(refreshing, vm::refresh, Modifier.padding(padding)) {
                LazyColumn(
                    contentPadding = PaddingValues(start = ScreenPadding, end = ScreenPadding, top = 4.dp, bottom = 32.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    item(key = "about") {
                        MetaText("Members appear only if they chose to be findable, and only ever as a rough distance.", maxLines = 3)
                    }
                    if (!data.hasPlace) {
                        item(key = "no-place") {
                            Column(Modifier.padding(vertical = 16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                                Text(
                                    "To see who and what is near you, say where you are. A suburb or town is plenty.",
                                    style = MaterialTheme.typography.bodyLarge,
                                )
                                Button(onClick = navigator::editProfile, modifier = Modifier.fillMaxWidth()) {
                                    Text("Put yourself on the map")
                                }
                            }
                        }
                        return@LazyColumn
                    }
                    item(key = "within") {
                        Picker(
                            label = "Within",
                            choices = Places.NEAR_KM.map { Choice(it.toString(), "$it km") },
                            selected = data.km.toString(),
                            onSelect = { it?.toIntOrNull()?.let(vm::within) },
                        )
                    }
                    if (!data.findable) {
                        item(key = "not-findable") {
                            LinkText("Others can't find you here. Let members nearby find you →", navigator::editProfile)
                        }
                    }
                    item(key = "people") { SectionHeading("People", Modifier.padding(top = 8.dp)) }
                    if (data.people.isEmpty()) {
                        item(key = "nobody") { EmptyNote("Nobody who chose to be findable is this near yet.") }
                    }
                    items(data.people, key = { "person-" + it.id }) { person ->
                        Row(
                            Modifier
                                .fillMaxWidth()
                                .clickable { navigator.person(person.id) }
                                .padding(vertical = 8.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(12.dp),
                        ) {
                            Avatar(person.id, person.name, size = 40.dp)
                            Column(Modifier.weight(1f)) {
                                Text(person.name, style = MaterialTheme.typography.titleSmall)
                                if (person.isAgent) PersonaTag(compact = true)
                                person.location?.let { MetaText(it) }
                            }
                            MetaText(person.distance.text)
                        }
                    }
                    item(key = "spheres") { SectionHeading("Spheres", Modifier.padding(top = 8.dp)) }
                    if (data.spheres.isEmpty()) {
                        item(key = "no-spheres") { EmptyNote("No sphere this near has said where it is.") }
                    }
                    items(data.spheres, key = { "sphere-" + it.id }) { sphere ->
                        Row(
                            Modifier
                                .fillMaxWidth()
                                .clickable { navigator.community(CommunityKind.Sphere, sphere.id) }
                                .padding(vertical = 8.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(12.dp),
                        ) {
                            GroupAvatar(CommunityKind.Sphere, size = 40.dp)
                            Column(Modifier.weight(1f)) {
                                Text(sphere.name, style = MaterialTheme.typography.titleSmall)
                                if (sphere.isDemo) DemoTag()
                                MetaText(
                                    listOfNotNull(
                                        sphere.location,
                                        "${sphere.memberCount} member${if (sphere.memberCount == 1) "" else "s"}",
                                        "you're in it".takeIf { sphere.isMember },
                                    ).joinToString(" · "),
                                    maxLines = 2,
                                )
                            }
                            MetaText(sphere.distance.text)
                        }
                    }
                }
            }
        }
    }
}
