package com.krbavcic.logosphere.ui

import androidx.compose.runtime.staticCompositionLocalOf
import androidx.navigation.NavHostController
import com.krbavcic.logosphere.core.logic.AppLink
import com.krbavcic.logosphere.core.logic.InfoPage
import com.krbavcic.logosphere.core.model.Community
import com.krbavcic.logosphere.core.model.CommunityKind
import kotlinx.serialization.Serializable

// Type-safe routes (Navigation Compose 2.8).
@Serializable data object AuthGraph
@Serializable data object SignInRoute
@Serializable data object RegisterRoute

@Serializable data object MainGraph
@Serializable data object TrailRoute
@Serializable data object OpeningsRoute
@Serializable data object CommunitiesRoute
@Serializable data object InboxRoute
@Serializable data object MeRoute

@Serializable data class OpeningRoute(val id: String)

/** A new opening; [actingAsKind]/[actingAsId] post it on behalf of a group the member manages. */
@Serializable data class NewOpeningRoute(val actingAsKind: String? = null, val actingAsId: String? = null)
@Serializable data class ExchangeRoute(val id: String)
@Serializable data class CommunityRoute(val kind: String, val id: String, val tab: String? = null)
@Serializable data class ManageCommunityRoute(val kind: String, val id: String)
@Serializable data class NewCommunityRoute(val kind: String)
@Serializable data class PersonRoute(val id: String, val tab: String? = null)
@Serializable data object SearchRoute

/** The Meaning Graph; [owner] opens it on one person's or group's cards. */
@Serializable data class GraphRoute(val owner: String? = null)
@Serializable data object EditProfileRoute
@Serializable data object AccountRoute

/** Writes a value card — the member's own, or a group's ([groupKind]/[groupId]); [cardId] edits one. */
@Serializable data class ValueCardEditorRoute(val groupKind: String? = null, val groupId: String? = null, val cardId: String? = null)
@Serializable data object AdminRoute
@Serializable data class InfoRoute(val page: String)

/** The bottom bar's destinations. */
enum class Tab(val route: Any, val label: String) {
    Trail(TrailRoute, "Trail"),
    Openings(OpeningsRoute, "Openings"),
    // Spheres hold the alliances and projects listed alongside them; "Communities" didn't fit.
    Communities(CommunitiesRoute, "Spheres"),
    Inbox(InboxRoute, "Inbox"),
    Me(MeRoute, "Me"),
}

/** Moving around the app, for screens: they never touch the NavController themselves. */
class Navigator(
    private val controller: NavHostController,
    private val selectTab: (Tab) -> Unit,
    private val openWeb: (String) -> Unit,
) {
    fun back() {
        controller.popBackStack()
    }

    fun tab(tab: Tab) = selectTab(tab)

    fun opening(id: String) = controller.navigate(OpeningRoute(id))

    fun newOpening(actingAs: Community? = null) = controller.navigate(NewOpeningRoute(actingAs?.kind?.name, actingAs?.id))

    fun exchange(id: String) = controller.navigate(ExchangeRoute(id))

    fun community(kind: CommunityKind, id: String, tab: String? = null) = controller.navigate(CommunityRoute(kind.name, id, tab))

    fun manageCommunity(kind: CommunityKind, id: String) = controller.navigate(ManageCommunityRoute(kind.name, id))

    fun newCommunity(kind: CommunityKind) = controller.navigate(NewCommunityRoute(kind.name))

    fun person(id: String) = controller.navigate(PersonRoute(id))

    /** Someone's page on one of its tabs (their trail, from a notification). */
    fun personTab(id: String, tab: String?) = controller.navigate(PersonRoute(id, tab))

    fun search() = controller.navigate(SearchRoute)

    fun meaningGraph(owner: String? = null) = controller.navigate(GraphRoute(owner))

    fun register() = controller.navigate(RegisterRoute)

    fun editProfile() = controller.navigate(EditProfileRoute)

    fun account() = controller.navigate(AccountRoute)

    fun valueCardEditor(group: Community? = null, cardId: String? = null) =
        controller.navigate(ValueCardEditorRoute(group?.kind?.name, group?.id, cardId))

    fun admin() = controller.navigate(AdminRoute)

    fun info(page: InfoPage) = controller.navigate(InfoRoute(page.name))

    /** This screen gives way to another (a new version of an opening, a group just started). */
    fun replace(open: Navigator.() -> Unit) {
        controller.popBackStack()
        open()
    }

    /** A page of the web app, for anything the phone has no screen for. */
    fun web(path: String) = openWeb(path)

    fun link(link: AppLink) = when (link) {
        is AppLink.Opening -> opening(link.id)
        is AppLink.Exchange -> exchange(link.id)
        is AppLink.Community -> community(link.kind, link.id, link.tab)
        is AppLink.Manage -> manageCommunity(link.kind, link.id)
        is AppLink.Person -> personTab(link.id, link.tab)
        is AppLink.MeaningGraph -> meaningGraph(link.owner)
        AppLink.Me -> tab(Tab.Me)
        AppLink.EditProfile -> editProfile()
        AppLink.Admin -> admin()
        is AppLink.Info -> info(link.page)
        is AppLink.Web -> web(link.path)
    }
}

val LocalNavigator = staticCompositionLocalOf<Navigator> { error("No Navigator provided") }
