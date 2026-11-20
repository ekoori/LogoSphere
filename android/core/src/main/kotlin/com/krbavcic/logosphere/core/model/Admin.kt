package com.krbavcic.logosphere.core.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// The platform administration console (backend/app/routes/admin.py), for members flagged
// is_platform_admin. Lists come whole; the screens filter them.

@Serializable
data class AdminCounts(
    val users: Int = 0,
    @SerialName("platform_admins") val platformAdmins: Int = 0,
    val spheres: Int = 0,
    val alliances: Int = 0,
    val projects: Int = 0,
    val openings: Int = 0,
    @SerialName("openings_open") val openingsOpen: Int = 0,
    val exchanges: Int = 0,
    @SerialName("sandbox_spheres") val sandboxSpheres: Int = 0,
    @SerialName("public_spheres") val publicSpheres: Int = 0,
)

@Serializable
data class AdminPerson(val id: String, val name: String? = null, val email: String? = null)

@Serializable
data class AdminOverview(
    val counts: AdminCounts = AdminCounts(),
    @SerialName("platform_admins") val platformAdmins: List<AdminPerson> = emptyList(),
)

@Serializable
data class AdminUser(
    val id: String,
    val name: String? = null,
    val surname: String? = null,
    @SerialName("full_name") val fullName: String? = null,
    val email: String? = null,
    val location: String? = null,
    @SerialName("is_platform_admin") val isPlatformAdmin: Boolean = false,
    @SerialName("is_agent") val isAgent: Boolean = false,
    @SerialName("joined_at") val joinedAt: String? = null,
    @SerialName("sphere_count") val sphereCount: Int = 0,
    @SerialName("card_count") val cardCount: Int = 0,
    @SerialName("is_you") val isYou: Boolean = false,
) {
    val label: String get() = fullName?.takeIf { it.isNotBlank() } ?: listOfNotNull(name, surname).joinToString(" ").ifBlank { email ?: "Member" }
}

@Serializable
data class AdminUsers(val users: List<AdminUser> = emptyList())

/** A sphere, alliance or project as the console lists it: counts instead of member lists. */
@Serializable
data class AdminGroup(
    val id: String,
    val kind: String = "sphere",
    val name: String = "",
    val description: String? = null,
    @SerialName("sphere_name") val sphereName: String? = null,
    @SerialName("owner_alliance") val ownerAlliance: String? = null,
    @SerialName("owner_name") val ownerName: String? = null,
    @SerialName("member_count") val memberCount: Int = 0,
    @SerialName("pending_count") val pendingCount: Int = 0,
    @SerialName("card_count") val cardCount: Int = 0,
    @SerialName("alliance_count") val allianceCount: Int = 0,
    @SerialName("project_count") val projectCount: Int = 0,
    @SerialName("join_policy") val joinPolicy: String? = null,
    @SerialName("decision_policy") val decisionPolicy: String? = null,
    @SerialName("pm_policy") val pmPolicy: String? = null,
    @SerialName("confirm_policy") val confirmPolicy: String? = null,
    val phase: String? = null,
    @SerialName("is_public") val isPublic: Boolean = false,
    @SerialName("is_sandbox") val isSandbox: Boolean = false,
    @SerialName("is_demo") val isDemo: Boolean = false,
) {
    val communityKind: CommunityKind get() = CommunityKind.of(kind) ?: CommunityKind.Sphere

    /** The value of one of its policies, by the policy's API name. */
    fun policy(key: String): String? = when (key) {
        "join_policy" -> joinPolicy
        "decision_policy" -> decisionPolicy
        "pm_policy" -> pmPolicy
        "confirm_policy" -> confirmPolicy
        "phase" -> phase
        else -> null
    }
}

@Serializable
data class AdminGroups(val items: List<AdminGroup> = emptyList())

@Serializable
data class AdminOpening(
    @SerialName("service_id") val id: String,
    val title: String = "",
    val description: String? = null,
    val type: String = "offer",
    val provider: String? = null,
    @SerialName("acting_user") val actingUser: String? = null,
    val spheres: List<String> = emptyList(),
    @SerialName("project_name") val projectName: String? = null,
    val status: String = "Posted",
    val cadence: String = "single",
    val version: Int = 1,
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("pending_count") val pendingCount: Int = 0,
    @SerialName("confirmed_count") val confirmedCount: Int = 0,
    @SerialName("is_open") val isOpen: Boolean = false,
) {
    val isOffer: Boolean get() = type != "need"
    val providerLabel: String get() = actingUser?.let { "$it for ${provider ?: "a group"}" } ?: provider ?: "A member"
}

@Serializable
data class AdminOpenings(val items: List<AdminOpening> = emptyList())

/** `POST /api/admin/users/<id>/reset_link`: [path] goes after the site's address. */
@Serializable
data class ResetLink(
    val message: String? = null,
    val path: String,
    @SerialName("expires_at") val expiresAt: String? = null,
)
