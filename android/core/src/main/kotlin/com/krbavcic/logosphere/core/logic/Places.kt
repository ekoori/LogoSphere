package com.krbavcic.logosphere.core.logic

import com.krbavcic.logosphere.core.model.FoundPlace
import com.krbavcic.logosphere.core.model.GeoPoint
import com.krbavcic.logosphere.core.model.Place
import com.krbavcic.logosphere.core.model.PlaceSettings
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.min
import kotlin.math.round

/** How exact a pin is: the square it is rounded into before it leaves the phone. */
enum class PinPrecision(val key: String, val km: Double?, val label: String) {
    Exact("exact", null, "The exact spot"),
    Km1("1km", 1.0, "About 1 km"),
    Km5("5km", 5.0, "About 5 km"),
    Km10("10km", 10.0, "About 10 km (a town)"),
    Km100("100km", 100.0, "About 100 km (a region)");

    /** A phone's approximate location is too rough for this. */
    val needsFineLocation: Boolean get() = km == null || km <= 1.0

    /** How far off a reading may be and still be this exact, in metres. */
    val roomMetres: Double get() = (km ?: 0.1) * 1000

    fun isFinerThan(other: PinPrecision): Boolean = ordinal < other.ordinal

    companion object {
        fun of(key: String?): PinPrecision? = entries.firstOrNull { it.key == key }
    }
}

/** The site's utils/places.js and mercator.js, for the phone: the two are tested to agree. */
object Places {
    const val PEOPLE = "users"
    const val OPENINGS = "openings"
    const val EVENTS = "events"
    const val LABEL_MAX = 120
    val NEAR_KM = listOf(5, 10, 25, 50, 100, 250)

    private const val KM_A_DEGREE = 111.32
    private val NAMED = setOf("postcode", "town", "region", "country")

    fun hasPoint(place: Place?): Boolean = place?.lat != null && place.lon != null

    fun isPin(place: Place?): Boolean = hasPoint(place) && place?.precision !in NAMED

    fun isNamed(place: Place?): Boolean = hasPoint(place) && place?.precision in NAMED

    /** A country is on the map, but says nothing about what's near. */
    fun canMeasure(place: Place?): Boolean = hasPoint(place) && place?.precision != "country"

    /** A point no finer than [km], so nothing more exact leaves the phone than was chosen. */
    fun coarsened(lat: Double, lon: Double, km: Double?): GeoPoint {
        if (km == null) return GeoPoint(sixPlaces(lat), sixPlaces(lon))
        val step = km / KM_A_DEGREE
        val middle = ((floor(lat / step) + 0.5) * step).coerceIn(-89.9, 89.9)
        val stepLon = min(360.0, step / cos(Math.toRadians(middle)))
        val middleLon = min(180.0, (floor((lon + 180) / stepLon) + 0.5) * stepLon - 180)
        return GeoPoint(sixPlaces(middle), sixPlaces(middleLon))
    }

    private fun sixPlaces(x: Double): Double = round(x * 1e6) / 1e6

    fun linkedTo(place: Place?): String? {
        if (place == null) return null
        if (isNamed(place)) {
            return if (place.precision == "country") "On the map, as a country: too rough to show what's near"
            else "On the map, as a ${place.precision}"
        }
        if (!isPin(place)) return if (place.label.isNullOrBlank()) null else "Only words so far: it isn't on the map"
        val km = PinPrecision.of(place.precision)?.km
        return if (km == null) "On the map, at the exact spot" else "On the map, to about ${km.toInt()} km"
    }

    /** Why it can't be saved yet, or null. */
    fun problem(place: Place?): String? =
        if (isPin(place) && place?.label.isNullOrBlank()) "Give the pin a name in a few words: that is what others see." else null

    /** Typing over a place found by name lets go of its point: the words would no longer say it. */
    fun withWords(place: Place?, words: String): Place {
        val label = words.take(LABEL_MAX)
        return if (place != null && isPin(place)) place.copy(label = label) else Place(label = label)
    }

    fun found(place: FoundPlace): Place =
        Place(label = place.label.take(LABEL_MAX), lat = place.lat, lon = place.lon, precision = place.precision, id = place.id)

    fun same(one: Place?, other: Place?): Boolean =
        one?.label.orEmpty() == other?.label.orEmpty() &&
            one?.lat == other?.lat && one?.lon == other?.lon && one?.precision == other?.precision && one?.id == other?.id

    /**
     * The body's `place`: [JsonNull] for none. Null when it can't be sent again: a place from the
     * search that was stored earlier has no id any more, and is unchanged anyway.
     */
    fun payload(place: Place?): JsonElement? {
        if (place == null) return JsonNull
        val label = place.label.orEmpty().trim()
        val lat = place.lat
        val lon = place.lon
        return when {
            place.id != null -> buildJsonObject { put("id", place.id); put("label", label) }
            lat != null && lon != null && isPin(place) -> {
                val precision = PinPrecision.of(place.precision) ?: PinPrecision.Km1
                val at = coarsened(lat, lon, precision.km)
                buildJsonObject {
                    put("lat", at.lat)
                    put("lon", at.lon)
                    put("precision", precision.key)
                    put("label", label)
                }
            }
            isNamed(place) -> null
            label.isEmpty() -> JsonNull
            else -> buildJsonObject { put("label", label) }
        }
    }
}

/** A place being edited, beside what is stored. */
@Serializable
data class PlaceDraft(
    val saved: Place? = null,
    val place: Place? = null,
    val person: Boolean = false,
    val findableChosen: Boolean = false,
    val wasFindable: Boolean = false,
) {
    /** With no point there's nothing to be found by. */
    val findable: Boolean get() = findableChosen && Places.hasPoint(place)

    val placeChanged: Boolean get() = !Places.same(saved, place)

    val changed: Boolean get() = placeChanged || (person && findable != wasFindable)

    val problem: String? get() = if (placeChanged) Places.problem(place) else null

    fun body(): JsonObject = buildJsonObject {
        if (placeChanged) Places.payload(place)?.let { put("place", it) }
        if (person) put("findable", findable)
    }

    companion object {
        fun of(stored: PlaceSettings, person: Boolean = false) = PlaceDraft(
            saved = stored.place,
            place = stored.place,
            person = person,
            findableChosen = stored.findable,
            wasFindable = stored.findable,
        )
    }
}
