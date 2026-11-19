package com.krbavcic.logosphere.ui.theme

import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.ui.graphics.Color

// The web's design tokens (frontend/src/styles/theme.css): sunlit linen, moss, terracotta, honey.
object Palette {
    val Paper = Color(0xFFF3ECDA)
    val PaperDeep = Color(0xFFEBE0C6)
    val Surface = Color(0xFFFDFAF2)
    val Surface2 = Color(0xFFF6EFE0)

    val Ink = Color(0xFF232A1D)
    val InkSoft = Color(0xFF54593F)
    val InkFaint = Color(0xFF8B8A6F)

    val Moss = Color(0xFF46583A)
    val MossDeep = Color(0xFF2F3D27)
    val Leaf = Color(0xFF6F8A4F)
    val Sage = Color(0xFF9BAB83)

    val Terracotta = Color(0xFFC2643C)
    val TerracottaDeep = Color(0xFFA64F2C)
    val Honey = Color(0xFFD9A23F)
    val HoneyDeep = Color(0xFFC2882A)

    val Border = Color(0xFFDDD2B4)
    val Danger = Color(0xFFB1442F)
    val Success = Color(0xFF5D7A3C)

    // Night: the same hues, lit from below.
    val Night = Color(0xFF171C13)
    val NightSurface = Color(0xFF1E251A)
}

val LightColors = lightColorScheme(
    primary = Palette.Moss,
    onPrimary = Palette.Surface,
    primaryContainer = Color(0xFFDCE5C9),
    onPrimaryContainer = Palette.MossDeep,
    secondary = Palette.HoneyDeep,
    onSecondary = Color(0xFF2E2208),
    secondaryContainer = Color(0xFFF5E3BC),
    onSecondaryContainer = Color(0xFF5A3F0E),
    tertiary = Palette.Terracotta,
    onTertiary = Color(0xFFFFF8F0),
    tertiaryContainer = Color(0xFFF4D9CB),
    onTertiaryContainer = Color(0xFF6B2E15),
    error = Palette.Danger,
    onError = Color.White,
    errorContainer = Color(0xFFF6D8D0),
    onErrorContainer = Color(0xFF5C1B10),
    background = Palette.Paper,
    onBackground = Palette.Ink,
    surface = Palette.Paper,
    onSurface = Palette.Ink,
    surfaceVariant = Palette.Surface2,
    onSurfaceVariant = Palette.InkSoft,
    surfaceTint = Palette.Moss,
    outline = Palette.InkFaint,
    outlineVariant = Palette.Border,
    inverseSurface = Palette.MossDeep,
    inverseOnSurface = Palette.Paper,
    inversePrimary = Color(0xFFA9C08A),
    surfaceBright = Palette.Surface,
    surfaceDim = Palette.PaperDeep,
    surfaceContainerLowest = Color.White,
    surfaceContainerLow = Palette.Surface,
    surfaceContainer = Palette.Surface2,
    surfaceContainerHigh = Color(0xFFEFE6D0),
    surfaceContainerHighest = Palette.PaperDeep,
)

val DarkColors = darkColorScheme(
    primary = Color(0xFFA9C08A),
    onPrimary = Color(0xFF1C2914),
    primaryContainer = Color(0xFF34452A),
    onPrimaryContainer = Color(0xFFD5E6BD),
    secondary = Color(0xFFE9BE6A),
    onSecondary = Color(0xFF3B2A05),
    secondaryContainer = Color(0xFF5A4313),
    onSecondaryContainer = Color(0xFFF8E1B0),
    tertiary = Color(0xFFE8956E),
    onTertiary = Color(0xFF4A1A06),
    tertiaryContainer = Color(0xFF6E3219),
    onTertiaryContainer = Color(0xFFFFD9C8),
    error = Color(0xFFF0A08F),
    onError = Color(0xFF5C1B10),
    errorContainer = Color(0xFF7A2A1B),
    onErrorContainer = Color(0xFFFFDAD2),
    background = Palette.Night,
    onBackground = Color(0xFFECE6D4),
    surface = Palette.Night,
    onSurface = Color(0xFFECE6D4),
    surfaceVariant = Color(0xFF2D3627),
    onSurfaceVariant = Color(0xFFC3C0A6),
    surfaceTint = Color(0xFFA9C08A),
    outline = Color(0xFF8F8D74),
    outlineVariant = Color(0xFF3D4636),
    inverseSurface = Color(0xFFECE6D4),
    inverseOnSurface = Palette.MossDeep,
    inversePrimary = Palette.Moss,
    surfaceBright = Color(0xFF353F2E),
    surfaceDim = Palette.Night,
    surfaceContainerLowest = Color(0xFF12160F),
    surfaceContainerLow = Palette.NightSurface,
    surfaceContainer = Color(0xFF232B1E),
    surfaceContainerHigh = Color(0xFF2A3324),
    surfaceContainerHighest = Color(0xFF323C2B),
)
