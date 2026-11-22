package com.krbavcic.logosphere.ui.events

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.krbavcic.logosphere.core.api.pictureSideFor
import com.krbavcic.logosphere.core.logic.EventAnswer
import com.krbavcic.logosphere.core.logic.Events
import com.krbavcic.logosphere.core.logic.Repeats
import com.krbavcic.logosphere.core.model.CommunityEvent
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.common.AiPictureTag
import com.krbavcic.logosphere.ui.common.BrandCard
import com.krbavcic.logosphere.ui.common.DemoTag
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.WhereLine
import java.util.Locale

/** An event in a list, by its next date. [inGroup]: the group whose list it is, which needn't be named. */
@Composable
fun EventCard(event: CommunityEvent, onClick: () -> Unit, modifier: Modifier = Modifier, inGroup: String? = null) {
    val next = event.upcoming ?: return
    val app = LocalAppContainer.current
    val told = Events.whenText(next, event.tz)
    val day = Events.date(next.day)
    val repeats = Repeats.of(event.repeats)
    val about = listOfNotNull(
        (event.host?.name ?: "For everyone").takeIf { inGroup == null || event.host?.id != inGroup },
        Events.repeatText(repeats, Events.date(event.starts)).takeIf { repeats != Repeats.Never },
    ).joinToString(" · ")
    val mine = EventAnswer.of(next.myAnswer)?.let { "You: ${it.label}" }
    val coming = listOfNotNull(Events.comingText(next).takeIf { it.isNotEmpty() }, mine).joinToString(" · ")

    BrandCard(modifier.fillMaxWidth(), onClick = onClick) {
        Row(Modifier.padding(12.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            if (day != null) {
                Column(
                    // The words beside it say the date already.
                    Modifier
                        .clearAndSetSemantics { }
                        .size(52.dp)
                        .clip(MaterialTheme.shapes.small)
                        .background(MaterialTheme.colorScheme.surfaceContainerHigh),
                    verticalArrangement = Arrangement.Center,
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text(day.dayOfMonth.toString(), style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.primary)
                    Text(
                        day.month.getDisplayName(java.time.format.TextStyle.SHORT, Locale.getDefault()).uppercase(),
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Text(event.title, style = MaterialTheme.typography.titleMedium, maxLines = 3, overflow = TextOverflow.Ellipsis)
                Text(told.text + (told.zoneNote?.let { " ($it)" } ?: ""), style = MaterialTheme.typography.bodyMedium)
                if (about.isNotEmpty()) MetaText(about, maxLines = 2)
                WhereLine(event.location, event.distance, maxLines = 2)
                if (coming.isNotEmpty()) MetaText(coming, maxLines = 2)
                if (event.isDemo) DemoTag()
            }
            if (event.hasImage) {
                val side = pictureSideFor(with(LocalDensity.current) { 72.dp.roundToPx() })
                Box(Modifier.size(72.dp).clip(MaterialTheme.shapes.small)) {
                    AsyncImage(
                        model = app.pictures.of(app.api.eventImageUrl(event.id, side)),
                        contentDescription = null,
                        contentScale = ContentScale.Crop,
                        modifier = Modifier.fillMaxSize(),
                    )
                    if (event.imageIsAi) AiPictureTag(Modifier.align(Alignment.BottomStart), short = true)
                }
            }
        }
    }
}
