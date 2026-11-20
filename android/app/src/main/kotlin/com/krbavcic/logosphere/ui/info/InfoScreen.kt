package com.krbavcic.logosphere.ui.info

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.krbavcic.logosphere.core.logic.InfoPage
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.common.BackTopBar
import com.krbavcic.logosphere.ui.common.BrandCard
import com.krbavcic.logosphere.ui.common.LinkText
import com.krbavcic.logosphere.ui.common.ScreenPadding
import com.krbavcic.logosphere.ui.common.readable
import com.krbavcic.logosphere.ui.theme.FrauncesDisplay
import com.krbavcic.logosphere.ui.theme.Palette

/** One of the site's information pages, drawn natively. */
@Composable
fun InfoScreen(page: InfoPage) {
    val navigator = LocalNavigator.current
    val uri = LocalUriHandler.current
    val blocks = InfoContent.of(page)
    Scaffold(topBar = { BackTopBar(page.title, navigator::back) }) { padding ->
        LazyColumn(
            Modifier.padding(padding),
            contentPadding = PaddingValues(start = ScreenPadding, end = ScreenPadding, top = 8.dp, bottom = 40.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            itemsIndexed(blocks) { _, block ->
                Box(Modifier.readable()) {
                    BlockView(block, onPage = navigator::info, onUrl = { uri.openUri(it) })
                }
            }
        }
    }
}

@Composable
private fun BlockView(block: Block, onPage: (InfoPage) -> Unit, onUrl: (String) -> Unit) {
    val colors = MaterialTheme.colorScheme
    when (block) {
        is Block.Eyebrow -> Text(block.text.uppercase(), style = MaterialTheme.typography.labelMedium, color = colors.tertiary)
        is Block.Title -> Text(block.text, style = MaterialTheme.typography.headlineMedium, fontFamily = FrauncesDisplay)
        is Block.Lead -> Text(block.text, style = MaterialTheme.typography.bodyLarge, color = colors.onSurfaceVariant)
        is Block.Heading -> Column(Modifier.padding(top = 16.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            block.number?.let { Text(it, style = MaterialTheme.typography.labelLarge, color = colors.tertiary) }
            Text(block.text, style = MaterialTheme.typography.titleLarge, fontFamily = FrauncesDisplay)
        }
        is Block.Para -> Text(block.text, style = MaterialTheme.typography.bodyLarge)
        is Block.Bullets -> Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            block.items.forEach { item ->
                Row {
                    Text("•  ", style = MaterialTheme.typography.bodyLarge, color = colors.primary)
                    Text(item, style = MaterialTheme.typography.bodyLarge)
                }
            }
        }
        is Block.Steps -> Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            block.items.forEachIndexed { index, (title, text) ->
                Row(verticalAlignment = Alignment.Top) {
                    Box(
                        Modifier.size(28.dp).clip(CircleShape).background(colors.primaryContainer),
                        contentAlignment = Alignment.Center,
                    ) { Text("${index + 1}", style = MaterialTheme.typography.labelLarge, color = colors.onPrimaryContainer) }
                    Spacer(Modifier.width(12.dp))
                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        Text(title, style = MaterialTheme.typography.titleSmall)
                        Text(text, style = MaterialTheme.typography.bodyMedium, color = colors.onSurfaceVariant)
                    }
                }
            }
        }
        is Block.Terms -> Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            block.items.forEachIndexed { index, (term, gloss) ->
                val highlight = block.highlightLast && index == block.items.lastIndex
                Column(
                    Modifier
                        .fillMaxWidth()
                        .clip(MaterialTheme.shapes.medium)
                        .background(if (highlight) colors.primaryContainer else colors.surfaceContainerLow)
                        .padding(horizontal = 14.dp, vertical = 10.dp),
                    verticalArrangement = Arrangement.spacedBy(2.dp),
                ) {
                    Text(term, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                    Text(gloss, style = MaterialTheme.typography.bodyMedium, color = colors.onSurfaceVariant)
                }
            }
        }
        is Block.Quote -> Text(
            "“${block.text}”" + (block.by?.let { " — $it" } ?: ""),
            style = MaterialTheme.typography.titleMedium,
            fontFamily = FrauncesDisplay,
            fontStyle = FontStyle.Italic,
            color = colors.primary,
            modifier = Modifier.padding(vertical = 8.dp),
        )
        is Block.ExampleCard -> BrandCard(Modifier.fillMaxWidth()) {
            Column(
                Modifier
                    .fillMaxWidth()
                    .drawBehind { drawRect(Palette.HoneyDeep, size = Size(5.dp.toPx(), size.height)) }
                    .padding(start = 21.dp, top = 16.dp, end = 16.dp, bottom = 16.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                block.fields.forEach { (label, text) ->
                    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        Text(label.uppercase(), style = MaterialTheme.typography.labelSmall, color = colors.onSurfaceVariant)
                        Text(text, style = MaterialTheme.typography.bodyMedium)
                    }
                }
            }
        }
        is Block.Link -> when {
            block.page != null -> LinkText(block.label, onClick = { onPage(block.page) })
            block.url != null -> OutlinedButton(onClick = { onUrl(block.url) }, modifier = Modifier.fillMaxWidth()) { Text(block.label) }
        }
    }
}
