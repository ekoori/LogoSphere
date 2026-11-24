package com.krbavcic.logosphere.ui.common

import android.os.Build
import android.widget.Toast
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Flag
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
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
import androidx.compose.ui.unit.dp
import com.krbavcic.logosphere.BuildConfig
import com.krbavcic.logosphere.core.api.userMessage
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LocalNavigator
import kotlinx.coroutines.launch
import kotlin.coroutines.cancellation.CancellationException

private const val NOTE_MAX = 1000

/** What a problem can be, in the words of the one reporting it. The server knows the same list. */
private val PROBLEMS = listOf("Doesn't work", "Confusing", "Wrong or missing", "An idea", "Other")

/**
 * The little flag on every screen (in its top bar, or on the sign-in pages): a few words about a
 * problem for LogoSphere's administrators, with where it happened. The server files it in
 * Cassandra with the other reports (POST /api/problems), signed in or not.
 */
@Composable
fun ProblemFlag(modifier: Modifier = Modifier) {
    val navigator = LocalNavigator.current
    var attached by remember { mutableStateOf<Map<String, String>?>(null) }
    IconButton(onClick = { attached = whatIsAttached(navigator.whereNow()) }, modifier = modifier) {
        Icon(Icons.Outlined.Flag, contentDescription = "Report a problem", tint = MaterialTheme.colorScheme.onSurfaceVariant)
    }
    attached?.let { ProblemDialog(it) { attached = null } }
}

/** Read when the flag is tapped, so the report says where the problem was seen. */
private fun whatIsAttached(screen: String): Map<String, String> = linkedMapOf(
    "screen" to screen,
    "app" to "LogoSphere ${BuildConfig.VERSION_NAME} (${BuildConfig.VERSION_CODE})",
    "android" to "Android ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT})",
)

@OptIn(ExperimentalLayoutApi::class, ExperimentalMaterial3Api::class)
@Composable
private fun ProblemDialog(attached: Map<String, String>, onClose: () -> Unit) {
    val app = LocalAppContainer.current
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val signedIn = app.session.user != null
    var kind by rememberSaveable { mutableStateOf<String?>(null) }
    var note by rememberSaveable { mutableStateOf("") }
    var showAttached by remember { mutableStateOf(false) }
    var sending by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }

    AlertDialog(
        onDismissRequest = { if (!sending) onClose() },
        icon = { Icon(Icons.Outlined.Flag, contentDescription = null) },
        title = { Text("Report a problem") },
        text = {
            Column(
                Modifier.heightIn(max = 520.dp).verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Text(
                    "Something that doesn't work, or could be better? Tell LogoSphere's administrators.",
                    style = MaterialTheme.typography.bodyMedium,
                )
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    PROBLEMS.forEach { choice ->
                        FilterChip(
                            selected = kind == choice,
                            onClick = { kind = choice.takeUnless { it == kind } },
                            label = { Text(choice) },
                        )
                    }
                }
                OutlinedTextField(
                    value = note,
                    onValueChange = { note = it.take(NOTE_MAX) },
                    label = { Text("What happened, and what did you expect?") },
                    minLines = 3,
                    keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences),
                    modifier = Modifier.fillMaxWidth(),
                )
                MetaText(
                    if (signedIn) "Only the administrators see it, with your name and what is attached."
                    else "Only the administrators see it, with what is attached. You're not signed in, so no name goes with it.",
                    maxLines = 4,
                )
                TextButton(onClick = { showAttached = !showAttached }) {
                    Text(if (showAttached) "Hide what is attached" else "Show what is attached")
                }
                if (showAttached) MetaText(attached.entries.joinToString("\n") { (key, value) -> "$key: $value" }, maxLines = 8)
                error?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
            }
        },
        confirmButton = {
            TextButton(
                enabled = !sending && note.isNotBlank(),
                onClick = {
                    sending = true
                    error = null
                    scope.launch {
                        try {
                            val said = app.api.reportProblem(kind ?: "Other", note, attached)
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
