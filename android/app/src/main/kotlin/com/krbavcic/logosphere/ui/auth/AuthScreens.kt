package com.krbavcic.logosphere.ui.auth

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Visibility
import androidx.compose.material.icons.outlined.VisibilityOff
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusDirection
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.krbavcic.logosphere.BuildConfig
import com.krbavcic.logosphere.core.api.LogoSphereApi
import com.krbavcic.logosphere.core.api.userMessage
import com.krbavcic.logosphere.data.SessionManager
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.common.PrimaryAction
import com.krbavcic.logosphere.ui.common.Wordmark
import com.krbavcic.logosphere.ui.common.readable
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlin.coroutines.cancellation.CancellationException

private val EMAIL = Regex("^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$")

class AuthViewModel(private val session: SessionManager, private val api: LogoSphereApi) : ViewModel() {
    private val _mailOn = MutableStateFlow<Boolean?>(null)

    /** Whether LogoSphere can send email, which decides these forms; null until known. */
    val mailOn: StateFlow<Boolean?> = _mailOn.asStateFlow()

    private val _linkSentTo = MutableStateFlow<String?>(null)

    /** Joining by email: where the link went. */
    val linkSentTo: StateFlow<String?> = _linkSentTo.asStateFlow()

    private val _forgot = MutableStateFlow<String?>(null)

    /** The answer to "email me a reset link". */
    val forgot: StateFlow<String?> = _forgot.asStateFlow()

    private val _busy = MutableStateFlow(false)
    val busy: StateFlow<Boolean> = _busy.asStateFlow()

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()

    init {
        viewModelScope.launch {
            _mailOn.value = try {
                api.mailOn()
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                false
            }
        }
    }

    fun emailResetLink(email: String) {
        if (email.isBlank()) {
            _forgot.value = "Type your email address on the sign-in screen first."
            return
        }
        if (_busy.value) return
        _busy.value = true
        viewModelScope.launch {
            try {
                _forgot.value = api.forgotPassword(email)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                _forgot.value = e.userMessage("That didn't send. Please try again.")
            } finally {
                _busy.value = false
            }
        }
    }

    fun closeForgot() {
        _forgot.value = null
    }

    fun joinAgain() {
        _linkSentTo.value = null
    }

    fun signIn(email: String, password: String, server: String?) = submit {
        if (email.isBlank() || password.isEmpty()) return@submit "Enter your email and password."
        session.signIn(email, password, normalised(server) ?: return@submit "That server address doesn't look right.")
        null
    }

    fun register(name: String, email: String, password: String, confirm: String, server: String?) = submit {
        val withPassword = mailOn.value != true
        when {
            name.isBlank() -> return@submit "Please enter your name."
            !EMAIL.matches(email.trim()) -> return@submit "Please enter a valid email address."
            withPassword && password.length < 8 -> return@submit "Password must be at least 8 characters."
            withPassword && password != confirm -> return@submit "Passwords do not match."
        }
        val address = normalised(server) ?: return@submit "That server address doesn't look right."
        if (session.register(name, email, password.takeIf { withPassword }, address)) _linkSentTo.value = email.trim()
        null
    }

    /** null for a bad address; the current server when none was given. */
    private fun normalised(server: String?): String? {
        val text = server?.trim().orEmpty()
        if (text.isEmpty()) return session.server
        return runCatching { LogoSphereApi.serverUrl(text).toString().trimEnd('/') }.getOrNull()
    }

    /** Runs [block]; a returned string is a validation message, a thrown error a failure. */
    private fun submit(block: suspend () -> String?) {
        if (_busy.value) return
        _busy.value = true
        _error.value = null
        viewModelScope.launch {
            try {
                _error.value = block()
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                _error.value = e.userMessage("Couldn't sign in. Please try again.")
            } finally {
                _busy.value = false
            }
        }
    }
}

@Composable
private fun authViewModel(): AuthViewModel {
    val container = LocalAppContainer.current
    return viewModel { AuthViewModel(container.session, container.api) }
}

@Composable
private fun AuthFrame(content: @Composable ColumnScope.() -> Unit) {
    Box(
        Modifier
            .fillMaxSize()
            .safeDrawingPadding()
            .imePadding(),
        contentAlignment = Alignment.TopCenter,
    ) {
        Column(
            Modifier
                .readable()
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp, vertical = 32.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Spacer(Modifier.height(24.dp))
            Wordmark()
            Text(
                "An economy that remembers why.",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.height(12.dp))
            content()
        }
    }
}

@Composable
private fun PasswordField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    imeAction: ImeAction,
    onDone: () -> Unit = {},
) {
    var visible by rememberSaveable { mutableStateOf(false) }
    val focus = LocalFocusManager.current
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        label = { Text(label) },
        singleLine = true,
        visualTransformation = if (visible) VisualTransformation.None else PasswordVisualTransformation(),
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password, imeAction = imeAction),
        keyboardActions = KeyboardActions(onNext = { focus.moveFocus(FocusDirection.Down) }, onDone = { onDone() }),
        trailingIcon = {
            IconButton(onClick = { visible = !visible }) {
                Icon(
                    if (visible) Icons.Outlined.VisibilityOff else Icons.Outlined.Visibility,
                    contentDescription = if (visible) "Hide password" else "Show password",
                )
            }
        },
        modifier = Modifier.fillMaxWidth(),
    )
}

@Composable
private fun ErrorText(error: String?) {
    if (error == null) return
    Surface(color = MaterialTheme.colorScheme.errorContainer, shape = MaterialTheme.shapes.medium) {
        Text(
            error,
            color = MaterialTheme.colorScheme.onErrorContainer,
            style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
        )
    }
}

/** Debug builds only: which LogoSphere server to use (the default is production). */
@Composable
private fun ServerField(value: String, onValueChange: (String) -> Unit) {
    if (!BuildConfig.DEBUG) return
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        label = { Text("Server (debug build)") },
        placeholder = { Text(BuildConfig.DEFAULT_SERVER_URL) },
        singleLine = true,
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri, imeAction = ImeAction.Next),
        modifier = Modifier.fillMaxWidth(),
    )
}

@Composable
fun SignInScreen(notice: String?) {
    val vm = authViewModel()
    val navigator = LocalNavigator.current
    val server = LocalAppContainer.current.session.server
    val busy by vm.busy.collectAsStateWithLifecycle()
    val error by vm.error.collectAsStateWithLifecycle()
    var email by rememberSaveable { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var serverText by rememberSaveable { mutableStateOf(if (server == BuildConfig.DEFAULT_SERVER_URL) "" else server) }
    val focus = LocalFocusManager.current
    val submit = {
        focus.clearFocus()
        vm.signIn(email, password, serverText)
    }

    AuthFrame {
        if (notice != null && error == null) {
            Surface(color = MaterialTheme.colorScheme.secondaryContainer, shape = MaterialTheme.shapes.medium) {
                Text(
                    notice,
                    color = MaterialTheme.colorScheme.onSecondaryContainer,
                    style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(12.dp),
                )
            }
        }
        Text("Sign in", style = MaterialTheme.typography.headlineMedium)
        ErrorText(error)
        OutlinedTextField(
            value = email,
            onValueChange = { email = it },
            label = { Text("Email") },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email, imeAction = ImeAction.Next),
            keyboardActions = KeyboardActions(onNext = { focus.moveFocus(FocusDirection.Down) }),
            modifier = Modifier.fillMaxWidth(),
        )
        PasswordField(password, { password = it }, "Password", ImeAction.Done, onDone = submit)
        ServerField(serverText) { serverText = it }
        PrimaryAction("Sign in", onClick = submit, busy = busy)
        TextButton(onClick = navigator::register, modifier = Modifier.align(Alignment.CenterHorizontally)) {
            Text("New to LogoSphere? Create an account", textAlign = TextAlign.Center)
        }
        var forgot by rememberSaveable { mutableStateOf(false) }
        TextButton(onClick = { forgot = true }, modifier = Modifier.align(Alignment.CenterHorizontally)) {
            Text("Forgot your password?", textAlign = TextAlign.Center)
        }
        if (forgot) {
            val mailOn by vm.mailOn.collectAsStateWithLifecycle()
            val said by vm.forgot.collectAsStateWithLifecycle()
            val close = {
                forgot = false
                vm.closeForgot()
            }
            AlertDialog(
                onDismissRequest = close,
                title = { Text("Forgot your password?") },
                text = {
                    Text(
                        said ?: when (mailOn) {
                            true -> "We'll email a link to ${email.trim().ifEmpty { "the address you type on the sign-in screen" }}. " +
                                "It works once, for 2 hours, and opens in your browser."
                            else -> "LogoSphere can't send email yet. Ask a platform administrator for a password reset link — " +
                                "it works once, for 24 hours. If you don't know one, write to support@logosphere.net."
                        },
                    )
                },
                confirmButton = {
                    if (mailOn == true && said == null) {
                        TextButton(onClick = { vm.emailResetLink(email) }, enabled = !busy) { Text("Email me a link") }
                    } else {
                        TextButton(onClick = close) { Text("OK") }
                    }
                },
                dismissButton = if (mailOn == true && said == null) {
                    { TextButton(onClick = close) { Text("Cancel") } }
                } else {
                    null
                },
            )
        }
    }
}

@Composable
fun RegisterScreen() {
    val vm = authViewModel()
    val navigator = LocalNavigator.current
    val server = LocalAppContainer.current.session.server
    val busy by vm.busy.collectAsStateWithLifecycle()
    val error by vm.error.collectAsStateWithLifecycle()
    var name by rememberSaveable { mutableStateOf("") }
    var email by rememberSaveable { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var confirm by remember { mutableStateOf("") }
    var serverText by rememberSaveable { mutableStateOf(if (server == BuildConfig.DEFAULT_SERVER_URL) "" else server) }
    val focus = LocalFocusManager.current
    val submit = {
        focus.clearFocus()
        vm.register(name, email, password, confirm, serverText)
    }

    val mailOn by vm.mailOn.collectAsStateWithLifecycle()
    val sentTo by vm.linkSentTo.collectAsStateWithLifecycle()

    AuthFrame {
        sentTo?.let { address ->
            Text("Check your email", style = MaterialTheme.typography.headlineMedium)
            Text(
                "We sent a link to $address. Open it to choose your password, then sign in here.",
                style = MaterialTheme.typography.bodyLarge,
            )
            Text(
                "It can take a few minutes: look in spam too. The link works for a day.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            PrimaryAction("Back to sign in", onClick = navigator::back)
            TextButton(onClick = vm::joinAgain, modifier = Modifier.align(Alignment.CenterHorizontally)) {
                Text("Send it again, or use another address")
            }
            return@AuthFrame
        }
        Text("Join LogoSphere", style = MaterialTheme.typography.headlineMedium)
        ErrorText(error)
        OutlinedTextField(
            value = name,
            onValueChange = { name = it },
            label = { Text("Name") },
            singleLine = true,
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Next),
            keyboardActions = KeyboardActions(onNext = { focus.moveFocus(FocusDirection.Down) }),
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = email,
            onValueChange = { email = it },
            label = { Text("Email") },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email, imeAction = ImeAction.Next),
            keyboardActions = KeyboardActions(onNext = { focus.moveFocus(FocusDirection.Down) }),
            modifier = Modifier.fillMaxWidth(),
        )
        if (mailOn == false) {
            PasswordField(password, { password = it }, "Password (at least 8 characters)", ImeAction.Next)
            PasswordField(confirm, { confirm = it }, "Confirm password", ImeAction.Done, onDone = submit)
        }
        ServerField(serverText) { serverText = it }
        if (mailOn == true) {
            Text(
                "You choose your password from the link we email you.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        PrimaryAction(
            if (mailOn == true) "Email me a link to join" else "Create account",
            onClick = submit,
            enabled = mailOn != null,
            busy = busy,
        )
        TextButton(onClick = navigator::back, modifier = Modifier.align(Alignment.CenterHorizontally)) {
            Text("Already have an account? Sign in")
        }
    }
}
