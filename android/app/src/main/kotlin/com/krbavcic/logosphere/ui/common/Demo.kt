package com.krbavcic.logosphere.ui.common

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp
import com.krbavcic.logosphere.core.model.DemoStatus
import com.krbavcic.logosphere.ui.theme.Brand

/**
 * "Try the demo spheres": shown on the Trail to a member who is in none of
 * them, until they join or dismiss it. New members are invited, not enrolled.
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
fun DemoInviteCard(invite: DemoStatus, onJoin: () -> Unit, onLook: () -> Unit, onDismiss: () -> Unit) {
    val names = invite.spheres.map { it.name }
    Column(
        Modifier
            .fillMaxWidth()
            .clip(MaterialTheme.shapes.large)
            .background(Brand.colors.demoWash)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Try the demo spheres", style = MaterialTheme.typography.titleMedium, color = Brand.colors.onDemoWash)
            DemoTag()
        }
        Text(
            "${names.joinToString(", ")}: AI personas play everyday neighbours there. Post a need, accept an " +
                "offer, write a receipt, and see how LogoSphere feels. Nothing there is real.",
            style = MaterialTheme.typography.bodyMedium,
            color = Brand.colors.onDemoWash,
        )
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Button(onClick = onJoin) { Text("Join all ${names.size}") }
            TextButton(onClick = onLook) { Text("Look first") }
            TextButton(onClick = onDismiss) { Text("Not now") }
        }
    }
}
