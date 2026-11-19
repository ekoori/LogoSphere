package com.krbavcic.logosphere.ui

import androidx.compose.runtime.staticCompositionLocalOf
import androidx.navigation.NavHostController
import com.krbavcic.logosphere.core.logic.AppLink
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
@Serializable data object NewOpeningRoute
@Serializable data class ExchangeRoute(val id: String)
@Serializable data class CommunityRoute(val kind: String, val id: String)
@Serializable data class PersonRoute(val id: String)
@Serializable data object SearchRoute

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

    fun newOpening() = controller.navigate(NewOpeningRoute)

    fun exchange(id: String) = controller.navigate(ExchangeRoute(id))

    fun community(kind: CommunityKind, id: String) = controller.navigate(CommunityRoute(kind.name, id))

    fun person(id: String) = controller.navigate(PersonRoute(id))

    fun search() = controller.navigate(SearchRoute)

    fun register() = controller.navigate(RegisterRoute)

    /** A page of the web app, for what the phone leaves to the web. */
    fun web(path: String) = openWeb(path)

    fun link(link: AppLink) = when (link) {
        is AppLink.Opening -> opening(link.id)
        is AppLink.Exchange -> exchange(link.id)
        is AppLink.Community -> community(link.kind, link.id)
        is AppLink.Person -> person(link.id)
        AppLink.Me -> tab(Tab.Me)
        is AppLink.Web -> web(link.path)
    }
}

val LocalNavigator = staticCompositionLocalOf<Navigator> { error("No Navigator provided") }
