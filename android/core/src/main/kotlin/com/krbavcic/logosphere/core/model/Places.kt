package com.krbavcic.logosphere.core.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// Real places (backend/app/utils/places.py). A person's point comes back only to that person;
// everyone else gets words and a banded distance.

/** How far, as it may be told: [km] is the band's edge, never the distance. */
@Serializable
data class Distance(val km: Int, val text: String = "")

@Serializable
data class GeoPoint(val lat: Double, val lon: Double)

/** A place as a form holds it: words, and perhaps a point with how exact it is. */
@Serializable
data class Place(
    val label: String? = null,
    val lat: Double? = null,
    val lon: Double? = null,
    val precision: String? = null,
    /** Chosen from the search just now. */
    val id: Long? = null,
    /** The phone's only: a pin put just now, whose true spot is still known here. */
    val fresh: Boolean = false,
)

/** `GET` and `POST /api/places/<kind>/<id>`. [id] is whose it now is (an opening may get a new version). */
@Serializable
data class PlaceSettings(
    val place: Place? = null,
    val findable: Boolean = false,
    val id: String? = null,
)

@Serializable
data class FoundPlace(
    val id: Long,
    val name: String = "",
    val label: String = "",
    val precision: String = "",
    val lat: Double = 0.0,
    val lon: Double = 0.0,
)

@Serializable
data class Attribution(val text: String = "", val url: String = "")

@Serializable
data class PlaceSearch(
    val available: Boolean = false,
    val results: List<FoundPlace> = emptyList(),
    val attribution: Attribution? = null,
)

@Serializable
data class NearPerson(
    val id: String,
    val name: String = "",
    val location: String? = null,
    @SerialName("is_agent") val isAgent: Boolean = false,
    val distance: Distance,
)

@Serializable
data class NearSphere(
    val id: String,
    val name: String = "",
    val location: String? = null,
    @SerialName("is_demo") val isDemo: Boolean = false,
    @SerialName("is_member") val isMember: Boolean = false,
    @SerialName("member_count") val memberCount: Int = 0,
    val distance: Distance,
)

/** `GET /api/nearby`: members who chose to be findable, and spheres. */
@Serializable
data class Nearby(
    @SerialName("has_place") val hasPlace: Boolean = false,
    val findable: Boolean = false,
    val km: Int = 25,
    val people: List<NearPerson> = emptyList(),
    val spheres: List<NearSphere> = emptyList(),
)
