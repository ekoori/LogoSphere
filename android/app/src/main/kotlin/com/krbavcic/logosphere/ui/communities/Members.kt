package com.krbavcic.logosphere.ui.communities

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.krbavcic.logosphere.core.logic.Roles
import com.krbavcic.logosphere.core.model.Community
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.Member
import com.krbavcic.logosphere.core.model.PersonRef
import com.krbavcic.logosphere.ui.common.Avatar
import com.krbavcic.logosphere.ui.common.EmptyNote
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.PersonaTag
import com.krbavcic.logosphere.ui.common.QuietPill
import com.krbavcic.logosphere.ui.common.ScreenPadding
import com.krbavcic.logosphere.ui.common.SectionHeading

private val ROLE_TIERS = mapOf(
    CommunityKind.Sphere to listOf("admin" to "Admins", "member" to "Members"),
    CommunityKind.Alliance to listOf("admin" to "Lead", "steward" to "Board members", "member" to "Members"),
    CommunityKind.Project to listOf("manager" to "Manager", "steward" to "Stewards", "contributor" to "Contributors", "observer" to "Observers"),
)

/**
 * A group's people as list items, in role tiers. Whoever may set roles (the founder, a platform
 * admin) also sees join requests to approve or decline, and each other member's role actions.
 */
fun LazyListScope.memberItems(
    community: Community,
    viewerId: String?,
    canSetRoles: Boolean,
    busy: Boolean,
    onSetRole: (memberId: String, role: String) -> Unit,
    onOpen: (memberId: String) -> Unit,
) {
    val kind = community.kind
    val members = community.members.filter { it.role != "pending" }
    if (canSetRoles && community.pendingMembers.isNotEmpty()) {
        item(key = "pending-head") {
            SectionHeading("Awaiting approval (${community.pendingMembers.size})", Modifier.padding(horizontal = ScreenPadding, vertical = 4.dp))
        }
        items(community.pendingMembers, key = { "pending-" + it.id }) { person ->
            PendingRow(person, kind, busy, onSetRole, onOpen)
        }
    }
    val tiers = ROLE_TIERS.getValue(kind)
    val known = tiers.map { it.first }.toSet()
    tiers.forEach { (role, label) ->
        val people = members.filter { it.role == role || (role == tiers.last().first && it.role !in known) }
        if (people.isNotEmpty()) {
            item(key = "tier-$role") {
                SectionHeading("$label (${people.size})", Modifier.padding(horizontal = ScreenPadding, vertical = 4.dp))
            }
            items(people, key = { "m-$role-" + it.id }) { member ->
                MemberRow(member, kind, isSelf = member.id == viewerId, canSetRoles = canSetRoles, busy = busy, onSetRole = onSetRole, onOpen = onOpen)
            }
        }
    }
    if (members.isEmpty()) item(key = "no-members") { EmptyNote("No members yet.") }
}

@Composable
private fun PendingRow(person: PersonRef, kind: CommunityKind, busy: Boolean, onSetRole: (String, String) -> Unit, onOpen: (String) -> Unit) {
    Column(Modifier.padding(horizontal = ScreenPadding, vertical = 6.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(Modifier.fillMaxWidth().clickable { onOpen(person.id) }, verticalAlignment = Alignment.CenterVertically) {
            Avatar(person.id, person.name, size = 36.dp)
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(person.name ?: "Member", style = MaterialTheme.typography.titleSmall)
                MetaText("Asked to join")
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { onSetRole(person.id, Roles.defaultRole(kind)) }, enabled = !busy, modifier = Modifier.weight(1f)) { Text("✓ Approve") }
            OutlinedButton(onClick = { onSetRole(person.id, Roles.REMOVE) }, enabled = !busy, modifier = Modifier.weight(1f)) { Text("Decline") }
        }
    }
}

@Composable
private fun MemberRow(
    member: Member,
    kind: CommunityKind,
    isSelf: Boolean,
    canSetRoles: Boolean,
    busy: Boolean,
    onSetRole: (String, String) -> Unit,
    onOpen: (String) -> Unit,
) {
    var menu by remember { mutableStateOf(false) }
    var confirmRemove by remember { mutableStateOf(false) }
    val actions = Roles.actions(kind, member)
    val removable = Roles.canRemove(kind, member)
    Row(
        Modifier
            .fillMaxWidth()
            .clickable { onOpen(member.id) }
            .padding(start = ScreenPadding, end = 4.dp, top = 6.dp, bottom = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Avatar(member.id, member.name, size = 36.dp)
        Spacer(Modifier.width(12.dp))
        Column(Modifier.weight(1f)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                Text((member.name ?: "Member") + if (isSelf) " (you)" else "", style = MaterialTheme.typography.titleSmall, modifier = Modifier.weight(1f, fill = false))
                if (member.isAgent) PersonaTag(compact = true)
            }
        }
        QuietPill(Roles.label(kind, member.role))
        if (canSetRoles && !isSelf && (actions.isNotEmpty() || removable)) {
            Box {
                IconButton(onClick = { menu = true }, enabled = !busy) {
                    Icon(Icons.Filled.MoreVert, contentDescription = "Change ${member.name ?: "this member"}'s role")
                }
                DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                    actions.forEach { action ->
                        DropdownMenuItem(text = { Text(action.label) }, onClick = { menu = false; onSetRole(member.id, action.role) })
                    }
                    if (removable) {
                        DropdownMenuItem(
                            text = { Text("Remove from the ${kind.noun.lowercase()}", color = MaterialTheme.colorScheme.error) },
                            onClick = { menu = false; confirmRemove = true },
                        )
                    }
                }
            }
        } else {
            Spacer(Modifier.width(12.dp))
        }
    }
    if (confirmRemove) {
        AlertDialog(
            onDismissRequest = { confirmRemove = false },
            title = { Text("Remove ${member.name ?: "this member"}?") },
            text = { Text("They leave the ${kind.noun.lowercase()} and can ask to join again.") },
            confirmButton = { TextButton(onClick = { confirmRemove = false; onSetRole(member.id, Roles.REMOVE) }) { Text("Remove") } },
            dismissButton = { TextButton(onClick = { confirmRemove = false }) { Text("Keep") } },
        )
    }
}
