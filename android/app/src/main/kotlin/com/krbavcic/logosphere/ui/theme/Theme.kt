package com.krbavcic.logosphere.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.krbavcic.logosphere.core.model.CommunityKind

// The web's radius scale: --r-sm 8, --r-md 12, --r-lg 18, --r-xl 26.
val LogoSphereShapes = Shapes(
    extraSmall = RoundedCornerShape(6.dp),
    small = RoundedCornerShape(8.dp),
    medium = RoundedCornerShape(12.dp),
    large = RoundedCornerShape(18.dp),
    extraLarge = RoundedCornerShape(26.dp),
)

/** Brand colours that have no Material role: the type/kind washes and value-card accents. */
@Immutable
data class BrandColors(
    val offerWash: Color,
    val onOfferWash: Color,
    val needWash: Color,
    val onNeedWash: Color,
    val doneWash: Color,
    val onDoneWash: Color,
    val receiptAccent: Color,
    val acknowledgementAccent: Color,
    val card: Color,
    val cardBorder: Color,
    /** The demonstration: Demo spheres and their AI personas. */
    val demoWash: Color,
    val onDemoWash: Color,
    val personaWash: Color,
    val onPersonaWash: Color,
)

private val LightBrand = BrandColors(
    offerWash = Color(0xFFF4DDD1),
    onOfferWash = Palette.TerracottaDeep,
    needWash = Color(0xFFF6E6C2),
    onNeedWash = Color(0xFF7A5512),
    doneWash = Color(0xFFDDE6CC),
    onDoneWash = Palette.MossDeep,
    receiptAccent = Palette.Leaf,
    acknowledgementAccent = Palette.Honey,
    card = Palette.Surface,
    cardBorder = Palette.Border,
    demoWash = Color(0xFFEDE3F7),
    onDemoWash = Color(0xFF5A338A),
    personaWash = Color(0xFFDDEAF4),
    onPersonaWash = Color(0xFF2F5D7C),
)

private val DarkBrand = BrandColors(
    offerWash = Color(0xFF5A2E1B),
    onOfferWash = Color(0xFFFFD2BE),
    needWash = Color(0xFF55410F),
    onNeedWash = Color(0xFFF8DFA5),
    doneWash = Color(0xFF34452A),
    onDoneWash = Color(0xFFD5E6BD),
    receiptAccent = Color(0xFFA9C08A),
    acknowledgementAccent = Color(0xFFE9BE6A),
    card = Palette.NightSurface,
    cardBorder = Color(0xFF3D4636),
    demoWash = Color(0xFF3E2D55),
    onDemoWash = Color(0xFFE2CFF8),
    personaWash = Color(0xFF22394A),
    onPersonaWash = Color(0xFFBFDDF2),
)

val LocalBrandColors = staticCompositionLocalOf { LightBrand }

/** A value card's accent, by its `color_key`. */
fun valueCardAccent(colorKey: String?): Color = when (colorKey) {
    "leaf" -> Palette.Leaf
    "terracotta" -> Palette.Terracotta
    "moss" -> Palette.Moss
    "sage" -> Palette.Sage
    else -> Palette.Honey
}

/** The web's per-kind banner gradients (EntityBanner.css), for entities without a photo. */
fun kindGradient(kind: CommunityKind?): Brush = when (kind) {
    CommunityKind.Sphere -> Brush.linearGradient(listOf(Palette.Honey, Palette.Terracotta, Palette.MossDeep))
    CommunityKind.Alliance -> Brush.linearGradient(listOf(Palette.Moss, Palette.MossDeep, Color(0xFF26311E)))
    CommunityKind.Project -> Brush.linearGradient(listOf(Palette.Leaf, Palette.Moss, Palette.MossDeep))
    null -> Brush.linearGradient(listOf(Palette.Terracotta, Palette.Honey, Palette.MossDeep)) // an opening
}

@Composable
fun LogoSphereTheme(darkTheme: Boolean = isSystemInDarkTheme(), content: @Composable () -> Unit) {
    androidx.compose.runtime.CompositionLocalProvider(LocalBrandColors provides if (darkTheme) DarkBrand else LightBrand) {
        MaterialTheme(
            colorScheme = if (darkTheme) DarkColors else LightColors,
            typography = LogoSphereTypography,
            shapes = LogoSphereShapes,
            content = content,
        )
    }
}

object Brand {
    val colors: BrandColors
        @Composable get() = LocalBrandColors.current
}
