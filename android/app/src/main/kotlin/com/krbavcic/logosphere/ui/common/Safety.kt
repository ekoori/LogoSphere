package com.krbavcic.logosphere.ui.common

import android.widget.Toast
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.unit.dp
import com.krbavcic.logosphere.core.api.userMessage
import com.krbavcic.logosphere.core.model.ReportOf
import com.krbavcic.logosphere.ui.LocalAppContainer
import kotlinx.coroutines.launch
import kotlin.coroutines.cancellation.CancellationException

private const val NOTE_MAX = 1000

/** "Report": a few words to the administrators. Nobody reported is told. */
@Composable
fun ReportLink(report: ReportOf, modifier: Modifier = Modifier, label: String = "Report") {
    var open by rememberSaveable(report.id) { mutableStateOf(false) }
    TextButton(onClick = { open = true }, modifier = modifier) {
        Text(label, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
    if (open) ReportDialog(report) { open = false }
}

@Composable
fun ReportDialog(report: ReportOf, onClose: () -> Unit) {
    val api = LocalAppContainer.current.api
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var note by rememberSaveable(report.id) { mutableStateOf("") }
    var sending by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }

    AlertDialog(
        onDismissRequest = { if (!sending) onClose() },
        title = { Text("Report") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = note,
                    onValueChange = { note = it.take(NOTE_MAX) },
                    label = { Text(if (report.needsNote) "What happened?" else "What is wrong? (optional)") },
                    keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences),
                    modifier = Modifier.fillMaxWidth(),
                )
                MetaText(
                    if (report.kind == "ai") "Only the platform's administrators see it, with what the AI gave you."
                    else "Only the platform's administrators see it. The person isn't told.",
                    maxLines = 3,
                )
                error?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
            }
        },
        confirmButton = {
            TextButton(
                enabled = !sending && (!report.needsNote || note.isNotBlank()),
                onClick = {
                    sending = true
                    error = null
                    scope.launch {
                        try {
                            val said = api.report(report, note)
                            Toast.makeText(context, said, Toast.LENGTH_LONG).show()
                            onClose()
                        } catch (e: CancellationException) {
                            throw e
                        } catch (e: Exception) {
                            error = e.userMessage("That didn't send. Please try again.")
                        } finally {
                            sending = false
                        }
                    }
                },
            ) { Text(if (sending) "Sending…" else "Send") }
        },
        dismissButton = { TextButton(onClick = onClose, enabled = !sending) { Text("Cancel") } },
    )
}

/** Asked before blocking, because it does several things at once. */
@Composable
fun BlockDialog(name: String, onBlock: () -> Unit, onClose: () -> Unit) {
    AlertDialog(
        onDismissRequest = onClose,
        title = { Text("Block $name?") },
        text = {
            Text(
                "While it stands you can't message, follow, take up each other's openings, acknowledge on each " +
                    "other's trails, or find each other nearby. They aren't told.",
            )
        },
        confirmButton = {
            TextButton(onClick = { onClose(); onBlock() }) { Text("Block", color = MaterialTheme.colorScheme.error) }
        },
        dismissButton = { TextButton(onClick = onClose) { Text("Cancel") } },
    )
}
