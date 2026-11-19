package com.krbavcic.logosphere.core.api

import java.io.IOException

/**
 * The server answered with an error status. [message] is the API's own `{"message": …}` text —
 * written for people, so screens show it as it is.
 */
open class ApiException(val status: Int, message: String) : IOException(message)

/** The session is missing, expired or revoked (`401`). */
class UnauthorizedException(message: String) : ApiException(401, message)

/** A message for any failure, fit to show a person. */
fun Throwable.userMessage(fallback: String = "Something went wrong. Please try again."): String = when (this) {
    is ApiException -> message?.takeIf { it.isNotBlank() } ?: fallback
    is IOException -> "Can't reach LogoSphere. Check your connection and try again."
    else -> fallback
}
