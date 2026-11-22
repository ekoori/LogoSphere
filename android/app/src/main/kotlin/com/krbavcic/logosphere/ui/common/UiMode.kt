package com.krbavcic.logosphere.ui.common

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.selection.selectable
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.compositionLocalOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import com.krbavcic.logosphere.core.api.userMessage
import com.krbavcic.logosphere.core.logic.UiMode
import com.krbavcic.logosphere.ui.LocalAppContainer
import kotlinx.coroutines.launch
import kotlin.coroutines.cancellation.CancellationException

/** Whether the member is in Simple ([UiMode]). Screens use it for what to show, never for what's allowed. */
val LocalSimple = compositionLocalOf { false }

/** Where Simple leaves options out of a form, with the way back to them. */
@Composable
fun MoreInAdvanced(what: String, modifier: Modifier = Modifier) {
    if (!LocalSimple.current) return
    val app = LocalAppContainer.current
    val scope = rememberCoroutineScope()
    var busy by remember { mutableStateOf(false) }
    var problem by remember { mutableStateOf<String?>(null) }
    Column(modifier) {
        MetaText("$what in Advanced.", maxLines = 3)
        LinkText(
            "Switch to Advanced",
            enabled = !busy,
            onClick = {
                scope.launch {
                    busy = true
                    problem = null
                    try {
                        app.session.setUiMode(UiMode.Advanced)
                    } catch (e: CancellationException) {
                        throw e
                    } catch (e: Exception) {
                        problem = e.userMessage()
                    } finally {
                        busy = false
                    }
                }
            },
        )
        problem?.let { Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error) }
    }
}

/** Me → Simple or Advanced. */
@Composable
fun UiModeDialog(current: UiMode, onChoose: (UiMode) -> Unit, onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Simple or Advanced") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("This changes only how much you're shown, here and on the site. Nothing of yours is lost by switching.")
                UiMode.entries.forEach { mode ->
                    Row(
                        Modifier
                            .fillMaxWidth()
                            .selectable(selected = mode == current, role = Role.RadioButton) { onChoose(mode) }
                            .padding(vertical = 12.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        RadioButton(selected = mode == current, onClick = null)
                        Column {
                            Text(mode.label, style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.onSurface)
                            Text(mode.about, style = MaterialTheme.typography.bodyMedium)
                        }
                    }
                }
            }
        },
        confirmButton = { TextButton(onClick = onDismiss) { Text("Close") } },
    )
}
