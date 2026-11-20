package com.krbavcic.logosphere.data

import android.content.Context
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/** Light, dark, or whatever the phone is set to. */
enum class ThemeChoice(val label: String) {
    System("Same as the phone"),
    Light("Light"),
    Dark("Dark"),
}

/** The member's choice of theme, kept on this phone (it isn't account data). */
class Appearance(context: Context) {
    private val prefs = context.getSharedPreferences("logosphere", Context.MODE_PRIVATE)
    private val _choice = MutableStateFlow(
        ThemeChoice.entries.firstOrNull { it.name == prefs.getString(KEY, null) } ?: ThemeChoice.System,
    )
    val choice: StateFlow<ThemeChoice> = _choice.asStateFlow()

    fun choose(choice: ThemeChoice) {
        prefs.edit().putString(KEY, choice.name).apply()
        _choice.value = choice
    }

    private companion object {
        const val KEY = "theme"
    }
}
