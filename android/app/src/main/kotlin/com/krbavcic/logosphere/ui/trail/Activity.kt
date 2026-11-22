package com.krbavcic.logosphere.ui.trail

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import com.krbavcic.logosphere.core.logic.Dates
import com.krbavcic.logosphere.core.logic.Links
import com.krbavcic.logosphere.core.model.ActivityItem
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.common.Avatar
import com.krbavcic.logosphere.ui.common.DemoTag
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.PersonaTag
import com.krbavcic.logosphere.ui.common.QuoteLine
import com.krbavcic.logosphere.ui.theme.Brand

/** One thing someone you follow did. */
@Composable
internal fun ActivityRow(item: ActivityItem, modifier: Modifier = Modifier) {
    val navigator = LocalNavigator.current
    val titleColor = MaterialTheme.colorScheme.primary
    val words = buildAnnotatedString {
        withStyle(SpanStyle(fontWeight = FontWeight.Bold)) { append(item.who.name) }
        append(" ${item.says}")
        if (item.title.isNotEmpty()) {
            append(" ")
            withStyle(SpanStyle(color = titleColor, fontWeight = FontWeight.SemiBold)) { append(item.title) }
        }
    }
    Row(
        modifier
            .fillMaxWidth()
            .clickable(role = Role.Button) { Links.parse(item.link)?.let(navigator::link) }
            .padding(vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Avatar(item.who.id, item.who.name, size = 40.dp)
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
            Text(words, style = MaterialTheme.typography.bodyMedium)
            item.text?.takeIf { it.isNotBlank() }?.let {
                QuoteLine(author = "Their words", text = it, accent = Brand.colors.acknowledgementAccent, maxLines = 4)
            }
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                MetaText(Dates.ago(item.at))
                if (item.who.isAgent) PersonaTag(compact = true)
                if (item.isDemo) DemoTag()
            }
        }
    }
}
