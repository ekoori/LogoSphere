package com.krbavcic.logosphere.ui.communities

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.dp
import com.krbavcic.logosphere.core.logic.Dates
import com.krbavcic.logosphere.core.model.Announcements
import com.krbavcic.logosphere.core.model.ReportOf
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.common.BrandCard
import com.krbavcic.logosphere.ui.common.LinkText
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.ReallyDialog
import com.krbavcic.logosphere.ui.common.ReportLink
import com.krbavcic.logosphere.ui.common.SectionHeading

private const val TEXT_MAX = 2000

/** The top of a group's page for who is in it: its announcements, and inviting someone in. */
@OptIn(ExperimentalLayoutApi::class)
@Composable
internal fun GroupNews(
    groupId: String,
    news: Announcements?,
    viewerId: String?,
    canInvite: Boolean,
    busy: Boolean,
    onAnnounce: (String, () -> Unit) -> Unit,
    onRemove: (String) -> Unit,
    onInvite: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val navigator = LocalNavigator.current
    var all by rememberSaveable { mutableStateOf(false) }
    var writing by rememberSaveable { mutableStateOf(false) }
    var text by rememberSaveable { mutableStateOf("") }
    var removing by rememberSaveable { mutableStateOf<String?>(null) }
    val list = news?.announcements.orEmpty()

    Column(modifier, verticalArrangement = Arrangement.spacedBy(8.dp)) {
        if (news == null) MetaText("The announcements didn't load. Pull down to try again.", maxLines = 2)
        if (list.isNotEmpty()) {
            BrandCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    SectionHeading(if (list.size > 1) "Announcements" else "Announcement")
                    (if (all) list else list.take(1)).forEachIndexed { index, said ->
                        if (index > 0) HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                        Text(said.text, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.padding(top = 4.dp))
                        FlowRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            val author = said.author
                            if (author != null) LinkText(author.name ?: "A member", { navigator.person(author.id) })
                            MetaText(Dates.ago(said.at), Modifier.padding(vertical = 11.dp))
                            if (said.canRemove) LinkText("Remove", { removing = said.id }, enabled = !busy)
                            if (author != null && author.id != viewerId) ReportLink(ReportOf.announcement(said.id, groupId))
                        }
                    }
                    if (list.size > 1) {
                        LinkText(if (all) "Only the latest" else "Earlier ones (${list.size - 1})", { all = !all })
                    }
                }
            }
        }
        val announces = news?.canAnnounce == true
        if (announces || canInvite) {
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                if (announces) OutlinedButton(onClick = { writing = true }) { Text("Announce to members") }
                if (canInvite) OutlinedButton(onClick = onInvite, enabled = !busy) { Text("Invite someone") }
            }
        }
    }

    if (writing) {
        AlertDialog(
            onDismissRequest = { if (!busy) writing = false },
            title = { Text("Announce to its members") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = text,
                        onValueChange = { text = it.take(TEXT_MAX) },
                        minLines = 3,
                        keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences),
                        modifier = Modifier.fillMaxWidth(),
                    )
                    MetaText("They are notified that there is one. The words themselves are read here.", maxLines = 3)
                }
            },
            confirmButton = {
                TextButton(
                    enabled = !busy && text.isNotBlank(),
                    onClick = { onAnnounce(text) { text = ""; writing = false } },
                ) { Text(if (busy) "Sending…" else "Announce") }
            },
            dismissButton = { TextButton(onClick = { writing = false }, enabled = !busy) { Text("Cancel") } },
        )
    }
    removing?.let { id ->
        ReallyDialog(
            title = "Remove this announcement?",
            text = "It's gone for everyone.",
            confirm = "Remove",
            onConfirm = { onRemove(id) },
            onClose = { removing = null },
        )
    }
}
