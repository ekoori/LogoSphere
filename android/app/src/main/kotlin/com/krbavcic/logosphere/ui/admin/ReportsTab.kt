package com.krbavcic.logosphere.ui.admin

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.krbavcic.logosphere.AppContainer
import com.krbavcic.logosphere.core.logic.Dates
import com.krbavcic.logosphere.core.model.Report
import com.krbavcic.logosphere.core.model.Reports
import com.krbavcic.logosphere.ui.LoadViewModel
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.common.BrandCard
import com.krbavcic.logosphere.ui.common.Choice
import com.krbavcic.logosphere.ui.common.EmptyNote
import com.krbavcic.logosphere.ui.common.LoadContent
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.Picker
import com.krbavcic.logosphere.ui.common.Refreshable
import com.krbavcic.logosphere.ui.common.ScreenPadding
import com.krbavcic.logosphere.ui.common.SnackbarMessages

class AdminReportsViewModel(private val app: AppContainer) : LoadViewModel<Reports>() {
    var status = "open"
        private set

    init {
        load()
    }

    override suspend fun fetch(force: Boolean): Reports = app.api.adminReports(status)

    fun show(status: String) {
        if (status == this.status) return
        this.status = status
        load()
    }

    fun settle(report: Report, outcome: String, note: String, remove: Boolean) = act(onSuccess = {
        say(if (remove) "Removed, and the report closed." else "Report closed.")
        reload()
    }) { app.api.settleReport(report.id, outcome, note, remove) }
}

private data class Settling(val report: Report, val status: String, val remove: Boolean = false)

/** What members reported. It is all of a private message an administrator ever sees. */
@OptIn(ExperimentalLayoutApi::class)
@Composable
internal fun ReportsTab(snackbar: SnackbarHostState) {
    val app = LocalAppContainer.current
    val navigator = LocalNavigator.current
    val vm: AdminReportsViewModel = viewModel { AdminReportsViewModel(app) }
    val state by vm.state.collectAsStateWithLifecycle()
    val refreshing by vm.refreshing.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    SnackbarMessages(vm.messages, snackbar)
    var settling by remember { mutableStateOf<Settling?>(null) }

    LoadContent(state, onRetry = vm::load) { data ->
        Refreshable(refreshing, vm::refresh) {
            LazyColumn(
                contentPadding = PaddingValues(start = ScreenPadding, end = ScreenPadding, bottom = 32.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                item(key = "filter") {
                    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Picker(
                            label = "Show (${data.open} waiting)",
                            choices = listOf(
                                Choice("open", "Waiting"),
                                Choice("handled", "Handled"),
                                Choice("dismissed", "Dismissed"),
                                Choice("all", "All"),
                            ),
                            selected = vm.status,
                            onSelect = { it?.let(vm::show) },
                        )
                        MetaText("A report is all of a private message an administrator ever sees. Nobody reported is told.", maxLines = 3)
                    }
                }
                if (data.reports.isEmpty()) item { EmptyNote("None.") }
                items(data.reports, key = { it.id }) { report ->
                    BrandCard(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Text(
                                report.what + (report.subject?.name?.let { " by $it" } ?: ""),
                                style = MaterialTheme.typography.titleSmall,
                            )
                            MetaText("Reported by ${report.reporter?.name ?: "a member"} on ${Dates.day(report.madeAt)}", maxLines = 2)
                            if (report.excerpt.isNotBlank()) Text("“${report.excerpt}”", style = MaterialTheme.typography.bodyLarge)
                            if (report.note.isNotBlank()) Text(report.note, style = MaterialTheme.typography.bodyMedium)
                            if (report.status != "open") {
                                val by = report.handledBy?.name?.let { " by $it" }.orEmpty()
                                val outcome = if (report.outcome.isBlank()) "" else ": ${report.outcome}"
                                MetaText((if (report.status == "handled") "Handled" else "Dismissed") + by + outcome, maxLines = 3)
                            }
                            FlowRow(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                report.subject?.let { who -> TextButton(onClick = { navigator.person(who.id) }) { Text("Their page") } }
                                if (report.kind == "opening") {
                                    report.itemId?.let { id -> TextButton(onClick = { navigator.opening(id) }) { Text("The opening") } }
                                }
                                if (report.status == "open") {
                                    TextButton(onClick = { settling = Settling(report, "handled") }, enabled = !busy) { Text("Handled") }
                                    TextButton(onClick = { settling = Settling(report, "dismissed") }, enabled = !busy) { Text("Dismiss") }
                                    if (report.removable) {
                                        TextButton(onClick = { settling = Settling(report, "handled", remove = true) }, enabled = !busy) {
                                            Text("Remove it", color = MaterialTheme.colorScheme.error)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    settling?.let { closing ->
        var note by rememberSaveable(closing.report.id) { mutableStateOf("") }
        AlertDialog(
            onDismissRequest = { settling = null },
            title = { Text(if (closing.remove) "Remove it for good?" else "Close this report?") },
            text = {
                OutlinedTextField(
                    value = note,
                    onValueChange = { note = it.take(1000) },
                    label = { Text("What you did (optional)") },
                    modifier = Modifier.fillMaxWidth(),
                )
            },
            confirmButton = {
                TextButton(onClick = {
                    settling = null
                    vm.settle(closing.report, closing.status, note, closing.remove)
                }) { Text(if (closing.remove) "Remove" else "Close it") }
            },
            dismissButton = { TextButton(onClick = { settling = null }) { Text("Cancel") } },
        )
    }
}
