package com.krbavcic.logosphere.ui.search

import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.krbavcic.logosphere.AppContainer
import com.krbavcic.logosphere.core.api.userMessage
import com.krbavcic.logosphere.core.logic.Links
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.SearchItem
import com.krbavcic.logosphere.core.model.SearchResults
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.common.Avatar
import com.krbavcic.logosphere.ui.common.BackTopBar
import com.krbavcic.logosphere.ui.common.GroupAvatar
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.ScreenPadding
import com.krbavcic.logosphere.ui.common.SectionHeading
import com.krbavcic.logosphere.ui.common.SegmentedTabs
import com.krbavcic.logosphere.ui.theme.valueCardAccent
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlin.coroutines.cancellation.CancellationException

private val SCOPES = listOf(
    null to "Everything", "user" to "People", "sphere" to "Spheres", "alliance" to "Alliances",
    "project" to "Projects", "opening" to "Openings", "card" to "Value cards",
)

data class SearchState(
    val loading: Boolean = false,
    val results: SearchResults? = null,
    val error: String? = null,
)

class SearchViewModel(private val app: AppContainer) : ViewModel() {
    private val _state = MutableStateFlow(SearchState())
    val state: StateFlow<SearchState> = _state.asStateFlow()
    private var job: Job? = null

    /** Searches as the person types, a moment after they pause. */
    fun search(query: String, nearValues: Boolean, kind: String?, debounce: Boolean = true) {
        job?.cancel()
        val q = query.trim()
        if (!nearValues && q.length < 2) {
            _state.value = SearchState()
            return
        }
        job = viewModelScope.launch {
            if (debounce) delay(350)
            _state.value = _state.value.copy(loading = true, error = null)
            _state.value = try {
                val results = if (nearValues) app.api.searchNearValues(q.ifEmpty { null }, kind) else app.api.search(q, kind)
                SearchState(results = results)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                SearchState(error = e.userMessage("Search failed. Please try again."))
            }
        }
    }
}

@Composable
fun SearchScreen() {
    val app = LocalAppContainer.current
    val vm: SearchViewModel = viewModel { SearchViewModel(app) }
    val navigator = LocalNavigator.current
    val state by vm.state.collectAsStateWithLifecycle()
    var query by rememberSaveable { mutableStateOf("") }
    var mode by rememberSaveable { mutableIntStateOf(0) } // 0 text, 1 near my values
    var scope by rememberSaveable { mutableStateOf<String?>(null) }
    val focus = remember { FocusRequester() }
    val focusManager = LocalFocusManager.current

    LaunchedEffect(query, mode, scope) { vm.search(query, mode == 1, scope) }
    LaunchedEffect(Unit) { focus.requestFocus() }

    Scaffold(topBar = { BackTopBar("Search", navigator::back) }) { padding ->
        LazyColumn(
            Modifier
                .padding(padding)
                .imePadding(),
            contentPadding = PaddingValues(start = ScreenPadding, end = ScreenPadding, bottom = 32.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            item(key = "field") {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    SegmentedTabs(listOf("Text search", "Near my values"), mode, {
                        mode = it
                        if (it == 1 && scope == "card") scope = null
                    })
                    OutlinedTextField(
                        value = query,
                        onValueChange = { query = it },
                        placeholder = {
                            Text(if (mode == 1) "Describe what matters — or leave empty to use your own values" else "Names, titles, descriptions, value cards…")
                        },
                        singleLine = true,
                        trailingIcon = {
                            if (query.isNotEmpty()) {
                                IconButton(onClick = { query = "" }) { Icon(Icons.Filled.Close, contentDescription = "Clear") }
                            }
                        },
                        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                        keyboardActions = KeyboardActions(onSearch = {
                            focusManager.clearFocus()
                            vm.search(query, mode == 1, scope, debounce = false)
                        }),
                        modifier = Modifier
                            .fillMaxWidth()
                            .focusRequester(focus),
                    )
                    Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        SCOPES.filter { mode == 0 || it.first != "card" }.forEach { (key, label) ->
                            FilterChip(selected = scope == key, onClick = { scope = key }, label = { Text(label) })
                        }
                    }
                    MetaText(
                        if (mode == 1) {
                            "Ranks by how close each value graph is to the values you describe, or to your own cards."
                        } else {
                            "Sphere-scoped openings, alliances and projects only show if you're in the sphere."
                        },
                        maxLines = 3,
                    )
                    if (state.loading) LinearProgressIndicator(Modifier.fillMaxWidth())
                }
            }
            val results = state.results
            when {
                state.error != null -> item { Text(state.error!!, color = MaterialTheme.colorScheme.error) }
                results == null && mode == 0 -> item { MetaText("Type at least two characters to search.") }
                results != null && results.groups.isEmpty() -> item {
                    MetaText(results.note ?: if (query.isBlank()) "Nothing found." else "Nothing found for “$query”.", maxLines = 3)
                }
            }
            results?.around?.takeIf { mode == 1 && query.isBlank() }?.let { around ->
                item(key = "around") {
                    MetaText("Around the value graph of ${around.name ?: "you"} (${around.cardCount} cards)")
                }
            }
            results?.groups?.forEach { group ->
                item(key = "g-" + group.kind) {
                    SectionHeading("${group.label} (${group.count})", Modifier.padding(top = 8.dp))
                }
                items(group.items, key = { "i-" + group.kind + (it.id ?: it.name) }) { item ->
                    ResultRow(item) { Links.parse(item.link)?.let(navigator::link) }
                }
            }
        }
    }
}

private fun counted(n: Int, noun: String) = "$n $noun${if (n == 1) "" else "s"}"

@Composable
private fun ResultRow(item: SearchItem, onClick: () -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        val group = CommunityKind.of(item.kind)
        when {
            group != null -> GroupAvatar(group, size = 40.dp)
            item.kind == "user" -> Avatar(item.id, item.name, size = 40.dp)
            item.kind == "card" -> Text("✶", color = valueCardAccent(null), style = MaterialTheme.typography.headlineSmall, modifier = Modifier.width(40.dp))
            else -> Text("◍", color = MaterialTheme.colorScheme.tertiary, style = MaterialTheme.typography.headlineSmall, modifier = Modifier.width(40.dp))
        }
        Spacer(Modifier.width(12.dp))
        Column(Modifier.weight(1f)) {
            Text(item.name, style = MaterialTheme.typography.titleSmall, maxLines = 1, overflow = TextOverflow.Ellipsis)
            item.summary?.takeIf { it.isNotBlank() }?.let {
                Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 2, overflow = TextOverflow.Ellipsis)
            }
            // As on the web: people have no members, and openings and cards no
            // value cards of their own, whatever counts the server sends.
            val meta = listOfNotNull(
                item.ownerName?.let { "Value card · $it" },
                item.sphereName?.takeIf { group != CommunityKind.Sphere },
                item.memberCount?.takeIf { group != null }?.let { counted(it, "member") },
                item.cardCount?.takeIf { group != null || item.kind == "user" }?.let { counted(it, "value card") },
                item.why.takeIf { it.isNotEmpty() }?.let { "shares: " + it.joinToString(", ") },
            )
            if (meta.isNotEmpty()) MetaText(meta.joinToString("  ·  "))
        }
    }
}
