package com.krbavcic.logosphere.ui.common

import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.saveable.Saver
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.dp
import com.krbavcic.logosphere.core.api.LogoSphereJson
import com.krbavcic.logosphere.core.logic.PinPrecision
import com.krbavcic.logosphere.core.logic.PlaceDraft
import com.krbavcic.logosphere.core.logic.Places
import com.krbavcic.logosphere.core.model.Attribution
import com.krbavcic.logosphere.core.model.Distance
import com.krbavcic.logosphere.core.model.FoundPlace
import com.krbavcic.logosphere.core.model.GeoPoint
import com.krbavcic.logosphere.core.model.Place
import com.krbavcic.logosphere.data.DeviceLocation
import com.krbavcic.logosphere.ui.LocalAppContainer
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlin.coroutines.cancellation.CancellationException
import kotlin.math.ceil

private const val SEARCH_AFTER_MS = 300L
private const val FOUND_SHOWN = 6

/** A place being edited, kept through rotation and the trip to a permission prompt. */
val PlaceDraftSaver: Saver<PlaceDraft, String> = Saver(
    save = { LogoSphereJson.encodeToString(PlaceDraft.serializer(), it) },
    restore = { LogoSphereJson.decodeFromString(PlaceDraft.serializer(), it) },
)

private fun howFarOff(metres: Float): String =
    if (metres >= 1000) "${ceil(metres / 1000.0).toInt()} km" else "${ceil(metres.toDouble()).toInt()} m"

/** A place in the form that saves it: where, and for yourself whether members nearby may find you. */
@Composable
fun PlaceFields(draft: PlaceDraft?, onChange: (PlaceDraft) -> Unit, label: String, modifier: Modifier = Modifier) {
    if (draft == null) {
        MetaText("The place didn't load, so it stays as it was.", modifier = modifier, maxLines = 2)
        return
    }
    val latest by rememberUpdatedState(draft)
    Column(modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        PlacePicker(draft.place, { onChange(latest.copy(place = it)) }, label, person = draft.person)
        if (draft.person) {
            val linked = Places.hasPoint(draft.place)
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("Members nearby can find me", style = MaterialTheme.typography.titleSmall)
                    MetaText(
                        if (linked) "They see your name, the words above and a rough distance. Never the spot."
                        else "Put yourself on the map first.",
                        maxLines = 3,
                    )
                }
                Switch(checked = draft.findable, onCheckedChange = { onChange(draft.copy(findableChosen = it)) }, enabled = linked)
            }
        }
    }
}

/**
 * Where something is, as exactly as someone wants: a name from the offline search, where the
 * phone is, or a pin on a map. It only holds the choice; whoever uses it saves it.
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
fun PlacePicker(value: Place?, onChange: (Place?) -> Unit, label: String, modifier: Modifier = Modifier, person: Boolean = false) {
    val app = LocalAppContainer.current
    val context = LocalContext.current
    val uriHandler = LocalUriHandler.current
    val scope = rememberCoroutineScope()
    // The phone and the name lookup answer later: they go by what's true then.
    val latest by rememberUpdatedState(value)
    val change by rememberUpdatedState(onChange)

    var precisionKey by rememberSaveable { mutableStateOf((PinPrecision.of(value?.precision) ?: PinPrecision.Km1).key) }
    val precision = PinPrecision.of(precisionKey) ?: PinPrecision.Km1
    var typed by remember { mutableStateOf<String?>(null) }
    var found by remember { mutableStateOf(emptyList<FoundPlace>()) }
    var credit by remember { mutableStateOf<Attribution?>(null) }
    var moveIt by remember { mutableStateOf(false) }
    var locating by remember { mutableStateOf(false) }
    var problem by remember { mutableStateOf<String?>(null) }
    var mapOpen by rememberSaveable { mutableStateOf(false) }

    LaunchedEffect(value) {
        if (Places.isPin(value)) PinPrecision.of(value?.precision)?.let { precisionKey = it.key }
    }
    LaunchedEffect(typed) {
        val text = typed?.trim().orEmpty()
        if (text.length < 2) {
            found = emptyList()
            return@LaunchedEffect
        }
        delay(SEARCH_AFTER_MS)
        try {
            val answer = app.api.searchPlaces(text)
            found = answer.results.take(FOUND_SHOWN)
            credit = answer.attribution
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            found = emptyList() // the words still do
        }
    }

    fun putPin(lat: Double, lon: Double) {
        val chosen = PinPrecision.of(precisionKey) ?: PinPrecision.Km1
        val pin = Place(label = latest?.label, lat = lat, lon = lon, precision = chosen.key, fresh = true)
        typed = null
        moveIt = false
        problem = null
        change(pin)
        if (!pin.label.isNullOrBlank()) return
        scope.launch {
            try {
                // A town's name to begin with. For that a square kilometre is close enough.
                val rough = Places.coarsened(lat, lon, maxOf(chosen.km ?: 0.0, 1.0))
                val name = app.api.nearestPlaces(rough.lat, rough.lon).results.firstOrNull()?.label
                val now = latest
                if (name != null && now != null && now.lat == lat && now.lon == lon && now.label.isNullOrBlank()) {
                    change(now.copy(label = name))
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                // They can name it themselves.
            }
        }
    }

    fun locate() {
        val wanted = PinPrecision.of(precisionKey) ?: PinPrecision.Km1
        locating = true
        problem = null
        scope.launch {
            val here = try {
                DeviceLocation.read(context, wanted)
            } finally {
                locating = false
            }
            if (here == null) {
                problem = "We couldn't get where you are. Is Location switched on? You can also choose on a map."
                return@launch
            }
            putPin(here.latitude, here.longitude)
            if (here.hasAccuracy() && here.accuracy > wanted.roomMetres) {
                problem = "Your phone only knew where you are to within ${howFarOff(here.accuracy)}. You can check it on the map."
            }
        }
    }

    val ask = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) {
        if (DeviceLocation.mayRead(context)) {
            locate()
        } else {
            problem = "LogoSphere may not see where you are. Choose on a map instead."
        }
    }

    val words = value?.label.orEmpty()
    val isPin = Places.isPin(value)
    Column(modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        OutlinedTextField(
            value = words,
            onValueChange = {
                // Words for a pin are just its name; anything else may be a place to look up.
                typed = if (Places.isPin(latest)) null else it
                change(Places.withWords(latest, it))
            },
            label = { Text(label) },
            placeholder = { Text(if (person) "Your suburb or town" else "The hall, the suburb or the town") },
            singleLine = true,
            isError = isPin && words.isBlank(),
            keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Words),
            modifier = Modifier.fillMaxWidth(),
        )
        if (found.isNotEmpty()) {
            Surface(
                shape = MaterialTheme.shapes.medium,
                color = MaterialTheme.colorScheme.surfaceContainerLow,
                border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
            ) {
                Column {
                    found.forEachIndexed { index, place ->
                        if (index > 0) HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                        Row(
                            Modifier
                                .fillMaxWidth()
                                .clickable(role = Role.Button) {
                                    change(Places.found(place))
                                    typed = null
                                    moveIt = false
                                    problem = null
                                }
                                .padding(horizontal = 12.dp, vertical = 12.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text(place.label, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.weight(1f))
                            MetaText(place.precision, Modifier.padding(start = 8.dp))
                        }
                    }
                }
            }
            credit?.let { by -> LinkText(by.text, onClick = { runCatching { uriHandler.openUri(by.url) } }) }
        }
        if (person) MetaText("Other members see these words: a suburb or town is plenty.", maxLines = 2)
        Places.linkedTo(value)?.let {
            Text(
                it,
                style = MaterialTheme.typography.labelLarge,
                color = if (Places.hasPoint(value)) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite },
            )
        }
        if (isPin && words.isBlank()) Warning("Give it a name above: that is what others see.")
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(
                onClick = {
                    if (DeviceLocation.allowed(context, precision)) locate() else ask.launch(DeviceLocation.permissionsFor(precision))
                },
                enabled = !locating,
            ) { Text(if (locating) "Finding you…" else "Use where I am now") }
            OutlinedButton(onClick = { mapOpen = true }) { Text("Choose on a map") }
            if (Places.hasPoint(value)) {
                TextButton(
                    onClick = {
                        change(if (words.isBlank()) null else Place(label = words))
                        typed = null
                        moveIt = false
                    },
                ) { Text("Take it off the map") }
            }
        }
        problem?.let { Warning(it) }
        if (isPin) {
            Picker(
                label = "How exact?",
                choices = PinPrecision.entries.map { Choice(it.key, it.label) },
                selected = precisionKey,
                onSelect = { key ->
                    val next = PinPrecision.of(key) ?: return@Picker
                    val now = latest ?: return@Picker
                    val was = PinPrecision.of(now.precision)
                    precisionKey = next.key
                    if (!now.fresh && was != null && next.isFinerThan(was)) {
                        // What was stored is only the middle of its square: it can't be more exact by itself.
                        moveIt = true
                        mapOpen = true
                    } else {
                        moveIt = false
                        change(now.copy(precision = next.key))
                    }
                },
            )
            MetaText(
                when {
                    precision != PinPrecision.Exact -> "It is rounded to that before it is saved."
                    person -> "It is saved exactly. Other members never get it: they only see a rough distance."
                    else -> "Everyone this is shown to will see the exact spot. Think twice if it is someone's home."
                },
                maxLines = 3,
            )
        }
        if (moveIt) Warning("To be more exact, put the pin again on the map.")
    }

    if (mapOpen) {
        MapPickerDialog(
            near = value,
            precision = precision,
            onPick = { lat, lon ->
                mapOpen = false
                putPin(lat, lon)
            },
            onDismiss = { mapOpen = false },
        )
    }
}

@Composable
private fun Warning(text: String) {
    Text(
        text,
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.error,
        modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite },
    )
}

/** Where something is, as others may know it: the words and a banded distance. */
@Composable
fun WhereLine(location: String?, distance: Distance?, modifier: Modifier = Modifier, maxLines: Int = 1) {
    val parts = listOfNotNull(location?.takeIf { it.isNotBlank() }?.let { "📍 $it" }, distance?.text)
    if (parts.isNotEmpty()) MetaText(parts.joinToString("  ·  "), modifier, maxLines)
}

/** A spot its people chose to show exactly, in the phone's own map app (only when pressed). */
@Composable
fun ExactSpot(point: GeoPoint?, modifier: Modifier = Modifier) {
    if (point == null) return
    val context = LocalContext.current
    val uriHandler = LocalUriHandler.current
    OutlinedButton(
        modifier = modifier,
        onClick = {
            val at = "${point.lat},${point.lon}"
            try {
                context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("geo:$at?q=$at")))
            } catch (e: ActivityNotFoundException) {
                runCatching { uriHandler.openUri("https://www.openstreetmap.org/?mlat=${point.lat}&mlon=${point.lon}#map=16/${point.lat}/${point.lon}") }
            }
        },
    ) { Text("See the spot on a map") }
}
