package com.krbavcic.logosphere.ui.common

import android.text.format.DateFormat
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.DatePicker
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TimePicker
import androidx.compose.material3.rememberDatePickerState
import androidx.compose.material3.rememberTimePickerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import com.krbavcic.logosphere.core.logic.Events
import java.time.Instant
import java.time.LocalDate
import java.time.LocalTime
import java.time.ZoneId
import java.time.ZoneOffset

@Composable
private fun TapField(label: String, value: String, onClick: () -> Unit, modifier: Modifier = Modifier) {
    OutlinedCard(onClick = onClick, modifier = modifier.fillMaxWidth()) {
        Column(Modifier.padding(horizontal = 16.dp, vertical = 10.dp)) {
            Text(label, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(value, style = MaterialTheme.typography.bodyLarge)
        }
    }
}

/** A day, chosen on a calendar. [onClear] lets it be none again. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DateField(
    label: String,
    value: LocalDate?,
    onChange: (LocalDate) -> Unit,
    modifier: Modifier = Modifier,
    empty: String = "Choose a day",
    onClear: (() -> Unit)? = null,
) {
    var open by rememberSaveable { mutableStateOf(false) }
    TapField(label, value?.let { Events.dateText(it) } ?: empty, { open = true }, modifier)
    if (!open) return
    // The picker counts days in UTC, whatever the phone's zone.
    val state = rememberDatePickerState(
        initialSelectedDateMillis = value?.atStartOfDay(ZoneOffset.UTC)?.toInstant()?.toEpochMilli(),
    )
    DatePickerDialog(
        onDismissRequest = { open = false },
        confirmButton = {
            TextButton(
                enabled = state.selectedDateMillis != null,
                onClick = {
                    open = false
                    state.selectedDateMillis?.let { onChange(Instant.ofEpochMilli(it).atZone(ZoneOffset.UTC).toLocalDate()) }
                },
            ) { Text("OK") }
        },
        dismissButton = {
            TextButton(onClick = { open = false; if (value != null) onClear?.invoke() }) {
                Text(if (onClear != null && value != null) "No date" else "Cancel")
            }
        },
    ) { DatePicker(state) }
}

/** A time of day, as the phone shows them. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TimeField(label: String, value: LocalTime?, onChange: (LocalTime) -> Unit, modifier: Modifier = Modifier) {
    var open by rememberSaveable { mutableStateOf(false) }
    TapField(label, value?.let { Events.clockText(it) } ?: "Choose a time", { open = true }, modifier)
    if (!open) return
    val state = rememberTimePickerState(
        initialHour = value?.hour ?: 18,
        initialMinute = value?.minute ?: 0,
        is24Hour = DateFormat.is24HourFormat(LocalContext.current),
    )
    AlertDialog(
        onDismissRequest = { open = false },
        title = { Text(label) },
        text = { Column(Modifier.verticalScroll(rememberScrollState())) { TimePicker(state) } },
        confirmButton = {
            TextButton(onClick = { open = false; onChange(LocalTime.of(state.hour, state.minute)) }) { Text("OK") }
        },
        dismissButton = { TextButton(onClick = { open = false }) { Text("Cancel") } },
    )
}

/** A time zone, found by a few letters of its name: there are some six hundred. */
@Composable
fun ZoneDialog(current: String, onChoose: (String) -> Unit, onClose: () -> Unit) {
    var looked by rememberSaveable { mutableStateOf("") }
    val all = remember {
        ZoneId.getAvailableZoneIds()
            .filter { ('/' in it && !it.startsWith("SystemV/") && !it.startsWith("Etc/")) || it == "UTC" }
            .sorted()
    }
    val shown = remember(looked) {
        val text = looked.trim().replace(' ', '_')
        if (text.isEmpty()) listOf(current) + all.filter { it != current } else all.filter { it.contains(text, ignoreCase = true) }
    }
    AlertDialog(
        onDismissRequest = onClose,
        title = { Text("Time zone") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = looked,
                    onValueChange = { looked = it },
                    label = { Text("A city") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                LazyColumn(Modifier.heightIn(max = 320.dp)) {
                    items(shown, key = { it }) { name ->
                        Text(
                            name.replace('_', ' ') + if (name == current) "  ✓" else "",
                            style = MaterialTheme.typography.bodyLarge,
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable(role = Role.Button) { onChoose(name) }
                                .padding(vertical = 12.dp),
                        )
                    }
                }
            }
        },
        confirmButton = { TextButton(onClick = onClose) { Text("Cancel") } },
    )
}
