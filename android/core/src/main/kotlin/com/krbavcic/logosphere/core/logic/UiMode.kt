package com.krbavcic.logosphere.core.logic

/**
 * How much of LogoSphere someone is shown (the site's utils/modes.js). Presentation only: Simple
 * never takes away what someone may do, and whatever is owed (approvals, confirmations, a link
 * to a vote) still shows.
 */
enum class UiMode(val key: String, val label: String, val about: String) {
    Simple("simple", "Simple", "Offers, needs, thanks and what people care about, with fewer options."),
    Advanced("advanced", "Advanced", "Everything: voting, group settings, kinds of meaning and fine-tuning.");

    companion object {
        /** An account's mode; one from before there was a choice (nothing said) counts as Advanced. */
        fun of(key: String?): UiMode = entries.firstOrNull { it.key == key } ?: Advanced
    }
}

/** The tabs a screen offers in each mode. */
object ShownTabs {
    /** Simple leaves out [advancedOnly], except the one that's open (a link can open any). */
    fun of(tabs: List<String>, advancedOnly: Set<String>, simple: Boolean, open: String?): List<String> =
        tabs.filter { !simple || it !in advancedOnly || it == open }
}
