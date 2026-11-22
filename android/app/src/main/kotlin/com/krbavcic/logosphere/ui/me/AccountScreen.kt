package com.krbavcic.logosphere.ui.me

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.krbavcic.logosphere.AppContainer
import com.krbavcic.logosphere.core.logic.Dates
import com.krbavcic.logosphere.core.model.BlockedPerson
import com.krbavcic.logosphere.core.model.EmailSettings
import com.krbavcic.logosphere.core.model.Invite
import com.krbavcic.logosphere.core.model.NewInvite
import com.krbavcic.logosphere.ui.Load
import com.krbavcic.logosphere.ui.LoadViewModel
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.common.BackTopBar
import com.krbavcic.logosphere.ui.common.BrandCard
import com.krbavcic.logosphere.ui.common.InviteDialog
import com.krbavcic.logosphere.ui.common.LinkText
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.ReallyDialog
import com.krbavcic.logosphere.ui.common.ScreenPadding
import com.krbavcic.logosphere.ui.common.SectionHeading
import com.krbavcic.logosphere.ui.common.SnackbarMessages
import com.krbavcic.logosphere.ui.common.readable
import java.time.LocalDate
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch

/** The fewest characters a password may have (the server's rule). */
private const val MIN_PASSWORD = 8

class AccountViewModel(private val app: AppContainer) : LoadViewModel<EmailSettings>() {
    init {
        load()
    }

    // Only the Email card waits on this: the rest of the screen works without it.
    override suspend fun fetch(force: Boolean): EmailSettings = app.api.emailSettings()

    fun toggleTopic(key: String) {
        val was = current ?: return
        act {
            val saved = app.api.chooseEmailTopics(was.toggled(key))
            update { saved }
            if (saved.confirmationSent) say("Saved. Now open the link we emailed you to confirm the address.")
        }
    }

    fun sendConfirmation() = act { say(app.api.sendEmailConfirmation()) }

    /** Back here, often from confirming the address in the browser. */
    fun returned() {
        if (state.value is Load.Ready) viewModelScope.launch { reload() }
    }

    /** Null until they load, or if they don't. */
    val blocked = MutableStateFlow<List<BlockedPerson>?>(null)

    suspend fun loadBlocked() {
        blocked.value = runCatching { app.api.blockedPeople() }.getOrNull()
    }

    fun unblock(person: BlockedPerson) = act {
        app.api.setBlocked(person.id, false)
        blocked.value = blocked.value?.filter { it.id != person.id }
        app.changes.emit(com.krbavcic.logosphere.data.Change.Profile)
    }

    /** Null until they load, or if they don't. */
    val invites = MutableStateFlow<List<Invite>?>(null)

    /** A link just made, shown until it's closed. */
    val madeInvite = MutableStateFlow<NewInvite?>(null)

    suspend fun loadInvites() {
        invites.value = runCatching { app.api.invites() }.getOrNull()
    }

    fun makeInvite() = act(onSuccess = { loadInvites() }) { madeInvite.value = app.api.makeInvite(null) }

    fun revokeInvite(id: String) = act(onSuccess = { loadInvites() }) { app.api.revokeInvite(id) }

    fun changePassword(current: String, new: String, onDone: () -> Unit) = act {
        say(app.api.changePassword(current, new))
        onDone()
    }

    fun export(uri: Uri) = act {
        app.saveText(uri, app.api.exportData())
        say("Your data was saved.")
    }

    fun deleteAccount(password: String) = act {
        app.api.deleteAccount(password)
        app.session.accountDeleted()
    }
}

/** Your password, your data and your account (the web's Settings). */
@Composable
fun AccountScreen() {
    val app = LocalAppContainer.current
    val vm: AccountViewModel = viewModel { AccountViewModel(app) }
    val navigator = LocalNavigator.current
    val busy by vm.busy.collectAsStateWithLifecycle()
    val email by vm.state.collectAsStateWithLifecycle()
    val blocked by vm.blocked.collectAsStateWithLifecycle()
    LaunchedEffect(vm) { vm.loadBlocked() }
    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) { vm.returned() }
    val invites by vm.invites.collectAsStateWithLifecycle()
    val madeInvite by vm.madeInvite.collectAsStateWithLifecycle()
    LaunchedEffect(vm) { vm.loadInvites() }
    var revoking by rememberSaveable { mutableStateOf<String?>(null) }
    val snackbar = remember { SnackbarHostState() }
    SnackbarMessages(vm.messages, snackbar)

    // Passwords stay in memory only: never in the saved state Android keeps for a screen.
    var current by remember { mutableStateOf("") }
    var new by remember { mutableStateOf("") }
    var again by remember { mutableStateOf("") }
    var deletePassword by remember { mutableStateOf("") }
    var confirmDelete by rememberSaveable { mutableStateOf(false) }
    val saveTo = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/json")) { uri ->
        uri?.let(vm::export)
    }
    val mismatch = again.isNotEmpty() && again != new
    val tooShort = new.isNotEmpty() && new.length < MIN_PASSWORD

    Scaffold(
        topBar = { BackTopBar("Password, email, data & account", navigator::back) },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        Column(
            Modifier
                .padding(padding)
                .imePadding()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = ScreenPadding, vertical = 8.dp)
                .readable(),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            EmailCard(email, busy, onToggle = vm::toggleTopic, onConfirm = vm::sendConfirmation, onRetry = vm::load)
            BrandCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    SectionHeading("Invitations")
                    MetaText(
                        "A link to share yourself. Each works for two weeks, or until you revoke it. To invite into a " +
                            "group, use Invite someone on its page.",
                        maxLines = 4,
                    )
                    OutlinedButton(onClick = vm::makeInvite, enabled = !busy, modifier = Modifier.fillMaxWidth()) {
                        Text("Make a link to LogoSphere")
                    }
                    val out = invites
                    if (out == null) MetaText("The list hasn't loaded.")
                    out?.forEach { invite ->
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) {
                                Text(invite.group?.name ?: "LogoSphere")
                                MetaText(
                                    "${invite.joined} joined · " +
                                        if (invite.works) "until ${Dates.day(invite.expiresAt)}" else "doesn't work any more",
                                    maxLines = 2,
                                )
                            }
                            LinkText("Revoke", { revoking = invite.id }, enabled = !busy)
                        }
                    }
                }
            }
            BrandCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    SectionHeading("Change your password")
                    PasswordField(current, { current = it }, "Current password")
                    PasswordField(new, { new = it }, "New password", if (tooShort) "At least $MIN_PASSWORD characters." else null)
                    PasswordField(again, { again = it }, "New password again", if (mismatch) "The two don't match." else null)
                    Button(
                        onClick = { vm.changePassword(current, new) { current = ""; new = ""; again = "" } },
                        enabled = !busy && current.isNotEmpty() && new.length >= MIN_PASSWORD && new == again,
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text("Change password") }
                    MetaText("Your other phones and browsers are signed out; this one stays signed in.", maxLines = 2)
                }
            }
            BrandCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    SectionHeading("People you blocked")
                    val people = blocked
                    when {
                        people == null -> MetaText("The list hasn't loaded.")
                        people.isEmpty() -> MetaText("Nobody.")
                        else -> people.forEach { person ->
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Text(person.name, modifier = Modifier.weight(1f))
                                LinkText("Unblock", { vm.unblock(person) }, enabled = !busy)
                            }
                        }
                    }
                }
            }
            BrandCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    SectionHeading("Your data")
                    Text(
                        "Everything LogoSphere holds about you — profile, value cards, memberships, openings, exchanges, " +
                            "follows, votes, messages, events and notifications — in one file you can keep.",
                        style = MaterialTheme.typography.bodyMedium,
                    )
                    OutlinedButton(
                        onClick = { saveTo.launch("logosphere-data-${LocalDate.now()}.json") },
                        enabled = !busy,
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text("Download your data") }
                }
            }
            BrandCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    SectionHeading("Delete your account")
                    Text(
                        "Your profile, value cards, notifications, follows and memberships are removed, and your open " +
                            "openings are withdrawn. Events you put on for everyone are cancelled, and your invitation " +
                            "links stop. A group's events and announcements stay with the group, without your name. " +
                            "Exchanges you took part in stay as history for the other people in them. This can't be undone.",
                        style = MaterialTheme.typography.bodyMedium,
                    )
                    PasswordField(deletePassword, { deletePassword = it }, "Your password, to confirm")
                    Button(
                        onClick = { confirmDelete = true },
                        enabled = !busy && deletePassword.isNotEmpty(),
                        colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error, contentColor = MaterialTheme.colorScheme.onError),
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text("Delete my account") }
                }
            }
        }
    }

    madeInvite?.let { InviteDialog(it) { vm.madeInvite.value = null } }
    revoking?.let { id ->
        ReallyDialog("Revoke this link?", "It stops working for whoever has it.", "Revoke", { vm.revokeInvite(id) }, { revoking = null })
    }
    if (confirmDelete) {
        AlertDialog(
            onDismissRequest = { confirmDelete = false },
            title = { Text("Delete your account?") },
            text = { Text("This can't be undone. You'll be signed out on every device.") },
            confirmButton = {
                TextButton(onClick = { confirmDelete = false; vm.deleteAccount(deletePassword) }) {
                    Text("Delete", color = MaterialTheme.colorScheme.error)
                }
            },
            dismissButton = { TextButton(onClick = { confirmDelete = false }) { Text("Keep it") } },
        )
    }
}

/** Which notifications also come by email: all off until switched on. */
@Composable
private fun EmailCard(state: Load<EmailSettings>, busy: Boolean, onToggle: (String) -> Unit, onConfirm: () -> Unit, onRetry: () -> Unit) {
    BrandCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            SectionHeading("Email")
            MetaText("Your notifications can come by email too. Nothing does unless you switch it on.", maxLines = 3)
            when (state) {
                Load.Loading -> MetaText("Loading…")
                is Load.Failed -> LinkText("Your email settings didn't load. Try again", onRetry)
                is Load.Ready -> {
                    val mail = state.value
                    when {
                        !mail.on -> MetaText("LogoSphere can't send email yet.")
                        !mail.canReceive -> MetaText("This account's address can't receive email.", maxLines = 2)
                        else -> {
                            MetaText("To ${mail.email}" + if (mail.confirmed) " (confirmed)" else " (not confirmed yet)", maxLines = 2)
                            if (!mail.confirmed) {
                                LinkText("Nothing is sent until you confirm it. Email me the link", onConfirm, enabled = !busy)
                            }
                            mail.choices.forEach { topic ->
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Column(Modifier.weight(1f)) {
                                        Text(topic.label, style = MaterialTheme.typography.titleSmall)
                                        MetaText(topic.about, maxLines = 3)
                                    }
                                    Switch(
                                        checked = topic.key in mail.topics,
                                        onCheckedChange = { onToggle(topic.key) },
                                        enabled = !busy && mail.mayToggle(topic.key),
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun PasswordField(value: String, onChange: (String) -> Unit, label: String, error: String? = null) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        label = { Text(label) },
        singleLine = true,
        isError = error != null,
        supportingText = error?.let { { Text(it) } },
        visualTransformation = PasswordVisualTransformation(),
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
        modifier = Modifier.fillMaxWidth(),
    )
}
