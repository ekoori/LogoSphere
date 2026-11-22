package com.krbavcic.logosphere.ui.common

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import com.krbavcic.logosphere.core.model.GroupSummary

/** A tick box and its words, all of it tappable. */
@Composable
fun CheckRow(label: String, checked: Boolean, onChange: (Boolean) -> Unit, modifier: Modifier = Modifier) {
    Row(
        modifier
            .fillMaxWidth()
            .toggleable(value = checked, role = Role.Checkbox, onValueChange = onChange)
            .heightIn(min = 48.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Checkbox(checked = checked, onCheckedChange = null)
        Text(label, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.weight(1f).padding(vertical = 8.dp))
    }
}

/** Which other spheres an opening is shared with. */
@Composable
fun SharePicker(choices: List<GroupSummary>, chosen: List<String>, onChange: (List<String>) -> Unit, modifier: Modifier = Modifier) {
    Column(modifier) {
        Text("Share it with your other spheres too", style = MaterialTheme.typography.titleSmall)
        choices.forEach { sphere ->
            CheckRow(sphere.name, sphere.id in chosen, { on -> onChange(if (on) chosen + sphere.id else chosen - sphere.id) })
        }
        MetaText(
            "People there will see the opening, who posted it and which sphere it comes from. Never that sphere's other people.",
            maxLines = 4,
        )
    }
}

@Composable
fun ShareDialog(
    choices: List<GroupSummary>,
    already: List<GroupSummary>,
    busy: Boolean,
    onSave: (List<String>) -> Unit,
    onClose: () -> Unit,
) {
    var chosen by rememberSaveable { mutableStateOf(already.map { it.id }) }
    AlertDialog(
        onDismissRequest = { if (!busy) onClose() },
        title = { Text("Sharing") },
        text = { SharePicker(choices, chosen, { chosen = it }, Modifier.verticalScroll(rememberScrollState())) },
        confirmButton = { TextButton(onClick = { onSave(chosen) }, enabled = !busy) { Text(if (busy) "Saving…" else "Save") } },
        dismissButton = { TextButton(onClick = onClose, enabled = !busy) { Text("Cancel") } },
    )
}
