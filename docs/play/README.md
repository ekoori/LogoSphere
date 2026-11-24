# Google Play listing

Everything the Play Console asks for, ready to paste. Graphics are in this folder. Written
2026-11-25 for the first Play build, 0.4.0 (version code 400), after Per Ankh's and BushLines'
listings.

## Before the first upload

1. **The upload key.** It never enters the repository. Make it once, on the computer that builds
   releases (keytool asks for one password, used for the store and the key):

   ```
   & "C:\Program Files\Android\Android Studio\jbr\bin\keytool.exe" -genkeypair -keystore "$env:USERPROFILE\.android\logosphere-upload.jks" -storetype PKCS12 -alias logosphere -keyalg RSA -keysize 4096 -validity 10000 -dname "CN=LogoSphere"
   ```

   Then add two lines to `~/.gradle/gradle.properties` (or set `LOGOSPHERE_KEYSTORE` and
   `LOGOSPHERE_KEYSTORE_PASSWORD`):

   ```
   logosphereKeystore=C:/Users/igor/.android/logosphere-upload.jks
   logosphereKeystorePassword=<the password>
   ```

   Keep a copy of the keystore and both lines somewhere safe. Without them a release build is
   signed with the debug key, which Play rejects, and Gradle says so. Google keeps the app signing
   key (Play App Signing), so a lost or leaked upload key can be replaced through Play Console
   (*App integrity* → *Request upload key reset*).
2. **The bundle.** `cd android && ./gradlew :app:bundleRelease` writes
   `app/build/outputs/bundle/release/app-release.aab`. Check it is signed with the upload key:
   `./gradlew :app:signingReport` must show `Alias: logosphere` for the release variant, not
   `AndroidDebugKey`.

## First upload, step by step

Publish from the same organisation account as Per Ankh (LOVI Tech): an organisation account does
not need the 12 testers for 14 days that new personal accounts need before production.

1. **Create the app.** Home → *Create app*: the name below, default language English, *App*,
   *Free*. The package is `earth.logosphere.app`; creating the app registers it to the account for
   Android developer verification.
2. **Signing.** Accept Play App Signing with a Google-generated app signing key. The first upload
   makes the bundle's key (the upload key above) the upload key.
3. **Store listing.** *Grow users* → *Store presence* → *Main store listing* and *Store settings*:
   texts from "App details", graphics from "Graphics".
4. **App content.** *Policy and programs* → *App content*: privacy policy, app access, ads, content
   rating, target audience, data safety, data deletion, advertising ID (not used), and the
   government, financial, health and news declarations, all from the sections below.
5. **Internal testing.** *Test and release* → *Testing* → *Internal testing*: a testers list with
   your own Google account, *Create new release*, upload the bundle, release name `0.4.0`. Roll it
   out and install it from the opt-in link.
6. **Closed or open testing, then production.** Send the changes for review; the first review of a
   new app can take several days.

Console menu names move between Play Console versions; the help pages name the current ones.

## App details

| Field | Value |
|---|---|
| App name (≤30) | LogoSphere: Help Each Other |
| Package | `earth.logosphere.app` |
| Default language | English (Australia) or English (United States) |
| App or game | App |
| Free or paid | Free |
| Category | Social |
| Tags | Community, Social, Lifestyle |
| Contact email | support@logosphere.earth (shown publicly; forwarded to Igor once the MX records are in) |
| Website | https://logosphere.earth |
| Privacy policy | https://logosphere.earth/privacy |

**Short description (≤80):**
Offer help, ask for it, and remember what your group gives each other.

**Full description (≤4000):**

> LogoSphere is where a group keeps track of the help its members give each other, and why it
> matters.
>
> • Openings: offer what you can do or lend, ask for what you need, and see what your spheres are
> offering right now.
> • Exchanges that remember: when help happens, both of you confirm it, add a receipt or a photo,
> and thank each other on your Meaning Trails.
> • Value cards and the Meaning Graph: say what you care about and why, and see how the people
> around you connect through what they value. Closeness is explained, never a score.
> • Spheres, alliances and projects: groups with their own members, rules and roles,
> announcements and events.
> • Messages, events and places: talk one to one, plan get-togethers, and find what is near you,
> only if you choose to share a place.
> • Simple mode, for anyone who wants fewer buttons.
> • Try everything first in the demo spheres, played by AI personas who are labelled as such.
> • Optional AI help to word a value card or draw a picture, only when you press its button.
>
> No ads, nothing sold, no tracking. Download everything we hold about you, or delete your
> account, from the app. A flag on every screen reaches the people who run LogoSphere.
>
> LogoSphere is open source: https://github.com/ekoori/LogoSphere

## Data safety form

Answers for 0.4.0. Update them before the version that turns on push notifications (a Firebase
token per phone).

- Does your app collect or share any of the required user data types? **Yes**.
- Is all user data collected by your app encrypted in transit? **Yes** (HTTPS only).
- Do you provide a way for users to request that their data be deleted? **Yes**: in the app
  (Me → Password, email, data & account → Delete my account) and on the website.
- Data deletion URL: https://logosphere.earth/privacy#your-choices
- Shared with third parties: **none**. Mailgun (email), Linode (hosting), Anthropic and OpenAI (AI
  help, only when asked) work for LogoSphere as service providers, which Play does not count as
  sharing.
- Data types collected, none sold, none used for advertising:

| Type | Required? | Purposes |
|---|---|---|
| Personal info → Name | Required | Account management, App functionality |
| Personal info → Email address | Required | Account management, App functionality |
| Personal info → User IDs | Required | Account management |
| Location → Approximate location | Optional (a place you set) | App functionality |
| Location → Precise location | Optional (only "Use where I am now", read once) | App functionality |
| Messages → Other in-app messages | Optional | App functionality |
| Photos and videos → Photos | Optional (profile, openings, receipts) | App functionality |
| App activity → Other user-generated content (openings, cards, acknowledgements) | Optional | App functionality |
| App info and performance → Diagnostics (the problem flag: screen, app and Android version) | Optional | Analytics |

- Not collected: financial info, health, contacts, calendar, files, audio, web browsing, installed
  apps, device or other IDs (until push is on), advertising ID.

## Content rating (IARC questionnaire)

Category: social networking / user-generated content. Violence, sexuality, language, controlled
substances, gambling: **No** to all. Users can interact and exchange content: **Yes**. Shares the
user's location with other users: **Yes** (a place a member chooses to set, for "near you").
Digital purchases: **No**. Expected: a general rating with the "Users Interact" and "Shares
Location" notices.

## Target audience and content

- Target age groups: **18 and over** (messaging between members, groups, and AI personas), which
  keeps the app outside the Designed for Families programme.
- Appeals to children: **No**. Ads: **No**. In-app purchases: **No**. Donations: none in the app
  (see "Policy notes").
- News app: No. Government app: No. Financial features: None. Health: No.

## App access

Everything needs an account. Give the reviewer one made for them: create it on the website (Join,
then the link it emails) as "Play Reviewer" with an address you can read, join the demo spheres
from the Openings tab, and put its email and password in *App access* with these notes:

> Sign in with the account above. The Openings tab shows the demo spheres, played by labelled AI
> personas. A flag at the top of every screen sends a problem report. AI help is under a value
> card's "Help me word it" and an opening's "Draw one with AI"; each result has a Report link.

## Graphics

| Asset | Requirement | File |
|---|---|---|
| App icon | 512×512 PNG, 32-bit | `icon-512.png` |
| Feature graphic | 1024×500 PNG (no alpha) or JPG | `feature-graphic.png` |
| Phone screenshots | 2–8, PNG or JPG, 320–3840 px, the long side at most twice the short | `screenshots/*.png` (1080×2031, six) |

The icon and feature graphic are drawn from the launcher icon's own geometry and the app's fonts
(Fraunces, Hanken Grotesk) in the site's colours. The screenshots (2026-11-25, signed in as the
persona Jo Rodan, so only demo content shows) come from the test phone, a Galaxy Note 9
(1080×2220), with its status and navigation bars cut off and nothing scaled: the Openings feed, a
need, the demo spheres, Riverside Commons, the Meaning Graph and the problem flag. They are not
9:16, which Play wants only for its recommendation slots; padding them to 9:16 smeared the
full-width pictures, so a 9:16 set needs a 16:9-screen phone or emulator. The Trail and Me screens
were left out because they show personas' likeness pictures. The README's `docs/demo.gif` is the
same six at 320 px, two seconds each.

## Policy notes

- Target API: 36, as Play requires for new apps since 31 August 2026. Native code (two AndroidX
  libraries) is aligned for 16 KB pages.
- Permissions: internet; notifications (asked once, after signing in); approximate and precise
  location, asked only on "Use where I am now"; and what Firebase Messaging adds (wake lock,
  network state, receiving messages), unused until push is switched on.
- No external payment links: the app has no Donate page. Play allows outside donation links only
  for registered charities; donations stay on the website (paused until a PayPal account is set).
- User-generated content: joining shows the terms; people, openings, messages, events,
  announcements and acknowledgements can be reported and people blocked; reports reach the
  administrators' queue in the app and on the site.
- AI-generated content: AI pictures are labelled; AI help's wording and pictures can be reported
  from where they appear; the demo spheres' personas are labelled AI and their names are a letter
  off the real people they echo (2026-11-25). Three of them (Jo Rodan, Emma Wotson, Elon Mask)
  have pictures that are likenesses of those people, with quotes in them; the others show
  initials. If review objects, replacing those three pictures is the next step.
