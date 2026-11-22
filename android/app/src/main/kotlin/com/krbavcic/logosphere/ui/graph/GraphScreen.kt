package com.krbavcic.logosphere.ui.graph

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.FitScreen
import androidx.compose.material.icons.filled.Remove
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.outlined.Hub
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material.icons.outlined.Tune
import androidx.compose.material3.FilledTonalIconButton
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.ListItem
import androidx.compose.material3.ListItemDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.krbavcic.logosphere.AppContainer
import com.krbavcic.logosphere.core.api.userMessage
import com.krbavcic.logosphere.core.logic.GraphScope
import com.krbavcic.logosphere.core.logic.GraphView
import com.krbavcic.logosphere.core.logic.ShownGraph
import com.krbavcic.logosphere.core.model.ClosenessMethod
import com.krbavcic.logosphere.core.model.GraphEdge
import com.krbavcic.logosphere.core.model.GraphNode
import com.krbavcic.logosphere.core.model.MeaningGraph
import com.krbavcic.logosphere.core.model.ValueCard
import com.krbavcic.logosphere.ui.Load
import com.krbavcic.logosphere.ui.LoadViewModel
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.common.BackTopBar
import com.krbavcic.logosphere.ui.common.EmptyNote
import com.krbavcic.logosphere.ui.common.LoadContent
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.ScreenPadding
import com.krbavcic.logosphere.ui.common.ScrollingTabs
import com.krbavcic.logosphere.ui.common.SnackbarMessages
import com.krbavcic.logosphere.ui.common.ValueCardSheet
import com.krbavcic.logosphere.ui.theme.Brand
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlin.coroutines.cancellation.CancellationException
import kotlin.math.roundToInt
import com.krbavcic.logosphere.ui.common.LocalSimple

class GraphViewModel(private val app: AppContainer) : LoadViewModel<MeaningGraph>() {
    private val _method = MutableStateFlow<Load<ClosenessMethod>>(Load.Loading)
    val method: StateFlow<Load<ClosenessMethod>> = _method.asStateFlow()

    init {
        load()
    }

    override suspend fun fetch(force: Boolean): MeaningGraph = app.api.meaningGraph()

    fun loadMethod() {
        if (_method.value is Load.Ready) return
        _method.value = Load.Loading
        viewModelScope.launch {
            _method.value = try {
                Load.Ready(app.api.meaningGraphMethod())
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                logFailure("method", e)
                Load.Failed(e.userMessage())
            }
        }
    }

    /** One judgement for each pair; saying the same again takes it back. */
    fun judge(edge: GraphEdge, close: Boolean) = act {
        val judged = app.api.judgeCloseness(edge.a, edge.b, if (edge.myJudgement == close) null else close)
        update { it.withEdge(judged) }
    }
}

private const val LEAST_PERCENT = 6f
private const val MOST_PERCENT = 50f

/** The Meaning Graph: every value card the member may read, drawn by closeness. [startOwner] starts on one owner's. */
@Composable
fun GraphScreen(startOwner: String?) {
    val app = LocalAppContainer.current
    val vm: GraphViewModel = viewModel { GraphViewModel(app) }
    val navigator = LocalNavigator.current
    val state by vm.state.collectAsStateWithLifecycle()
    val method by vm.method.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    SnackbarMessages(vm.messages, snackbar)

    var scope by rememberSaveable { mutableIntStateOf(0) }
    var owner by rememberSaveable { mutableStateOf(startOwner) }
    var focus by rememberSaveable { mutableStateOf<String?>(null) }
    var selected by rememberSaveable { mutableStateOf<String?>(null) }
    var demos by rememberSaveable { mutableStateOf(true) }
    var query by rememberSaveable { mutableStateOf("") }
    var searching by rememberSaveable { mutableStateOf(false) }
    var tuning by rememberSaveable { mutableStateOf(false) }
    var fromPercent by rememberSaveable { mutableFloatStateOf(-1f) } // below zero: the server's
    var asList by rememberSaveable { mutableStateOf(false) }
    var details by rememberSaveable { mutableStateOf(false) }
    var showMethod by rememberSaveable { mutableStateOf(false) }
    var reading by remember { mutableStateOf<ValueCard?>(null) }
    val drawing = remember { GraphDrawing() }
    val simple = LocalSimple.current

    fun showEverything() {
        scope = 0
        owner = null
        focus = null
    }

    Scaffold(
        topBar = {
            BackTopBar("Meaning Graph", navigator::back) {
                IconButton(onClick = {
                    searching = !searching
                    if (!searching) query = ""
                }) {
                    Icon(
                        if (searching) Icons.Filled.Close else Icons.Filled.Search,
                        contentDescription = if (searching) "Stop finding" else "Find a value or a person",
                    )
                }
                IconButton(onClick = { asList = !asList }) {
                    if (asList) {
                        Icon(Icons.Outlined.Hub, contentDescription = "See it as a graph")
                    } else {
                        Icon(Icons.AutoMirrored.Filled.List, contentDescription = "See it as a list")
                    }
                }
                IconButton(onClick = {
                    showMethod = true
                    vm.loadMethod()
                }) { Icon(Icons.Outlined.Info, contentDescription = "How closeness is worked out") }
            }
        },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        LoadContent(state, onRetry = vm::load, modifier = Modifier.padding(padding)) { graph ->
            // Simple has no slider, so it keeps to the platform's threshold.
            val from = if (!simple && fromPercent >= 0) fromPercent.roundToInt() / 100.0 else graph.shownFrom
            val shown = remember(graph, scope, owner, focus, demos, query, from) {
                GraphView.visible(graph, GraphScope.entries[scope], owner, focus, demos, query, from)
            }
            val byId = remember(graph) { graph.nodes.associateBy { it.id } }
            val chosen = selected?.takeIf { it in shown.degree }?.let(byId::get)

            Column(Modifier.fillMaxSize().padding(padding)) {
                Row(
                    Modifier.fillMaxWidth().padding(start = ScreenPadding, end = 4.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Box(Modifier.weight(1f)) {
                        ScrollingTabs(
                            options = GraphScope.entries.map { it.label },
                            selected = if (owner != null || focus != null) -1 else scope,
                            onSelect = {
                                showEverything()
                                scope = it
                            },
                        )
                    }
                    IconButton(onClick = { tuning = !tuning }) { Icon(Icons.Outlined.Tune, contentDescription = "What to show") }
                }
                if (searching) {
                    OutlinedTextField(
                        value = query,
                        onValueChange = { query = it },
                        singleLine = true,
                        placeholder = { Text("Find a value or a person…") },
                        modifier = Modifier.fillMaxWidth().padding(horizontal = ScreenPadding, vertical = 4.dp),
                    )
                }
                if (tuning) {
                    Column(Modifier.padding(horizontal = ScreenPadding)) {
                        FilterChip(selected = demos, onClick = { demos = !demos }, label = { Text("Demo and AI personas") })
                        if (!simple) {
                            MetaText("Connections from ${GraphView.percent(from)}")
                            Slider(
                                value = (from * 100).toFloat(),
                                onValueChange = { fromPercent = it.roundToInt().toFloat() },
                                valueRange = LEAST_PERCENT..MOST_PERCENT,
                            )
                        }
                    }
                }
                val ownerNow = owner
                val focusNow = focus
                if (ownerNow != null || focusNow != null) {
                    val of = if (focusNow != null) {
                        "“${byId[focusNow]?.title.orEmpty()}”"
                    } else {
                        "${graph.nodes.firstOrNull { it.owner.id == ownerNow }?.owner?.name ?: "One owner"}'s cards"
                    }
                    Row(
                        Modifier.fillMaxWidth().padding(start = ScreenPadding, end = 4.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        MetaText("$of and what they connect to", Modifier.weight(1f), maxLines = 2)
                        TextButton(onClick = ::showEverything) { Text("Show everything") }
                    }
                }

                Box(Modifier.weight(1f).fillMaxWidth()) {
                    when {
                        shown.nodes.isEmpty() -> EmptyNote(
                            when {
                                query.isNotBlank() -> "No card matches “${query.trim()}”."
                                owner == null && focus == null && GraphScope.entries[scope] == GraphScope.Mine ->
                                    "You haven't written a value card yet. Write your first under Me."
                                else -> "No cards match these filters."
                            },
                        )

                        asList -> GraphList(shown, byId, onPick = {
                            selected = it
                            details = true
                        })

                        else -> {
                            GraphCanvas(
                                shown = shown,
                                selected = chosen?.id,
                                onSelect = { selected = it },
                                drawing = drawing,
                                surface = Brand.colors.card,
                                ink = MaterialTheme.colorScheme.onSurface,
                            )
                            Column(Modifier.align(Alignment.TopEnd).padding(4.dp)) {
                                FilledTonalIconButton(onClick = { drawing.zoomBy(1.3f) }) {
                                    Icon(Icons.Filled.Add, contentDescription = "Zoom in")
                                }
                                FilledTonalIconButton(onClick = { drawing.zoomBy(0.77f) }) {
                                    Icon(Icons.Filled.Remove, contentDescription = "Zoom out")
                                }
                                FilledTonalIconButton(onClick = drawing::fit) {
                                    Icon(Icons.Filled.FitScreen, contentDescription = "Fit everything in")
                                }
                            }
                        }
                    }
                }

                // As tall with a card chosen as without, so the graph doesn't shift under the finger.
                Surface(color = MaterialTheme.colorScheme.surfaceContainerLow, modifier = Modifier.fillMaxWidth().heightIn(min = 116.dp)) {
                    if (chosen != null) {
                        ChosenCard(chosen, shown.degree[chosen.id] ?: 0, onOpen = { details = true })
                    } else {
                        Column(
                            Modifier.fillMaxWidth().padding(horizontal = ScreenPadding, vertical = 8.dp),
                            verticalArrangement = Arrangement.spacedBy(3.dp),
                        ) {
                            MetaText(
                                "Cards that care about close things are drawn near each other. Tap one for the exact figures and why.",
                                maxLines = 2,
                            )
                            GraphLegend()
                            MetaText("${shown.nodes.size} cards · ${shown.edges.size} connections")
                        }
                    }
                }
            }

            if (details && chosen != null) {
                GraphDetailsSheet(
                    node = chosen,
                    edges = shown.edges,
                    byId = byId,
                    focused = focus == chosen.id,
                    busy = busy,
                    onSelect = { selected = it },
                    onFocus = {
                        focus = it
                        details = false
                    },
                    onReadCard = {
                        details = false
                        reading = chosen.card.copy(title = chosen.title)
                    },
                    onOwner = { who ->
                        details = false
                        val kind = who.communityKind
                        if (kind != null) navigator.community(kind, who.id) else navigator.person(who.id)
                    },
                    onJudge = vm::judge,
                    onDismiss = { details = false },
                )
            }
        }
    }

    reading?.let { ValueCardSheet(it, onDismiss = { reading = null }) }
    if (showMethod) MethodSheet(method, onRetry = vm::loadMethod, onDismiss = { showMethod = false })
}

@Composable
private fun ChosenCard(node: GraphNode, connections: Int, onOpen: () -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .clickable(role = Role.Button, onClick = onOpen)
            .padding(start = ScreenPadding, end = 4.dp, top = 10.dp, bottom = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        MeaningDot(node.mode, node.owner.isGroup)
        Column(Modifier.weight(1f)) {
            Text(
                node.title,
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onSurface,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            MetaText("${node.owner.name} · $connections ${if (connections == 1) "connection" else "connections"}")
        }
        TextButton(onClick = onOpen) { Text("See why") }
    }
}

/** The same graph as text. */
@Composable
private fun GraphList(shown: ShownGraph, byId: Map<String, GraphNode>, onPick: (String) -> Unit) {
    val rows = remember(shown) {
        shown.nodes
            .map { it to GraphView.closestTo(it.id, shown.edges) }
            .sortedWith(compareByDescending<Pair<GraphNode, List<GraphEdge>>> { it.second.size }.thenBy { it.first.title })
    }
    LazyColumn(Modifier.fillMaxSize()) {
        items(rows, key = { it.first.id }) { (node, close) ->
            val nearest = close.firstOrNull()
            ListItem(
                headlineContent = { Text(node.title) },
                supportingContent = {
                    val whose = node.owner.name + if (node.owner.isAgent) " (AI)" else ""
                    val closest = nearest?.let {
                        "\nClosest: ${byId[it.other(node.id)]?.title.orEmpty()}, ${GraphView.percent(it.closeness)}"
                    }.orEmpty()
                    val count = if (close.size == 1) "1 connection" else "${close.size} connections"
                    Text("$whose · ${node.mode.label} · $count$closest")
                },
                leadingContent = { MeaningDot(node.mode, node.owner.isGroup) },
                colors = ListItemDefaults.colors(containerColor = MaterialTheme.colorScheme.background),
                modifier = Modifier.clickable(role = Role.Button) { onPick(node.id) },
            )
        }
    }
}
