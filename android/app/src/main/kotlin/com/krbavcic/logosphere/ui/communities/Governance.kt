package com.krbavcic.logosphere.ui.communities

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.krbavcic.logosphere.AppContainer
import com.krbavcic.logosphere.core.logic.Dates
import com.krbavcic.logosphere.core.logic.Policies
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.GroupGovernance
import com.krbavcic.logosphere.core.model.GroupPolicy
import com.krbavcic.logosphere.core.model.NewProposal
import com.krbavcic.logosphere.core.model.Proposal
import com.krbavcic.logosphere.core.model.Tally
import com.krbavcic.logosphere.data.Change
import com.krbavcic.logosphere.ui.Load
import com.krbavcic.logosphere.ui.LoadViewModel
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.common.BrandCard
import com.krbavcic.logosphere.ui.common.Choice
import com.krbavcic.logosphere.ui.common.LinkText
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.Picker
import com.krbavcic.logosphere.ui.common.Pill
import com.krbavcic.logosphere.ui.common.QuietPill
import com.krbavcic.logosphere.ui.common.SectionHeading
import com.krbavcic.logosphere.ui.common.SegmentedTabs
import com.krbavcic.logosphere.ui.common.SnackbarMessages
import com.krbavcic.logosphere.ui.theme.Brand

class GovernanceViewModel(
    private val app: AppContainer,
    private val kind: CommunityKind,
    private val id: String,
) : LoadViewModel<GroupGovernance>() {
    val viewerId: String? get() = app.session.user?.id

    init {
        load()
    }

    override suspend fun fetch(force: Boolean): GroupGovernance = app.api.governance(kind, id)

    /** A passed policy proposal changes the group itself: everything showing it re-fetches. */
    private suspend fun changed() {
        reload()
        app.communities.invalidate(kind)
        app.changes.emit(Change.Communities)
    }

    fun vote(proposal: Proposal, choice: String) = act(onSuccess = { changed() }) { app.api.vote(kind, id, proposal.id, choice) }

    fun close(proposal: Proposal) = act(onSuccess = { changed() }) { app.api.closeProposal(kind, id, proposal.id) }

    fun withdraw(proposal: Proposal) = act(onSuccess = { changed() }) { app.api.withdrawProposal(kind, id, proposal.id) }

    fun delegate(delegateId: String?) = act(onSuccess = {
        reload()
        say(if (delegateId == null) "You vote for yourself again." else "Your vote is lent.")
    }) { app.api.delegateVote(kind, id, delegateId) }

    fun propose(proposal: NewProposal, onDone: () -> Unit) = act(onSuccess = {
        onDone()
        changed()
        say("The vote is open.")
    }) { app.api.propose(kind, id, proposal) }
}

/**
 * Liquid democracy for a group (the web's GovernancePanel): its policies, your vote (cast
 * yourself or lent to a member you trust), open proposals to vote on and decided ones.
 */
@Composable
fun GovernancePanel(
    kind: CommunityKind,
    id: String,
    snackbar: SnackbarHostState,
    onManage: (() -> Unit)?,
    modifier: Modifier = Modifier,
) {
    val app = LocalAppContainer.current
    val vm: GovernanceViewModel = viewModel(key = "governance-$kind-$id") { GovernanceViewModel(app, kind, id) }
    val state by vm.state.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    SnackbarMessages(vm.messages, snackbar)
    when (val s = state) {
        Load.Loading -> Box(modifier.fillMaxWidth().padding(24.dp), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
        is Load.Failed -> Column(modifier, verticalArrangement = Arrangement.spacedBy(8.dp)) {
            MetaText(s.message, maxLines = 4)
            OutlinedButton(onClick = vm::load) { Text("Try again") }
        }
        is Load.Ready -> GovernanceContent(kind, s.value, vm, busy, onManage, modifier)
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun GovernanceContent(
    kind: CommunityKind,
    g: GroupGovernance,
    vm: GovernanceViewModel,
    busy: Boolean,
    onManage: (() -> Unit)?,
    modifier: Modifier,
) {
    val me = vm.viewerId
    var proposing by rememberSaveable { mutableStateOf(false) }
    Column(modifier, verticalArrangement = Arrangement.spacedBy(16.dp)) {
        BrandCard(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                SectionHeading("How this ${kind.noun.lowercase()} decides")
                Text(
                    buildAnnotatedString {
                        append("Any member can propose a change; everyone votes, or lends their vote to someone they trust. Proposals pass by ")
                        withStyle(SpanStyle(fontWeight = FontWeight.Bold)) { append(Policies.decisionCopy(g.decisionPolicy)) }
                        append(". A lent vote follows its delegate (even when they lend it on), and voting yourself always overrides it.")
                    },
                    style = MaterialTheme.typography.bodyMedium,
                )
                g.policies.forEach { (key, policy) ->
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(policy.label, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.weight(1f))
                        Text(
                            Policies.valueLabel(policy.value ?: if (key == "join_policy") "open" else null),
                            style = MaterialTheme.typography.bodyMedium,
                            fontWeight = FontWeight.SemiBold,
                        )
                    }
                }
                if (g.canManage && onManage != null) {
                    LinkText("As a manager you can also set these directly →", onClick = onManage)
                }
            }
        }

        if (g.isMember) {
            BrandCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    SectionHeading("Your vote")
                    Picker(
                        label = "Cast by",
                        choices = listOf(Choice(null, "Yourself")) + g.members.filter { it.id != me }.map { Choice(it.id, it.name ?: "Member") },
                        selected = g.myDelegate?.id,
                        onSelect = { if (it != g.myDelegate?.id) vm.delegate(it) },
                        enabled = !busy,
                    )
                    g.myDelegate?.let { MetaText("${it.name ?: "Your delegate"} votes for you unless you vote yourself.", maxLines = 2) }
                    if (g.delegatedToMe.isNotEmpty()) {
                        MetaText(
                            "Voting on behalf of ${g.delegatedToMe.joinToString { it.name ?: "a member" }} — your vote carries their weight too.",
                            maxLines = 3,
                        )
                    }
                }
            }
        }

        SectionHeading("Open proposals (${g.open.size})") {
            if (g.isMember) TextButton(onClick = { proposing = !proposing }) { Text(if (proposing) "Cancel" else "+ Propose") }
        }
        if (proposing) ProposeForm(g.policies, busy) { proposal -> vm.propose(proposal) { proposing = false } }
        if (g.open.isEmpty() && !proposing) MetaText("Nothing is being voted on right now.")
        g.open.forEach { p ->
            ProposalCard(p, canManage = g.canManage, isMine = p.createdBy == me, busy = busy, onVote = { vm.vote(p, it) }, onClose = { vm.close(p) }, onWithdraw = { vm.withdraw(p) })
        }
        if (g.decided.isNotEmpty()) {
            SectionHeading("Decided (${g.decided.size})")
            g.decided.forEach { p ->
                ProposalCard(p, canManage = false, isMine = false, busy = busy, onVote = {}, onClose = {}, onWithdraw = {})
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun ProposalCard(
    p: Proposal,
    canManage: Boolean,
    isMine: Boolean,
    busy: Boolean,
    onVote: (String) -> Unit,
    onClose: () -> Unit,
    onWithdraw: () -> Unit,
) {
    var confirm by rememberSaveable(p.id) { mutableStateOf<String?>(null) }
    BrandCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                StatusPill(p.status)
                QuietPill(if (p.isPolicy) "Policy change" else "Motion")
            }
            MetaText(
                "by ${p.createdByName ?: "a member"} · " +
                    if (p.isOpen) "closes ${Dates.shortDay(p.closesAt)}" else "closed ${Dates.shortDay(p.closedAt)}",
            )
            Text(p.title, style = MaterialTheme.typography.titleMedium)
            if (p.isPolicy) {
                Text(
                    buildAnnotatedString {
                        append("Set ")
                        withStyle(SpanStyle(fontWeight = FontWeight.Bold)) { append(p.policyLabel ?: p.policyKey.orEmpty()) }
                        append(" to ")
                        withStyle(SpanStyle(fontWeight = FontWeight.Bold)) { append(Policies.valueLabel(p.policyValue)) }
                        if (p.status == "passed") append(" — applied.")
                    },
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
            p.description?.takeIf { it.isNotBlank() }?.let { Text(it, style = MaterialTheme.typography.bodyMedium) }
            p.tally?.let { TallyBar(it) }
            if (p.isOpen) {
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    listOf("yes", "no", "abstain").forEach { choice ->
                        FilterChip(
                            selected = p.myVote == choice,
                            onClick = { if (p.myVote != choice) onVote(choice) },
                            enabled = !busy,
                            label = { Text((if (p.myVote == choice) "✓ " else "") + choice.replaceFirstChar { it.uppercase() }) },
                        )
                    }
                }
                MetaText(if (p.wouldPass) "Would pass as it stands" else "Would not pass as it stands")
                Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    if (canManage) TextButton(onClick = { confirm = "close" }, enabled = !busy) { Text("Count now") }
                    if (isMine) TextButton(onClick = { confirm = "withdraw" }, enabled = !busy) { Text("Withdraw") }
                }
            }
        }
    }
    when (confirm) {
        "close" -> AlertDialog(
            onDismissRequest = { confirm = null },
            title = { Text("Count the votes now?") },
            text = { Text("Voting ends and the proposal passes or fails on the votes cast so far.") },
            confirmButton = { TextButton(onClick = { confirm = null; onClose() }) { Text("Count now") } },
            dismissButton = { TextButton(onClick = { confirm = null }) { Text("Keep it open") } },
        )
        "withdraw" -> AlertDialog(
            onDismissRequest = { confirm = null },
            title = { Text("Withdraw your proposal?") },
            text = { Text("Voting ends and nothing changes.") },
            confirmButton = { TextButton(onClick = { confirm = null; onWithdraw() }) { Text("Withdraw") } },
            dismissButton = { TextButton(onClick = { confirm = null }) { Text("Keep it") } },
        )
    }
}

@Composable
private fun StatusPill(status: String) {
    val c = Brand.colors
    when (status) {
        "passed" -> Pill("Passed", c.doneWash, c.onDoneWash)
        "rejected" -> Pill("Rejected", MaterialTheme.colorScheme.errorContainer, MaterialTheme.colorScheme.onErrorContainer)
        "withdrawn" -> QuietPill("Withdrawn")
        else -> Pill("Open", c.offerWash, c.onOfferWash)
    }
}

/** Weighted yes / no / abstain against everyone who could be represented. */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun TallyBar(t: Tally) {
    val cast = t.yes + t.no + t.abstain
    val total = maxOf(t.eligible, cast, 1).toFloat()
    val yes = MaterialTheme.colorScheme.primary
    val no = MaterialTheme.colorScheme.error
    val abstain = MaterialTheme.colorScheme.outline
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Row(
            Modifier
                .fillMaxWidth()
                .height(8.dp)
                .clip(CircleShape)
                .background(MaterialTheme.colorScheme.surfaceVariant)
                .semantics { contentDescription = "${t.yes} yes, ${t.no} no, ${t.abstain} abstain of ${t.eligible} members" },
        ) {
            listOf(t.yes to yes, t.no to no, t.abstain to abstain).forEach { (n, color) ->
                if (n > 0) Box(Modifier.weight(n / total).fillMaxHeight().background(color))
            }
            val rest = total - cast
            if (rest > 0) Box(Modifier.weight(rest / total).fillMaxHeight().background(Color.Transparent))
        }
        FlowRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            MetaText("${t.yes} yes")
            MetaText("${t.no} no")
            MetaText("${t.abstain} abstain")
            MetaText("${t.unrepresented} of ${t.eligible} not represented")
            t.directVotes?.let { MetaText("$it voted directly") }
        }
    }
}

@Composable
private fun ProposeForm(policies: Map<String, GroupPolicy>, busy: Boolean, onSubmit: (NewProposal) -> Unit) {
    var isPolicy by rememberSaveable { mutableIntStateOf(if (policies.isNotEmpty()) 0 else 1) }
    var policyKey by rememberSaveable { mutableStateOf(policies.keys.firstOrNull()) }
    var policyValue by rememberSaveable { mutableStateOf<String?>(null) }
    var title by rememberSaveable { mutableStateOf("") }
    var description by rememberSaveable { mutableStateOf("") }
    var days by rememberSaveable { mutableIntStateOf(7) }
    val policy = policyKey?.let { policies[it] }
    val options = if (policyKey != null && policy != null) Policies.proposalOptions(policyKey!!, policy) else emptyList()
    val ready = if (isPolicy == 0) policyKey != null && policyValue != null else title.isNotBlank()

    BrandCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            SegmentedTabs(listOf("Change a policy", "A motion"), isPolicy, { isPolicy = it })
            if (isPolicy == 0) {
                Picker(
                    label = "Policy",
                    choices = policies.map { (k, v) -> Choice(k, "${v.label} (now: ${Policies.valueLabel(v.value ?: if (k == "join_policy") "open" else null)})") },
                    selected = policyKey,
                    onSelect = { policyKey = it; policyValue = null },
                )
                Picker(
                    label = "Change to",
                    choices = listOf(Choice(null, "— choose —")) + options.map { Choice(it, Policies.valueLabel(it)) },
                    selected = policyValue,
                    onSelect = { policyValue = it },
                )
            } else {
                OutlinedTextField(
                    value = title,
                    onValueChange = { title = it },
                    label = { Text("What are you proposing?") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences),
                    modifier = Modifier.fillMaxWidth(),
                )
            }
            OutlinedTextField(
                value = description,
                onValueChange = { description = it },
                label = { Text(if (isPolicy == 0) "Why? (optional)" else "Details (optional)") },
                keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences),
                modifier = Modifier.fillMaxWidth().heightIn(min = 80.dp),
            )
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Open for", style = MaterialTheme.typography.bodyMedium)
                OutlinedButton(onClick = { if (days > 1) days-- }, enabled = days > 1, contentPadding = PaddingValues(0.dp)) { Text("−") }
                Text("$days day${if (days == 1) "" else "s"}", style = MaterialTheme.typography.titleSmall)
                OutlinedButton(onClick = { if (days < 30) days++ }, enabled = days < 30, contentPadding = PaddingValues(0.dp)) { Text("+") }
            }
            Button(
                onClick = {
                    onSubmit(
                        if (isPolicy == 0) NewProposal("policy", "", description, days, policyKey, policyValue)
                        else NewProposal("motion", title, description, days),
                    )
                },
                enabled = ready && !busy,
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Open the vote") }
        }
    }
}
