package com.krbavcic.logosphere.ui.common

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.size
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.krbavcic.logosphere.ui.theme.FrauncesDisplay
import com.krbavcic.logosphere.ui.theme.Palette

/** The web header's hand-drawn sun (Header.js BrandMark), on a 32-unit grid. */
@Composable
fun SunMark(size: Dp = 32.dp, color: Color = Palette.Terracotta, modifier: Modifier = Modifier) {
    Canvas(modifier.size(size)) {
        val u = this.size.width / 32f
        drawCircle(color, radius = 6.5f * u, center = Offset(16f * u, 16f * u))
        val rays = listOf(
            16f to 2.5f to (16f to 6f), 16f to 26f to (16f to 29.5f),
            29.5f to 16f to (26f to 16f), 6f to 16f to (2.5f to 16f),
            25.5f to 6.5f to (23.1f to 8.9f), 8.9f to 23.1f to (6.5f to 25.5f),
            25.5f to 25.5f to (23.1f to 23.1f), 8.9f to 8.9f to (6.5f to 6.5f),
        )
        rays.forEach { (from, to) ->
            drawLine(
                color,
                start = Offset(from.first * u, from.second * u),
                end = Offset(to.first * u, to.second * u),
                strokeWidth = 2f * u,
                cap = StrokeCap.Round,
            )
        }
    }
}

/** "Logo**Sphere**", as the web's header sets it. */
@Composable
fun Wordmark(fontSize: TextUnit = 26.sp, modifier: Modifier = Modifier) {
    Row(modifier, verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        SunMark(size = (fontSize.value * 1.15f).dp)
        Text(
            buildAnnotatedString {
                append("Logo")
                withStyle(SpanStyle(color = MaterialTheme.colorScheme.tertiary, fontWeight = FontWeight.Bold)) { append("Sphere") }
            },
            fontFamily = FrauncesDisplay,
            fontWeight = FontWeight.SemiBold,
            fontSize = fontSize,
            color = MaterialTheme.colorScheme.onBackground,
        )
    }
}
