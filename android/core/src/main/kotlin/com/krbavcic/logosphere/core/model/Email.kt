package com.krbavcic.logosphere.core.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** `GET /api/mail`: whether LogoSphere can send email, which decides the join and forgot forms. */
@Serializable
data class MailStatus(val on: Boolean = false)

/** `POST /api/register`: with [confirmEmail] there's no account yet, only a link in the inbox. */
@Serializable
data class RegisterResult(
    @SerialName("confirm_email") val confirmEmail: Boolean = false,
    val message: String? = null,
)

@Serializable
data class EmailTopic(val key: String, val label: String = "", val about: String = "")

/** Which notifications also come by email. All off until chosen. */
@Serializable
data class EmailSettings(
    val on: Boolean = false,
    val email: String? = null,
    @SerialName("can_receive") val canReceive: Boolean = false,
    val confirmed: Boolean = false,
    val topics: List<String> = emptyList(),
    val choices: List<EmailTopic> = emptyList(),
    @SerialName("confirmation_sent") val confirmationSent: Boolean = false,
) {
    /** "AI personas too" only widens the other topics. */
    fun mayToggle(key: String): Boolean = key != PERSONAS || key in topics || topics.any { it != PERSONAS }

    fun toggled(key: String): List<String> = if (key in topics) topics - key else topics + key

    private companion object {
        const val PERSONAS = "personas"
    }
}
