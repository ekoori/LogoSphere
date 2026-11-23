package com.krbavcic.logosphere.ui

import android.Manifest
import android.content.Context
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.consumeWindowInsets
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountCircle
import androidx.compose.material.icons.filled.Eco
import androidx.compose.material.icons.filled.Groups
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.VolunteerActivism
import androidx.compose.material.icons.outlined.AccountCircle
import androidx.compose.material.icons.outlined.Eco
import androidx.compose.material.icons.outlined.Groups
import androidx.compose.material.icons.outlined.Notifications
import androidx.compose.material.icons.outlined.VolunteerActivism
import androidx.compose.material3.Badge
import androidx.compose.material3.BadgedBox
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalUriHandler
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavDestination.Companion.hasRoute
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.navigation
import androidx.navigation.compose.rememberNavController
import androidx.navigation.toRoute
import com.krbavcic.logosphere.core.logic.InfoPage
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.data.AuthState
import com.krbavcic.logosphere.push.Push
import com.krbavcic.logosphere.ui.admin.AdminScreen
import com.krbavcic.logosphere.ui.auth.RegisterScreen
import com.krbavcic.logosphere.ui.auth.SignInScreen
import com.krbavcic.logosphere.ui.communities.CommunitiesScreen
import com.krbavcic.logosphere.ui.communities.CommunityScreen
import com.krbavcic.logosphere.ui.communities.ManageCommunityScreen
import com.krbavcic.logosphere.ui.communities.NewCommunityScreen
import com.krbavcic.logosphere.ui.events.EditEventScreen
import com.krbavcic.logosphere.ui.events.EventScreen
import com.krbavcic.logosphere.ui.events.EventsScreen
import com.krbavcic.logosphere.ui.exchange.ExchangeScreen
import com.krbavcic.logosphere.ui.graph.GraphScreen
import com.krbavcic.logosphere.ui.inbox.InboxScreen
import com.krbavcic.logosphere.ui.info.InfoScreen
import com.krbavcic.logosphere.ui.me.AccountScreen
import com.krbavcic.logosphere.ui.me.EditProfileScreen
import com.krbavcic.logosphere.ui.me.MeScreen
import com.krbavcic.logosphere.ui.values.ValueCardEditorScreen
import com.krbavcic.logosphere.ui.messages.ConversationScreen
import com.krbavcic.logosphere.ui.messages.MessagesScreen
import com.krbavcic.logosphere.ui.openings.NewOpeningScreen
import com.krbavcic.logosphere.ui.openings.OpeningScreen
import com.krbavcic.logosphere.ui.openings.OpeningsScreen
import com.krbavcic.logosphere.ui.people.NearbyScreen
import com.krbavcic.logosphere.ui.people.PersonScreen
import com.krbavcic.logosphere.ui.search.SearchScreen
import com.krbavcic.logosphere.ui.trail.TrailScreen
import kotlinx.coroutines.launch
import com.krbavcic.logosphere.core.logic.UiMode
import com.krbavcic.logosphere.ui.common.LocalSimple

private fun Tab.icon(selected: Boolean): ImageVector = when (this) {
    Tab.Trail -> if (selected) Icons.Filled.Eco else Icons.Outlined.Eco
    Tab.Openings -> if (selected) Icons.Filled.VolunteerActivism else Icons.Outlined.VolunteerActivism
    Tab.Communities -> if (selected) Icons.Filled.Groups else Icons.Outlined.Groups
    Tab.Inbox -> if (selected) Icons.Filled.Notifications else Icons.Outlined.Notifications
    Tab.Me -> if (selected) Icons.Filled.AccountCircle else Icons.Outlined.AccountCircle
}

/** Android 13+: once, after signing in, ask whether LogoSphere may show notifications. */
@Composable
private fun AskForNotifications(signedIn: Boolean) {
    if (Build.VERSION.SDK_INT < 33) return
    val context = LocalContext.current
    val ask = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { }
    LaunchedEffect(signedIn) {
        if (!signedIn || Push.mayNotify(context)) return@LaunchedEffect
        val prefs = context.getSharedPreferences("logosphere", Context.MODE_PRIVATE)
        if (prefs.getBoolean("asked_notifications", false)) return@LaunchedEffect
        prefs.edit().putBoolean("asked_notifications", true).apply()
        ask.launch(Manifest.permission.POST_NOTIFICATIONS)
    }
}

@Composable
fun LogoSphereRoot() {
    val container = LocalAppContainer.current
    val auth by container.session.state.collectAsStateWithLifecycle()
    if (auth is AuthState.Loading) return // the splash screen is still up

    val controller = rememberNavController()
    // Decided once; later sign-ins and sign-outs swap graphs below.
    val start: Any = remember { if (auth is AuthState.SignedIn) MainGraph else AuthGraph }
    val signedIn = auth is AuthState.SignedIn

    LaunchedEffect(signedIn) {
        val current = controller.currentBackStackEntry ?: return@LaunchedEffect
        val inMain = current.destination.hierarchy.any { it.hasRoute(MainGraph::class) }
        if (signedIn && !inMain) {
            controller.navigate(MainGraph) { popUpTo(controller.graph.id) { inclusive = true } }
        } else if (!signedIn && inMain) {
            controller.navigate(AuthGraph) { popUpTo(controller.graph.id) { inclusive = true } }
        }
    }

    val entry by controller.currentBackStackEntryAsState()
    val destination = entry?.destination
    val inMain = destination?.hierarchy?.any { it.hasRoute(MainGraph::class) } == true
    var selectedTab by rememberSaveable { mutableStateOf(Tab.Openings) }
    // Coming back to a tab's own screen makes that tab current again.
    val tabOnScreen = Tab.entries.firstOrNull { tab -> destination?.hasRoute(tab.route::class) == true }
    LaunchedEffect(tabOnScreen) {
        if (tabOnScreen != null) selectedTab = tabOnScreen
    }

    val uriHandler = LocalUriHandler.current
    val navigator = remember(controller) {
        Navigator(
            controller = controller,
            selectTab = { tab ->
                if (tab == selectedTab && controller.currentBackStackEntry?.destination?.hasRoute(tab.route::class) == false) {
                    // Tapping the current tab again returns to its top.
                    controller.popBackStack(tab.route, inclusive = false)
                } else {
                    // Openings is where the app opens, so it's the root of the signed-in back stack
                    // (Trail is still the first tab in the bar).
                    controller.navigate(tab.route) {
                        popUpTo<OpeningsRoute> { saveState = true }
                        launchSingleTop = true
                        restoreState = true
                    }
                }
                selectedTab = tab
            },
            openWeb = { path -> uriHandler.openUri(container.api.webUrl(path)) },
        )
    }

    // A tapped notification opens its page once the signed-in screens are up.
    val pendingLink by container.pendingLink.collectAsStateWithLifecycle()
    LaunchedEffect(pendingLink, inMain) {
        val link = pendingLink ?: return@LaunchedEffect
        if (inMain) {
            container.pendingLink.value = null
            navigator.link(link)
        }
    }
    AskForNotifications(signedIn)

    val unread by container.inbox.unread.collectAsStateWithLifecycle()
    val scope = rememberCoroutineScope()
    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) {
        if (container.session.user != null) scope.launch { container.inbox.refreshCount() }
    }
    LaunchedEffect(signedIn) {
        if (signedIn) container.inbox.refreshCount()
    }

    val simple = (auth as? AuthState.SignedIn)?.user?.uiMode == UiMode.Simple
    CompositionLocalProvider(LocalNavigator provides navigator, LocalSimple provides simple) {
        Scaffold(
            contentWindowInsets = WindowInsets(0),
            bottomBar = {
                if (inMain) {
                    NavigationBar(containerColor = MaterialTheme.colorScheme.surfaceContainerLow) {
                        Tab.entries.forEach { tab ->
                            val selected = tab == selectedTab
                            NavigationBarItem(
                                selected = selected,
                                onClick = { navigator.tab(tab) },
                                icon = {
                                    if (tab == Tab.Inbox && unread > 0) {
                                        BadgedBox(badge = { Badge { Text(if (unread > 99) "99+" else unread.toString()) } }) {
                                            Icon(tab.icon(selected), contentDescription = "${tab.label}, $unread unread")
                                        }
                                    } else {
                                        Icon(tab.icon(selected), contentDescription = tab.label)
                                    }
                                },
                                label = { Text(tab.label, maxLines = 1) },
                                colors = NavigationBarItemDefaults.colors(
                                    selectedIconColor = MaterialTheme.colorScheme.primary,
                                    selectedTextColor = MaterialTheme.colorScheme.primary,
                                    indicatorColor = MaterialTheme.colorScheme.primaryContainer,
                                ),
                            )
                        }
                    }
                }
            },
        ) { padding ->
            NavHost(
                navController = controller,
                startDestination = start,
                modifier = Modifier
                    .padding(padding)
                    .consumeWindowInsets(padding),
            ) {
                navigation<AuthGraph>(startDestination = SignInRoute) {
                    composable<SignInRoute> {
                        SignInScreen(notice = (auth as? AuthState.SignedOut)?.notice)
                    }
                    composable<RegisterRoute> { RegisterScreen() }
                }
                navigation<MainGraph>(startDestination = OpeningsRoute) {
                    composable<TrailRoute> { TrailScreen() }
                    composable<OpeningsRoute> { OpeningsScreen() }
                    composable<CommunitiesRoute> { CommunitiesScreen() }
                    composable<InboxRoute> { InboxScreen() }
                    composable<MeRoute> { MeScreen() }
                    composable<OpeningRoute> { OpeningScreen(it.toRoute<OpeningRoute>().id) }
                    composable<NewOpeningRoute> {
                        val route = it.toRoute<NewOpeningRoute>()
                        NewOpeningScreen(route.actingAsKind?.let(CommunityKind::valueOf), route.actingAsId)
                    }
                    composable<ExchangeRoute> { ExchangeScreen(it.toRoute<ExchangeRoute>().id) }
                    composable<CommunityRoute> {
                        val route = it.toRoute<CommunityRoute>()
                        CommunityScreen(CommunityKind.valueOf(route.kind), route.id, route.tab)
                    }
                    composable<ManageCommunityRoute> {
                        val route = it.toRoute<ManageCommunityRoute>()
                        ManageCommunityScreen(CommunityKind.valueOf(route.kind), route.id)
                    }
                    composable<NewCommunityRoute> { NewCommunityScreen(CommunityKind.valueOf(it.toRoute<NewCommunityRoute>().kind)) }
                    composable<PersonRoute> {
                        val route = it.toRoute<PersonRoute>()
                        PersonScreen(route.id, route.tab)
                    }
                    composable<SearchRoute> { SearchScreen() }
                    composable<NearbyRoute> { NearbyScreen() }
                    composable<EventsRoute> { EventsScreen() }
                    composable<EventRoute> { EventScreen(it.toRoute<EventRoute>().id) }
                    composable<EditEventRoute> {
                        val route = it.toRoute<EditEventRoute>()
                        EditEventScreen(route.id, route.groupKind?.let(CommunityKind::valueOf), route.groupId)
                    }
                    composable<MessagesRoute> { MessagesScreen() }
                    composable<ConversationRoute> {
                        val route = it.toRoute<ConversationRoute>()
                        ConversationScreen(route.personId, route.openingId, route.about)
                    }
                    composable<GraphRoute> { it.toRoute<GraphRoute>().let { route -> GraphScreen(route.owner, route.card) } }
                    composable<EditProfileRoute> { EditProfileScreen() }
                    composable<AccountRoute> { AccountScreen() }
                    composable<ValueCardEditorRoute> {
                        val route = it.toRoute<ValueCardEditorRoute>()
                        ValueCardEditorScreen(route.groupKind?.let(CommunityKind::valueOf), route.groupId, route.cardId)
                    }
                    composable<AdminRoute> { AdminScreen() }
                    composable<InfoRoute> { InfoScreen(InfoPage.valueOf(it.toRoute<InfoRoute>().page)) }
                }
            }
        }
    }
}
