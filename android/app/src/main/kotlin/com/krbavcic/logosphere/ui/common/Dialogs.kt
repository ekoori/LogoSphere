package com.krbavcic.logosphere.ui.common

import android.content.Intent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.unit.dp
import com.krbavcic.logosphere.core.logic.Dates
import com.krbavcic.logosphere.core.model.NewInvite
import com.krbavcic.logosphere.ui.LocalAppContainer

/** Asked before what can't be undone. */
@Composable
fun ReallyDialog(title: String, text: String, confirm: String, onConfirm: () -> Unit, onClose: () -> Unit) {
    AlertDialog(
        onDismissRequest = onClose,
        title = { Text(title) },
        text = { Text(text) },
        confirmButton = {
            TextButton(onClick = { onClose(); onConfirm() }) { Text(confirm, color = MaterialTheme.colorScheme.error) }
        },
        dismissButton = { TextButton(onClick = onClose) { Text("No") } },
    )
}

/** An invitation link just made, to share or copy. It isn't shown again once closed. */
@Composable
fun InviteDialog(invite: NewInvite, onClose: () -> Unit) {
    val link = LocalAppContainer.current.api.webUrl(invite.path)
    val clipboard = LocalClipboardManager.current
    val context = LocalContext.current
    AlertDialog(
        onDismissRequest = onClose,
        title = { Text(invite.group?.let { "A link into ${it.name}" } ?: "A link to LogoSphere") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                SelectionContainer {
                    Text(link, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.primary)
                }
                Text(
                    "It works for up to ${invite.mostUses} people until ${Dates.day(invite.expiresAt)}, and it isn't shown " +
                        "again. Whoever holds it can use it and sees your name. Revoke it under Me → Password, email, " +
                        "data & account.",
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        },
        confirmButton = {
            TextButton(onClick = {
                val send = Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, link)
                context.startActivity(Intent.createChooser(send, "Share the invitation"))
            }) { Text("Share") }
        },
        dismissButton = {
            Row {
                TextButton(onClick = { clipboard.setText(AnnotatedString(link)) }) { Text("Copy") }
                TextButton(onClick = onClose) { Text("Close") }
            }
        },
    )
}
