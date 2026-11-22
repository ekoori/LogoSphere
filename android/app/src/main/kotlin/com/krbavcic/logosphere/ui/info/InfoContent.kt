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

    /** "Last updated …" under a document's title. */
    data class Updated(val text: String) : Block

    /** The few points that matter most, in a card at the top. */
    data class Glance(val items: List<String>, val title: String = "At a glance") : Block

    /** A callout inside a section. */
    data class Note(val text: String) : Block
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
            "None of this is a rewrite. LogoSphere already speaks in profiles, receipts, acknowledgements, spheres and a " +
                "gift-economy board of offers and needs. A meaning lens simply lets each of them carry more of the truth it was " +
                "always reaching for.",
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
        Block.Heading("What you can do here today", "06"),
        Block.Para("The ideas above aren’t a roadmap. They’re working parts, on the web and in this app."),
        Block.Terms(
            listOf(
                "◍ Offers & needs" to "Ask for a hand or offer one. Someone accepts, you confirm, and an exchange begins.",
                "✓ Receipts" to "The person helped says what happened and what it meant — with photos if they like. Both sides can add a note.",
                "✶ Meaning Graph" to "Value cards: what you care about, why, what it looks like, and what drift looks like. Endorse them, review them.",
                "✦ Spheres & groups" to "Your group’s own space. Alliances bring groups together; projects gather shared work.",
                "△ Deciding together" to "Propose a change, vote on it, or lend your vote to someone you trust. Policies that pass apply themselves.",
                "❍ Demo spheres" to "Practice spaces where AI personas play everyday neighbours — clearly labelled — so you can try everything first.",
                "♡ Acknowledgements" to "Thank someone on their trail, and say which values it showed. Whose trail it is chooses what to highlight.",
                "◎ Closeness, explained" to "One map of everyone’s value cards. How close two are is worked out in the open, the same for every viewer, and people can disagree.",
                "⇄ Lend & borrow" to "Share an opening with your other spheres, and lend what can come back.",
                "◷ Gather" to "Events with who’s coming, announcements from a group, and links to invite people in.",
                "◌ Near you" to "Real places, as exact or as rough as you choose. Others never get your point, only a rough distance.",
                "✉ Talk" to "Private messages between two people, with blocking and reporting.",
            ),
        ),
        Block.Heading("What we won’t do", "07"),
        Block.Terms(
            listOf(
                "No ads, no tracking." to "Nothing here is paid for by watching you, and nothing about you is ever sold.",
                "No scores." to "No points, ranks or leaderboards: receipts and reasons, not numbers to chase.",
                "No AI posing as people." to "AI personas live only in the demo spheres, and every one is labelled.",
                "No AI evidence." to "Outside the demo spheres, AI pictures can’t stand as receipts or as what happened.",
                "No lock-in." to "Download everything we hold about you, or delete your account, whenever you like.",
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
        Block.Heading("The words you’ll see in the app"),
        Block.Terms(
            listOf(
                "Offers & Needs" to "The board. Say what you can give, or what you’re looking for.",
                "Sphere" to "Your group’s own space — the neighbourhood, the club, the congregation. Private to it unless you say otherwise.",
                "Exchange" to "The record of one specific act of help, start to finish.",
                "Receipt" to "A real thank-you with substance — what happened and what it meant. Not a star rating.",
                "Meaning Trail" to "Your history — everything you’ve given and received, in order, visible to your group.",
                "Value Card" to "Optional. A short note on what you personally care about, so people find kindred spirits, not just favours.",
                "Alliance & Project" to "An alliance joins groups inside a sphere; a project gathers people around a piece of shared work.",
                "Governance" to "How your group decides: anyone can propose a change, everyone can vote — or lend their vote to someone they trust.",
                "Acknowledgement" to "A few public words of thanks on anyone’s trail, with value cards if you like. The trail’s owner can highlight them.",
                "Meaning Graph" to "Everyone’s value cards as a map. Cards sit closer when they attend to the same things, and each link shows why.",
                "To lend, to borrow" to "An opening for something that comes back. You finish the exchange once it’s home.",
                "Events & announcements" to "What’s on, once or repeating, with who’s coming; and a short word from a group’s managers to its members.",
                "Near you" to "Say where you are, as roughly as you like, and see what’s near as rough distances. Others find you only if you allow it.",
                "Messages" to "Private, between two people. You can block and report.",
                "Invitation" to "A link you share yourself, to LogoSphere or straight into a group. It works for two weeks.",
                "Simple & Advanced" to "How much you’re shown. Simple keeps to giving, asking and thanking; switch whenever you like.",
            ),
        ),
        Block.Heading("Working together, deciding together"),
        Block.Para("Alliances and projects"),
        Block.Bullets(
            listOf(
                "Several groups in a sphere can form an alliance — a tool library run by three congregations, say.",
                "A project gathers people around one piece of work, with its own offers, needs and trail.",
                "A group can post an opening as itself, so the help is the group’s, not one person’s.",
            ),
        ),
        Block.Para("Decisions without the politics"),
        Block.Bullets(
            listOf(
                "Anyone can propose a change — who can join, how decisions pass — or put a question to the group.",
                "Everyone votes, or lends their vote to someone they trust; voting yourself always counts first.",
                "When a policy proposal passes, LogoSphere applies it. No minutes to chase.",
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
                "Is any of this visible outside our group?" to "A sphere is private to the people in it, and nothing you post is searchable by strangers on the open internet. Three exceptions, all chosen: what you post to everyone is seen by every member; an opening you share with your other spheres shows there, without this sphere’s other people; and a sphere whose admin switches on “public activity” shows its projects, alliances and openings to anyone.",
                "Is AI used here?" to "Only where it says so. It can help you word a value card or draw a picture, when you press its button, and it plays the labelled personas in demo spheres. Outside the demo spheres, pictures made with AI aren’t evidence: not receipt photos, not exchange pictures.",
                "Will it email me?" to "Only what your account needs, like a password link, and the notifications you choose to get by email. Those are all off until you turn them on.",
                "What if I just want to watch for now?" to "That’s completely fine. You can see what’s being offered and needed before you ever post anything yourself.",
                "What are the demo spheres, and who are the “AI personas”?" to "Practice spaces where you can try everything before bringing your group. Most of their members are AI characters with famous names playing everyday neighbours — every one is labelled “AI persona”, and nothing in a demo sphere is real.",
                "Is there a phone app?" to "Yes — this Android app does nearly everything the website does (invitation links open on the website). On other phones, the website works in your browser.",
                "Can I leave a group, or delete my account?" to "Any time. Leave a group from its page; download your data or delete your account on the Me tab, under Password, email, data & account.",
                "Isn’t this just one more app to manage?" to "It’s meant to replace the digging-through-the-group-chat step, not add to it — one place where who-needs-what and who’s-already-helping actually lives.",
            ),
        ),
        Block.Heading("Try it with the people you already trust."),
        Block.Para("Start small — one sphere, a handful of neighbours or members. The trail builds itself from there."),
        Block.Link("Read the philosophy →", page = InfoPage.About),
    )

    private val contribute = listOf(
        Block.Eyebrow("Contribute"),
        Block.Title("Help build LogoSphere"),
        Block.Lead(
            "LogoSphere is open source, built by volunteers and shaped by the groups that use it. There’s a place for you " +
                "whether or not you write code.",
        ),
        Block.Heading("Ways to help", "01"),
        Block.Terms(
            listOf(
                "◍ Bring your group" to "Use it for real with the people you already help, and tell us what got in the way. That shapes LogoSphere more than anything else.",
                "✓ Test it" to "Try the website and this app. When something breaks or confuses you, open an issue with what you did and what you saw.",
                "✎ Words and design" to "Clearer wording, kinder empty states, better pages, more accessible screens — all welcome.",
                "{ } Code" to "The backend, the website and the Android app all live in one repository, with tests for each.",
            ),
        ),
        Block.Heading("What it’s built with", "02"),
        Block.Terms(
            listOf(
                "Server" to "Python and Flask, with Cassandra 5 for storage and pictures in object storage.",
                "Website" to "React, built with Vite; one design system, in light and dark.",
                "Android app" to "Kotlin and Jetpack Compose, talking to the same API as the website.",
                "The API" to "Described in LogoSphereAPI.yaml (OpenAPI); a test keeps it in step with the code.",
                "Demo spheres" to "AI personas written with Anthropic’s Claude, their pictures drawn with an OpenAI image model.",
            ),
        ),
        Block.Heading("How we work", "03"),
        Block.Bullets(
            listOf(
                "Small, careful changes, each with tests: pytest for the server, Vitest for the website, JUnit for the app.",
                "Words for people: messages say what happened and what to do next, in plain language.",
                "Private by default: no tracking, no ads, and only what a feature needs.",
                "Every screen in both light and dark, at phone width and with a screen reader.",
            ),
        ),
        Block.Heading("Get started", "04"),
        Block.Para("The code is on GitHub. Its README explains how to run everything on your own computer."),
        Block.Para("Not sure where to begin? Open an issue saying what you’d like to work on, or what you wish LogoSphere did — we’ll help you find a good first step."),
        Block.Link("Visit the repository", url = "https://github.com/ekoori/LogoSphere"),
    )

    private val donate = listOf(
        Block.Eyebrow("Donate"),
        Block.Title("Keep LogoSphere running"),
        Block.Lead("It runs on donations and volunteers’ time, so it can stay free, ad-free and on the side of the groups that use it."),
        Block.Heading("What it costs", "01"),
        Block.Para("LogoSphere has no ads and sells nothing — your data least of all. What it does cost:"),
        Block.Bullets(
            listOf(
                "A server, and storage for everyone’s pictures.",
                "The AI services that write the AI personas in the demo spheres, so anyone can try LogoSphere before bringing their group.",
                "The address, certificates and upkeep that keep it all reachable and safe.",
            ),
        ),
        Block.Para("Donations pay for these, so more groups can use LogoSphere freely."),
        Block.Heading("How to give", "02"),
        Block.Para("Donations go through PayPal: you can pay with a PayPal account or a card. PayPal handles the payment; we receive only what PayPal shares about it."),
        Block.Link(
            "Donate with PayPal",
            url = "https://www.paypal.com/donate?business=donate%40logosphere.net&no_recurring=0&item_name=Support+LogoSphere&currency_code=USD",
        ),
        Block.Heading("Other ways to help", "03"),
        Block.Bullets(
            listOf(
                "Bring your group — LogoSphere is worth the most when it’s used.",
                "Give your time — testing, writing, design or code (see Contribute).",
                "Tell someone who runs a group that could use it.",
            ),
        ),
        Block.Link("Contribute →", page = InfoPage.Contribute),
        Block.Heading("Thank you", "04"),
        Block.Para("Every gift — money, time or a word to a friend — keeps a little more help from getting lost in a chat thread. We’re grateful."),
    )

    private val privacy = listOf(
        Block.Eyebrow("Privacy"),
        Block.Title("What we keep, and why"),
        Block.Lead("LogoSphere keeps what it needs to remember the help your group gives and receives — and nothing to sell, track or advertise with."),
        Block.Updated("Last updated 23 November 2026"),
        Block.Glance(
            listOf(
                "No ads, no analytics, no tracking — and we never sell your data.",
                "Your group sees what happens in your group; your email stays private.",
                "Your spot on the map is never shown to other members.",
                "Notification emails are off until you switch them on.",
                "AI personas live only in the labelled demo spheres.",
                "AI help runs only when you press its button, and gets only what you typed there.",
                "Download everything we hold about you, or delete your account, yourself.",
            ),
        ),
        Block.Heading("What we keep", "01"),
        Block.Terms(
            listOf(
                "Your account" to "Your name and email address, and your password — stored only as a one-way hash, so nobody (us included) can read it.",
                "Your profile" to "Whatever you add: a surname, where you are, a photo, and the value cards on your Meaning Graph.",
                "What you do here" to "The openings you post and accept, and the spheres you share them with; the exchanges you take part in, with their receipts, photos, notes, follow-ups and acknowledgements; likes; who you follow; the groups you belong to; and governance proposals, votes and the members you lend your vote to.",
                "Places" to "The words you use for a place and, if you put it on the map, a point no more exact than you chose: a pin is rounded before it leaves your phone. For yourself we also keep whether members nearby may find you. That is off unless you switch it on.",
                "Email" to "Whether you confirmed your address, and which notifications you chose to get by email. When someone starts to join, their name and address for up to a day, until the emailed link is used. To prevent misuse, we count emails and requests for up to a day, without storing the address or the connection they count.",
                "Events, announcements and invitations" to "Events you put on, with their pictures and places, and whether you said you would come to which date. Announcements you write. For an invitation link, a one-way hash of it, who made it and who joined with it, for two weeks. If someone signs up with one, that hash waits with their name and address until they finish.",
                "Messages, blocks and reports" to "Messages you send and get, whom you blocked, and the reports you make with a copy of what you reported.",
                "Your choices on the Meaning Graph and in Settings" to "Which pairs of value cards you judged close or not (others see only totals, from two people up), and whether you use Simple or Advanced.",
                "AI help" to "That you used it, for two days, to keep to daily limits. Not what you typed. For each picture it draws we keep a fingerprint and a tiny thumbnail, so AI pictures can be labelled.",
                "Notifications" to "The messages LogoSphere writes for you when something happens that concerns you.",
                "Keeping you signed in" to "A random session identifier — in a cookie on the web, on your phone in the app — that lasts up to 30 days or until you sign out. If you allow notifications on Android, the app also registers your phone’s push address for as long as you’re signed in on it.",
                "Server records" to "Like any website, the server notes requests (including your IP address) to keep it secure and fix problems. The list of requests is kept for about two weeks, and the server’s own log for some months. To stop password guessing, we count wrong passwords for 15 minutes, without storing the address or the connection they came from.",
            ),
        ),
        Block.Para("We don’t use analytics, advertising or tracking of any kind, and we never sell or rent anything about you."),
        Block.Heading("Who sees what", "02"),
        Block.Bullets(
            listOf(
                "Members see your name, photo, the words you use for where you are, and your value cards.",
                "Your groups see what happens in them: a sphere’s openings, exchanges, receipts and people are for its members. If its managers switch on public activity, anyone, even visitors without an account, can see its projects, alliances and openings, and every signed-in member can see who is in it. A demo sphere shows who is in it to every member.",
                "Every signed-in member can also see a sphere’s name, description, place, value cards and how many are in it, so it can be found; what is posted to everyone, and the exchanges that come of it; and the acknowledgements left on your own trail.",
                "Profile, group and opening pictures can be fetched by anyone who has their exact web address, signed in or not. Receipt, exchange and event pictures are only for those who may see them.",
                "Your email address is never shown to other members.",
                "An opening you share with other spheres shows there with your name, the sphere it comes from and how many liked it. It doesn’t show that sphere’s other people. Its exchanges are seen in its own sphere and by both sides.",
                "Whom you follow isn’t shown to others, though each person is told when you start following them. The activity of people you follow, and whom you both know, show you only what you could open anyway.",
                "An event, with who is coming, is seen by the members of its sphere, or by every signed-in member when it is for everyone.",
                "An announcement is read by the group’s members, and for an alliance or project by the rest of its sphere. Its notification never has the words.",
                "An invitation link shows your name, and the group’s, to whoever holds it. You’re told who joined with it.",
                "A message is for the two people in it. Writing to everyone who responded to an opening sends each their own, so they don’t learn who else responded. AI personas neither read nor send messages, and none go to an AI provider.",
                "A block isn’t told to the person it’s about. A report goes only to the platform’s administrators.",
                "Platform administrators — the few people who run LogoSphere — can see email addresses and what happens in every group, so they can keep the platform working and safe, and use that access only for that. They don’t see your point on the map, and of private messages they see only what was reported. Like all that is stored, both can be reached by whoever runs the server: messages aren’t end-to-end encrypted.",
            ),
        ),
        Block.Para("Exchanges belong to both people in them, so an exchange stays in the other person’s trail as well as yours."),
        Block.Heading("Places and who is near", "03"),
        Block.Bullets(
            listOf(
                "Your point is never shown to another member, however exact you made it.",
                "Distances are worked out between squares a kilometre across and told only in steps (within 2 km, 5 km, 10 km and so on). Someone determined could work out your square from several of them, and only if you chose to be findable. A rougher place blurs that further.",
                "A group, opening or event shows its words and a rough distance. It shows the spot itself only when whoever runs it chose “the exact spot”, and for a private sphere only to those inside it, or whom an opening was shared with. An event for everyone shows it to every signed-in member.",
                "Your phone’s location is read once, when you press “Use where I am now”, and is never followed.",
                "Maps come from OpenStreetMap, only when you open one. It then learns your IP address, that you came from LogoSphere, and the part of the world you’re looking at. “See the spot on a map” opens your phone’s own map app.",
            ),
        ),
        Block.Heading("Demo spheres and AI personas", "04"),
        Block.Para(
            "The demo spheres are clearly labelled practice spaces. Most of their members are AI personas: characters with famous " +
                "names, playing everyday neighbours, whose posts and replies are written by AI models — text by Anthropic’s Claude, " +
                "pictures by OpenAI. They are not the real people, and every one of them is labelled.",
        ),
        Block.Note(
            "To write the personas’ replies, what happens in the demo spheres — including your name and what you post there — is sent to " +
                "Anthropic and OpenAI. The personas act only in the demo spheres, and nothing from the real spheres is sent to " +
                "write them. If you’d rather not, simply don’t join the demo spheres.",
        ),
        Block.Heading("AI help, when you ask for it", "05"),
        Block.Para(
            "AI can help you word a value card, or draw a picture for an offer, need, group or event. It does nothing until you " +
                "press its button, and it saves nothing by itself.",
        ),
        Block.Bullets(
            listOf(
                "Wording a card sends what you typed for that card to Anthropic’s Claude.",
                "Drawing a picture sends the title, the description and your hint to OpenAI.",
                "Neither gets your name, email address, location or anything else about you, unless you type it there yourself.",
                "AI pictures are labelled, and in real spheres they can’t be receipt photos or exchange pictures. We can’t recognise every AI picture made elsewhere. In demo spheres, evidence may be AI-made.",
            ),
        ),
        Block.Heading("Who helps us run it", "06"),
        Block.Para("A few services do part of the work. Each gets only what its job needs:"),
        Block.Terms(
            listOf(
                "Linode (Akamai Cloud)" to "Runs the server and stores pictures, in a private storage bucket in London.",
                "Google Fonts" to "Serves the website’s two typefaces, so your browser contacts Google to load them. (This app carries its fonts inside.)",
                "Anthropic and OpenAI" to "Write the AI personas in the demo spheres, and give AI help when you ask for it (see above).",
                "OpenStreetMap" to "Draws the map, when you open one (see Places above).",
                "Mailgun" to "Delivers email, once it’s switched on: joining, password links, and the notifications you chose. It gets your address and that email. We switch off its tracking of opens and clicks.",
                "Google Firebase" to "Delivers push notifications to Android phones, once they’re switched on, with only a notification’s text and link.",
                "PayPal" to "Handles donations, if you make one. We get only what PayPal shares about a payment.",
            ),
        ),
        Block.Heading("How long we keep it", "07"),
        Block.Para(
            "For as long as you have an account. When you delete it, we remove your profile, credentials, sessions, value cards, " +
                "notifications, follows and memberships, and withdraw your open openings. Exchanges you took part in stay, under " +
                "your name, because they’re part of the other person’s record too. So do the messages you sent, for the person " +
                "who got them, without your name; and reports, as the safety record. A group’s events and announcements stay " +
                "with it, without your name. Your events for everyone are cancelled, keeping only their name and time; your " +
                "replies to events and your invitation links go.",
        ),
        Block.Para("Backup copies of the database may hold your data for a while longer before they’re replaced."),
        Block.Heading("Your choices", "08"),
        Block.Bullets(
            listOf(
                "Change your name, place and photo any time, on the Me tab (or in Settings on the website).",
                "Take a copy of everything we hold about you: Me → Password, email, data & account.",
                "Choose which notifications are emailed (none unless you pick some), in the same place, or stop them from any of those emails.",
                "Leave any group from its page.",
                "Delete your account yourself, in the same place.",
                "Ask us anything, or for anything those don’t cover, at privacy@logosphere.net.",
            ),
        ),
        Block.Para("LogoSphere is meant for adults and for families who use it together; it isn’t designed for children on their own."),
        Block.Heading("Changes to this policy", "09"),
        Block.Para(
            "When how we handle data changes, we’ll update this page and its date. If a change matters to you — something new " +
                "we’d keep, or someone new who’d see it — we’ll say so in LogoSphere before it happens.",
        ),
        Block.Link("Read the terms →", page = InfoPage.Terms),
    )

    private val terms = listOf(
        Block.Eyebrow("Terms of service"),
        Block.Title("The terms, in plain words"),
        Block.Lead("What you can expect from LogoSphere, and what LogoSphere and its members expect of you."),
        Block.Updated("Last updated 23 November 2026"),
        Block.Glance(
            listOf(
                "Help here is a gift: nothing is bought or sold.",
                "What you post stays yours; your group gets to see it.",
                "Be honest, be kind, respect privacy, be yourself.",
                "Outside the demo spheres, evidence mustn’t be AI-made.",
                "You can block and report.",
                "Demo spheres are practice: their AI personas are labelled, and not the real people.",
            ),
        ),
        Block.Heading("What LogoSphere is", "01"),
        Block.Para(
            "LogoSphere is a place for groups — neighbourhoods, clubs, congregations, teams — to ask for help, offer it, keep an " +
                "honest record of what happened, and decide things together. It’s a gift economy: no money changes hands " +
                "through LogoSphere, and nothing here is for sale.",
        ),
        Block.Para("By creating an account or using LogoSphere, you agree to these terms. If you don’t, please don’t use it."),
        Block.Heading("Your account", "02"),
        Block.Bullets(
            listOf(
                "Use your own name and a real email address; one person per account.",
                "Keep your password to yourself. You’re responsible for what’s done with your account.",
                "If you think someone else has used it, change your password (Me → Password, email, data & account) — that signs out every other device — and tell us at support@logosphere.net.",
            ),
        ),
        Block.Heading("What you post", "03"),
        Block.Para(
            "What you write and the photos you add stay yours. By posting them you let LogoSphere store them and show them to the " +
                "people who can see that place — your group’s members, the spheres you share an opening with, every member for " +
                "what you post to everyone, or anyone if a group’s managers have made its activity public — and keep exchanges " +
                "as shared history for both people in them.",
        ),
        Block.Para("Only post what’s yours to share: no one else’s photos, words or private details without their agreement."),
        Block.Heading("AI, pictures and evidence", "04"),
        Block.Para(
            "AI can help you word a value card, or draw a picture for an offer, need, group or event. It can be wrong: what " +
                "you post with it is yours to check.",
        ),
        Block.Para(
            "Receipts are evidence. Outside the demo spheres, don’t use AI-made pictures as receipt photos or exchange pictures. " +
                "LogoSphere refuses those it recognises, and it can’t recognise every one. In demo spheres evidence may be AI-made.",
        ),
        Block.Heading("How we treat each other", "05"),
        Block.Terms(
            listOf(
                "Be honest." to "Offer what you can really give; ask for what you really need; write receipts that say what happened.",
                "Keep it a gift." to "No selling, bartering for money, advertising or fundraising through openings.",
                "Be kind." to "No harassment, threats, hate or discrimination — in posts, messages, receipts, acknowledgements or anywhere else.",
                "Don’t spam." to "Messages, invitations, events and announcements are for people who’d want them.",
                "Respect privacy." to "Don’t share someone’s personal details, or what they told you in confidence.",
                "Be yourself." to "Don’t pretend to be someone else — another member, a famous person, or an AI persona.",
                "Keep it legal and safe." to "Nothing illegal, dangerous or exploitative.",
            ),
        ),
        Block.Para(
            "You can block anyone, and report a person, message, opening, event, announcement or acknowledgement to the " +
                "platform’s administrators. Nobody else is told.",
        ),
        Block.Note(
            "LogoSphere doesn’t check members, run members’ events or guarantee that help will happen. When you meet people or go to their homes, use " +
                "the same care you would anywhere: meet somewhere you’re comfortable, and trust your instincts.",
        ),
        Block.Heading("Groups and the people who run them", "06"),
        Block.Para(
            "Spheres, alliances and projects set their own rules — who may join, how decisions pass — and members can change them " +
                "by proposal and vote. A group’s managers can approve and remove members and edit the group.",
        ),
        Block.Para(
            "Platform administrators may remove content or close accounts that break these terms or put people at risk. So they " +
                "can keep it running, LogoSphere shows them what happens in every group, but not your point on the map, and of " +
                "private messages only what was reported. They act for the good of the community, not to take sides in a group’s own decisions.",
        ),
        Block.Heading("Demo spheres and AI personas", "07"),
        Block.Para(
            "The demo spheres are clearly labelled practice spaces. Most of their members are AI personas: characters with famous " +
                "names, playing everyday neighbours, written by AI. They are not the real people, nothing they say is an " +
                "endorsement, and nothing in a demo sphere is real — no help is actually promised there.",
        ),
        Block.Para("What you post in a demo sphere is processed by AI services to write the personas’ replies — see the privacy policy."),
        Block.Heading("Leaving", "08"),
        Block.Para(
            "You can leave any group from its page, and delete your account yourself, any time. We may close an account that " +
                "seriously or repeatedly breaks these terms; where we can, we’ll tell you why first.",
        ),
        Block.Heading("What we can and can’t promise", "09"),
        Block.Para(
            "LogoSphere is run by a small, volunteer-built project. We work to keep it running and your data safe, but we provide " +
                "it as it is, without guarantees that it will always be available, free of mistakes, or suitable for any " +
                "particular purpose.",
        ),
        Block.Para(
            "As far as the law allows, we aren’t responsible for indirect losses, or for what members do or agree between " +
                "themselves, on LogoSphere or off it. Nothing in these terms takes away rights that the law where you live gives " +
                "you and that can’t be signed away.",
        ),
        Block.Heading("Changes to these terms", "10"),
        Block.Para(
            "If we change these terms, we’ll update this page and its date, and for changes that matter we’ll tell members in " +
                "LogoSphere before they take effect. Using LogoSphere after that means you accept the new terms.",
        ),
        Block.Heading("Questions", "11"),
        Block.Para("Write to support@logosphere.net."),
        Block.Link("Read the privacy policy →", page = InfoPage.Privacy),
    )
}
