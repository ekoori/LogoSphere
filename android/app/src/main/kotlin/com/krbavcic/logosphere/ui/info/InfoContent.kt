package com.krbavcic.logosphere.ui.info

import com.krbavcic.logosphere.core.logic.InfoPage

/** A piece of an information page; the screen draws each kind its own way. */
sealed interface Block {
    data class Eyebrow(val text: String) : Block
    data class Title(val text: String) : Block
    data class Lead(val text: String) : Block
    data class Heading(val text: String, val number: String? = null) : Block
    data class Para(val text: String) : Block
    data class Bullets(val items: List<String>) : Block
    data class Steps(val items: List<Pair<String, String>>) : Block

    /** Term and gloss pairs (a glossary, a comparison, what a card keeps). */
    data class Terms(val items: List<Pair<String, String>>, val highlightLast: Boolean = false) : Block
    data class Quote(val text: String, val by: String? = null) : Block

    /** A value card's fields, as an example. */
    data class ExampleCard(val fields: List<Pair<String, String>>) : Block
    data class Link(val label: String, val url: String? = null, val page: InfoPage? = null) : Block
}

/**
 * The site's information pages (frontend/src/pages: About, HowItWorks, Contribute, Donate,
 * Privacy, TOS), word for word where they are words; the web's decorative graphics are left out.
 */
object InfoContent {
    fun of(page: InfoPage): List<Block> = when (page) {
        InfoPage.About -> about
        InfoPage.HowItWorks -> howItWorks
        InfoPage.Contribute -> contribute
        InfoPage.Donate -> donate
        InfoPage.Privacy -> privacy
        InfoPage.Terms -> terms
    }

    private val about = listOf(
        Block.Eyebrow("LogoSphere · a meaning-based economy"),
        Block.Title("An economy that remembers why."),
        Block.Lead(
            "Every system that scales human cooperation must compress what people care about into something it can move " +
                "around. Money does it with price. Platforms do it with clicks. Each translation is lossy — and what leaks " +
                "away is the meaning. LogoSphere is an attempt to keep it.",
        ),
        Block.Link("Prefer the plain-language version? See how it works, step by step →", page = InfoPage.HowItWorks),
        Block.Heading("When value collapses", "01"),
        Block.Para(
            "Tell a community its worth is a number, and it will manufacture the number. This is Goodhart’s trap: when a " +
                "measure becomes a target, it stops being a good measure. Likes, daily-active-users, reputation points — thin " +
                "proxies are easy to optimise precisely because they’ve already discarded the reasons underneath them.",
        ),
        Block.Para(
            "A meaning-centric platform inherits a sharper version of the same risk. The moment meaning can be cashed in, " +
                "people optimise for appearing meaningful. The proxy doesn’t just mislead — it crowds out the thing it was " +
                "meant to stand for.",
        ),
        Block.Terms(
            listOf(
                "Thin proxy" to "♥ 2,431 · DAU 18.2k · ★ 4.9 · pts 1,290 — easy to move, easy to fake, blind to why.",
                "Thick value" to "Tools stay alive in the neighbourhood — repaired and shared, not landfilled — because the labour " +
                    "already inside a thing shouldn’t be thrown away. Hard to fake. Carries its own reasons.",
            ),
        ),
        Block.Heading("Thick Models of Value", "02"),
        Block.Para(
            "A Thick Model of Value is a representation rich enough to survive being optimised. Where a preference records " +
                "what you chose, and a written rule records what’s allowed, a TMV carries the why — and the texture around it.",
        ),
        Block.Terms(
            listOf(
                "Reasons" to "The “because” behind a choice — not only the choice itself.",
                "Endorsement" to "What you’d still choose after reflection, told apart from impulse.",
                "Context & roles" to "The promises, boundaries, and obligations a situation carries.",
                "Trade-offs" to "Priorities, thresholds, and the lines you will not cross.",
                "Collective goods" to "Trust, legitimacy, the commons no single person holds.",
                "Endorsed change" to "Growth you would affirm — distinguished from drift and capture.",
            ),
        ),
        Block.Para("A ladder of fidelity — each rung keeps more of what mattered:"),
        Block.Steps(
            listOf(
                "Preferences" to "what — utilities, rankings",
                "Values-as-text" to "policies you can lawyer around",
                "Thick value" to "reasons, endorsement, context",
            ),
        ),
        Block.Heading("The Value Card", "03"),
        Block.Para(
            "To be usable by humans, a thick value compresses into a card — a small, honest artefact you could read in ten " +
                "seconds and recognise as your own.",
        ),
        Block.ExampleCard(
            listOf(
                "I care about" to "Tools staying alive in the neighbourhood — repaired, shared, not landfilled.",
                "Because" to "Throwing away a fixable thing wastes the care and labour already inside it.",
                "Looks like" to "Running the Saturday repair café · teaching the fix, not just doing it · lending freely.",
                "Drift looks like" to "Hoarding the best tools · counting repairs for status · skipping the teaching to save time.",
                "In conflict, I prioritise" to "Teaching someone over finishing faster.",
                "Never" to "Charging for access to shared tools.",
            ),
        ),
        Block.Para("CLEAR values:"),
        Block.Terms(
            listOf(
                "C · Concrete" to "behaviours you can actually see",
                "L · Levers & limits" to "trade-offs and boundaries",
                "E · Endorsement" to "chosen on reflection, not impulse",
                "A · Anti-signals" to "what drift looks like",
                "R · Review" to "revisited on a cadence",
            ),
        ),
        Block.Heading("Three kinds of meaning", "04"),
        Block.Para(
            "Meaning isn’t pleasure, and it isn’t status. Following Viktor Frankl, it arrives by three routes — and a healthy " +
                "ledger can tell them apart.",
        ),
        Block.Terms(
            listOf(
                "✶ Creative — what you make and give" to "“I rebuilt the tool library’s catalogue so anyone can find what to borrow.”",
                "❍ Experiential — what you receive and encounter" to "“Sitting with a neighbour as she learned to sharpen her grandfather’s plane.”",
                "△ Attitudinal — the stance you take under constraint" to "“We kept the repair café free, even when keeping it open got hard.”",
            ),
        ),
        Block.Heading("Woven into the platform", "05"),
        Block.Para(
            "None of this is a rewrite. LogoSphere already speaks in profiles, Receipts, acknowledgements, spheres, and a " +
                "gift-economy openings. A meaning lens simply lets each primitive carry more of the truth it was always reaching for.",
        ),
        Block.Terms(
            listOf(
                "Meaning Graph" to "A profile holds a handful of Value Cards instead of a tag cloud — what you care about, and why.",
                "Receipt → Meaning Receipt" to "A record of exchange that names the value it expressed, what it cost, and the receiver’s endorsement.",
                "Acknowledgement → Light signal" to "Public thanks stays lightweight — warmth, not currency. The weight-bearing work belongs to receipts.",
                "Sphere & Project → Norm bundle + drift clause" to "A community declares its shared values — and a “we’re drifting if…” clause to catch its own slide.",
                "Openings → Meaning-tagged exchange" to "Offers and needs carry the values they serve; matching favours overlaps that are endorsed and evidenced.",
            ),
        ),
        Block.Quote("If meaning becomes a currency, it will be optimised."),
        Block.Para(
            "So the whole design turns on one distinction. Endorsed meaning is what holds up under reflection and " +
                "deliberation. Performed meaning is status play wearing meaning’s clothes. Every mechanism here — receipts over " +
                "points, reasons over scores, drift clauses over leaderboards — exists to keep the first from collapsing into the second.",
        ),
        Block.Heading("Build it with us"),
        Block.Para(
            "Help shape an economy worth measuring. If you’d rather your contributions be remembered for what they meant than " +
                "counted for what they scored, you belong here.",
        ),
        Block.Link("Contribute →", page = InfoPage.Contribute),
    )

    private val howItWorks = listOf(
        Block.Eyebrow("LogoSphere · in plain terms"),
        Block.Title("Favors, remembered — not lost in a chat thread."),
        Block.Lead(
            "Every week your group asks for help, offers help, and says thanks — and then it vanishes into a scroll of messages " +
                "nobody will find again. LogoSphere gives that a home: a simple way to ask, to offer, to say a real thank-you, and " +
                "to keep a record of it that your whole group can see growing.",
        ),
        Block.Link("Want the bigger idea behind it? →", page = InfoPage.About),
        Block.Heading("It isn’t the people. It’s the memory."),
        Block.Para(
            "Most communities are already generous — help happens all the time. What’s missing isn’t willingness, it’s a place " +
                "for it to live afterward. Here’s where it usually goes to die:",
        ),
        Block.Terms(
            listOf(
                "💬 The group chat" to "Someone asks for a hand. Three people reply. By tomorrow it’s buried under forty other messages.",
                "📋 The spreadsheet" to "Somebody’s job to update it. They get busy. Six months later nobody trusts the numbers in it.",
                "🤝 A word of thanks" to "Real, and it matters in the moment — but by dinner, there’s no trace it happened at all.",
            ),
        ),
        Block.Para("One shared trail your whole group can actually see, that builds itself as help happens."),
        Block.Heading("Five steps, start to finish"),
        Block.Steps(
            listOf(
                "Post it" to "Need a hand, or got one to give? Say so in a sentence — an Offer or a Need. It shows up on your group’s board, not the whole internet.",
                "Someone says yes" to "A member of your group accepts. You work out the when and where together, same as you always would.",
                "You do the thing" to "Fix the fence, watch the kids, lend the drill, drive someone to an appointment — whatever it actually is, in real life, off the app.",
                "Say thanks, both ways" to "The person who was helped writes a Receipt — a real thank-you, not a star rating: what happened, what it meant, maybe a photo. The helper can leave a short note back.",
                "It joins the trail" to "That receipt becomes part of both people’s Meaning Trail — a running, visible record of what they’ve given and received in your group.",
            ),
        ),
        Block.Heading("A real example: Maria’s fence"),
        Block.Para(
            "Maria’s back fence has a hole a dog could get through. Tom, three doors down, is a retired carpenter who’s handy " +
                "with exactly this. Here’s what that looks like, start to finish.",
        ),
        Block.Steps(
            listOf(
                "Maria posts a Need" to "Fence repair, west side — “One panel’s broken through — dog-sized hole. Any help this week appreciated!”",
                "Tom accepts" to "“Got a spare panel in the garage actually. Saturday morning work?”",
                "Maria’s Receipt" to "“Fixed it in under two hours — and showed me how to do the next repair myself. That’s the kind of neighbour I hope to be too.”",
            ),
        ),
        Block.Para(
            "That’s it. Two neighbours, one fence, one honest thank-you — and now it’s a permanent part of both of their trails, " +
                "visible to everyone in Oakview Neighbours.",
        ),
        Block.Heading("Six words you’ll see in the app"),
        Block.Terms(
            listOf(
                "Offers & Needs" to "The board. Say what you can give, or what you’re looking for.",
                "Sphere" to "Your group’s own space — the neighbourhood, the club, the congregation. Private to it unless you say otherwise.",
                "Exchange" to "The record of one specific act of help, start to finish.",
                "Receipt" to "A real thank-you with substance — what happened and what it meant. Not a star rating.",
                "Meaning Trail" to "Your history — everything you’ve given and received, in order, visible to your group.",
                "Value Card" to "Optional. A short note on what you personally care about, so people find kindred spirits, not just favours.",
            ),
        ),
        Block.Heading("What you actually get out of it"),
        Block.Para("If you’re a member"),
        Block.Bullets(
            listOf(
                "Get recognised for what you actually did — not just a “like.”",
                "Build a track record people in your group can see and trust.",
                "No awkward conversation about money — it was never on the table.",
                "Find people who care about the same things you do, not just favours.",
            ),
        ),
        Block.Para("If you help run the group"),
        Block.Bullets(
            listOf(
                "Replace the WhatsApp archaeology with a place things actually live.",
                "New members can see what your group does just by scrolling.",
                "Ready-made evidence when you need to show real impact — a grant form, an annual report, a volunteer thank-you night.",
                "Nobody has to be the one maintaining a spreadsheet by hand.",
            ),
        ),
        Block.Heading("How this is different"),
        Block.Terms(
            listOf(
                "Group chat" to "Fast to post. Gone by tomorrow. No record of what actually happened.",
                "Nextdoor / Marketplace" to "Built for selling things and airing complaints — not for organised giving.",
                "A spreadsheet" to "Someone has to maintain it by hand. Just numbers — no story behind them.",
                "LogoSphere" to "Builds itself as help actually happens. The story stays attached to the record.",
            ),
            highlightLast = true,
        ),
        Block.Heading("What people ask first"),
        Block.Terms(
            listOf(
                "Does money change hands?" to "No. LogoSphere is for help freely given — a fence fixed, a ride offered, an afternoon of childcare. If people sometimes call this a “gift economy,” that’s the plain meaning of the term: helping, no money involved.",
                "Do I have to write a receipt every single time?" to "No — but it’s the whole mechanism. It’s how the person who helped actually gets seen, and how your group’s trail grows into something worth looking at.",
                "Is any of this visible outside our group?" to "Not unless your group chooses it. A Sphere is private to the people in it, and nothing you post is searchable by strangers on the open internet — unless the sphere’s admin explicitly switches on “public activity”, in which case its projects, alliances and openings become viewable by anyone.",
                "What if I just want to watch for now?" to "That’s completely fine. You can see what’s being offered and needed before you ever post anything yourself.",
                "Isn’t this just one more app to manage?" to "It’s meant to replace the digging-through-the-group-chat step, not add to it — one place where who-needs-what and who’s-already-helping actually lives.",
            ),
        ),
        Block.Heading("Try it with the people you already trust."),
        Block.Para("Start small — one sphere, a handful of neighbours or members. The trail builds itself from there."),
        Block.Link("Read the philosophy →", page = InfoPage.About),
    )

    private val contribute = listOf(
        Block.Title("Contribute to LogoSphere"),
        Block.Lead(
            "LogoSphere is an open-source project aimed at building a social network and gift economy platform. We welcome " +
                "contributions from developers, designers, and anyone interested in making a positive impact. Join us in creating " +
                "a community-driven platform that fosters trust, collaboration, and mutual support.",
        ),
        Block.Heading("Technologies We Use"),
        Block.Terms(listOf("Frontend" to "React", "Backend" to "Flask (Python)", "Database" to "Cassandra", "Version Control" to "Git")),
        Block.Heading("Current Development Phase"),
        Block.Para(
            "We are currently in the phase of fine-tuning the mockup and translating it into precise requirements for the " +
                "frontend, data model, database configuration, and backend functionality. Our goal is to close the development " +
                "loop one class at a time and define unit tests to ensure the robustness of our platform.",
        ),
        Block.Heading("Get Involved"),
        Block.Para(
            "Our project is hosted on GitHub. You can find the repository, contribute to the code, report issues, and join discussions:",
        ),
        Block.Link("Visit our GitHub Repository", url = "https://github.com/ekoori/LogoSphere"),
        Block.Heading("Join Our Community"),
        Block.Para(
            "Interested in contributing? Join our community of developers and collaborators. Whether you're a seasoned " +
                "developer or just getting started, your contributions are valuable to us.",
        ),
    )

    private val donate = listOf(
        Block.Title("Support LogoSphere"),
        Block.Lead(
            "LogoSphere relies on the generous support of its members to continue building a community-driven platform. Your " +
                "donations help us improve the platform, add new features, and maintain our services. Any contribution, big or " +
                "small, is greatly appreciated.",
        ),
        Block.Heading("How to Donate"),
        Block.Para("You can make a donation using PayPal. The button below opens PayPal in your browser."),
        Block.Link(
            "Donate with PayPal",
            url = "https://www.paypal.com/donate?business=donate%40logosphere.net&no_recurring=0&item_name=Support+LogoSphere&currency_code=USD",
        ),
        Block.Heading("Thank You!"),
        Block.Para(
            "We deeply appreciate your support. Your donation helps us continue our mission to foster trust, collaboration, " +
                "and mutual support within our community.",
        ),
    )

    private val privacy = listOf(
        Block.Title("Privacy Policy"),
        Block.Lead(
            "Your privacy is important to us. This privacy policy explains what personal data LogoSphere collects from you, " +
                "how we use that data, and your rights regarding your personal information.",
        ),
        Block.Heading("Data Collection"),
        Block.Para("We collect the following types of data:"),
        Block.Terms(
            listOf(
                "Personal Information" to "Name, email address, and other contact details provided during registration.",
                "Usage Data" to "Information about how you use our platform, including the pages you visit, the features you use, and the actions you take.",
                "Device Data" to "Information about the device you use to access our platform, including your IP address, browser type, and operating system.",
            ),
        ),
        Block.Heading("Data Usage"),
        Block.Para("We use your data for the following purposes:"),
        Block.Bullets(
            listOf(
                "To provide and maintain our services",
                "To improve and personalize your experience",
                "To communicate with you, including sending updates and notifications",
                "To analyze usage patterns and improve our platform",
                "To comply with legal obligations",
            ),
        ),
        Block.Heading("Data Sharing"),
        Block.Para("We do not sell or rent your personal information to third parties. We may share your data with:"),
        Block.Bullets(
            listOf(
                "Service providers who assist us in operating our platform",
                "Legal authorities if required by law or to protect our rights",
            ),
        ),
        Block.Heading("Your Rights"),
        Block.Para("You have the following rights regarding your personal data:"),
        Block.Bullets(
            listOf(
                "The right to access and update your information",
                "The right to request the deletion of your data",
                "The right to object to or restrict the processing of your data",
                "The right to data portability",
                "The right to withdraw consent at any time",
            ),
        ),
        Block.Para("If you have any questions or concerns about your privacy, please contact us at privacy@logosphere.net."),
    )

    private val terms = listOf(
        Block.Title("Terms of Service"),
        Block.Lead(
            "Welcome to LogoSphere. By using our platform, you agree to comply with and be bound by the following terms and " +
                "conditions of service. Please review the following terms carefully.",
        ),
        Block.Heading("Acceptance of Terms"),
        Block.Para(
            "By accessing and using LogoSphere, you accept and agree to be bound by the terms and provision of this agreement. " +
                "In addition, when using LogoSphere's services, you shall be subject to any posted guidelines or rules applicable " +
                "to such services. Any participation in this service will constitute acceptance of this agreement. If you do not " +
                "agree to abide by the above, please do not use this service.",
        ),
        Block.Heading("Changes to Terms"),
        Block.Para(
            "LogoSphere reserves the right to update or modify these terms at any time without prior notice. Your continued use " +
                "of the service following any such change constitutes your agreement to follow and be bound by the terms as " +
                "changed. For this reason, we encourage you to review these terms whenever you use the service.",
        ),
        Block.Heading("User Responsibilities"),
        Block.Para(
            "As a user of LogoSphere, you agree to use the platform responsibly and ethically. You are responsible for " +
                "maintaining the confidentiality of your account information and for all activities that occur under your account. " +
                "You agree to notify LogoSphere immediately of any unauthorized use of your account or any other breach of security.",
        ),
        Block.Heading("Content Ownership"),
        Block.Para(
            "All content provided on LogoSphere is the intellectual property of LogoSphere or the content creators. You may not " +
                "modify, publish, transmit, participate in the transfer or sale of, reproduce, create derivative works from, " +
                "distribute, perform, display, or in any way exploit any of the content in whole or in part.",
        ),
        Block.Heading("Limitation of Liability"),
        Block.Para(
            "LogoSphere is not liable for any direct, indirect, incidental, consequential, or punitive damages arising out of or " +
                "related to your use of the service. This includes, but is not limited to, damages for errors, omissions, " +
                "interruptions, defects, delays in operation or transmission, computer virus, or loss of data.",
        ),
        Block.Heading("Contact Information"),
        Block.Para("If you have any questions about these Terms of Service, please contact us at support@logosphere.net."),
    )
}
