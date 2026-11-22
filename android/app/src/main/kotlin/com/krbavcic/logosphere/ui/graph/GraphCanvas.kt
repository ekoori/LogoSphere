package com.krbavcic.logosphere.ui.graph

import android.animation.ValueAnimator
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.calculateCentroid
import androidx.compose.foundation.gestures.calculatePan
import androidx.compose.foundation.gestures.calculateZoom
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.runtime.withFrameNanos
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.geometry.isSpecified
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Fill
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.toSize
import com.krbavcic.logosphere.core.logic.ForceLayout
import com.krbavcic.logosphere.core.logic.ShownGraph
import com.krbavcic.logosphere.core.model.FranklMode
import com.krbavcic.logosphere.core.model.GraphEdge
import com.krbavcic.logosphere.core.model.GraphNode
import com.krbavcic.logosphere.ui.theme.Brand
import com.krbavcic.logosphere.ui.theme.BrandColors
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt
import kotlin.math.sqrt

private const val MIN_ZOOM = 0.2f
private const val MAX_ZOOM = 4f
private const val LABEL_ZOOM = 1.05f
private const val STEPS_A_FRAME = 2
private const val UNSEEN_STEPS = 40
private const val MAX_LABEL = 34

/** The corner the screen's zoom buttons sit in: no label runs under them. */
private val BUTTONS_WIDE = 56.dp
private val BUTTONS_HIGH = 156.dp

/** The colour of a kind of meaning. Never alone: its glyph is drawn in it, its word is beside it. */
internal fun BrandColors.meaning(mode: FranklMode): Color = when (mode) {
    FranklMode.Creative -> graphCreative
    FranklMode.Experiential -> graphExperiential
    FranklMode.Attitudinal -> graphAttitudinal
}

/** A node's radius in dp: by connections, never likes. */
private fun radiusFor(degree: Int?): Float = 5.5f + min(9f, sqrt((degree ?: 0).toFloat()) * 2.3f)

private fun short(text: String) = if (text.length > MAX_LABEL) text.take(MAX_LABEL - 2) + "…" else text

/** The picture's moving parts: the layout (in dp) and the member's view of it (in px). */
class GraphDrawing {
    internal var layout: ForceLayout? = null
        private set

    /** Read while drawing, bumped on every change: only the drawing is redone. */
    internal var frame by mutableIntStateOf(0)
        private set

    /** Bumped when the layout has to run again. */
    internal var run by mutableIntStateOf(0)
        private set

    internal var size = Size.Zero
        private set
    internal var density = 1f
    internal var pan = Offset.Zero
        private set
    internal var zoom = 1f
        private set
    private var touched = false
    private var cards: Set<String> = emptySet()

    private fun still() = !ValueAnimator.areAnimatorsEnabled()

    internal fun show(ids: List<String>, edges: List<GraphEdge>) {
        val layout = ForceLayout(ids, edges, layout?.positions().orEmpty())
        this.layout = layout
        // Other connections between the same cards keep the view you chose; other cards fit afresh.
        val now = ids.toSet()
        if (now != cards) touched = false
        cards = now
        // The first tangle sorts itself out unseen; the rest is worth watching.
        if (still()) layout.settle() else repeat(UNSEEN_STEPS) { layout.step() }
        if (!touched) fitView()
        run++
        frame++
    }

    internal fun tick(): Boolean {
        val layout = layout ?: return false
        if (!layout.moving) return false
        repeat(STEPS_A_FRAME) { if (layout.moving) layout.step() }
        if (!touched) fitView()
        frame++
        return layout.moving
    }

    internal fun resize(to: Size) {
        size = to
        if (!touched) fitView()
        frame++
    }

    internal fun at(body: ForceLayout.Body) = Offset(
        size.width / 2 + pan.x + body.x.toFloat() * zoom * density,
        size.height / 2 + pan.y + body.y.toFloat() * zoom * density,
    )

    private fun fitView() {
        val bodies = layout?.bodies.orEmpty()
        if (bodies.isEmpty() || size.width <= 0f) return
        val left = bodies.minOf { it.x }
        val right = bodies.maxOf { it.x }
        val top = bodies.minOf { it.y }
        val bottom = bodies.maxOf { it.y }
        val width = size.width / density.toDouble()
        val height = size.height / density.toDouble()
        // Room for labels at the edges.
        val k = min(
            (width - min(130.0, width * 0.18)) / max(right - left, 120.0),
            (height - min(90.0, height * 0.18)) / max(bottom - top, 120.0),
        ).toFloat().coerceIn(MIN_ZOOM, 1.6f)
        zoom = k
        pan = Offset(
            (-(left + right) / 2).toFloat() * k * density,
            ((-(top + bottom) / 2).toFloat() * k - 6f) * density,
        )
    }

    /** Puts everything back in view. */
    fun fit() {
        touched = false
        fitView()
        frame++
    }

    fun zoomBy(factor: Float) = zoomAround(factor, Offset(size.width / 2, size.height / 2))

    internal fun zoomAround(factor: Float, point: Offset) {
        val k = (zoom * factor).coerceIn(MIN_ZOOM, MAX_ZOOM)
        val from = point - Offset(size.width / 2, size.height / 2)
        pan = from - (from - pan) * (k / zoom)
        zoom = k
        touched = true
        frame++
    }

    internal fun panBy(by: Offset) {
        pan += by
        touched = true
        frame++
    }

    internal fun drag(body: ForceLayout.Body, by: Offset) {
        body.held = true
        body.x += by.x / (zoom * density)
        body.y += by.y / (zoom * density)
        touched = true
        if (!still()) {
            layout?.reheat()
            run++
        }
        frame++
    }

    /** The card under a finger: anything within [slop], the nearest first. */
    internal fun bodyAt(point: Offset, degree: Map<String, Int>, slop: Float): ForceLayout.Body? = layout?.bodies.orEmpty()
        .map { it to (at(it) - point).getDistance() }
        .filter { (body, away) -> away <= max(slop, radiusFor(degree[body.id]) * 1.7f * density) }
        .minByOrNull { it.second }
        ?.first
}

/**
 * The Meaning Graph drawn: pinch, pan, drag a card, tap one. A circle is a person's card, a square
 * a group's. The screen's list has the same for TalkBack.
 */
@Composable
fun GraphCanvas(
    shown: ShownGraph,
    selected: String?,
    onSelect: (String?) -> Unit,
    drawing: GraphDrawing,
    surface: Color,
    ink: Color,
    modifier: Modifier = Modifier,
) {
    val colours = Brand.colors
    val measurer = rememberTextMeasurer(cacheSize = 256)
    val labelStyle = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold)
    drawing.density = LocalDensity.current.density

    val ids = remember(shown) { shown.nodes.map { it.id } }
    LaunchedEffect(drawing, ids, shown.edges) { drawing.show(ids, shown.edges) }
    LaunchedEffect(drawing) {
        // Not restarted by each nudge of a drag: that would keep cancelling the frame it waits for.
        snapshotFlow { drawing.run }.collect {
            do {
                withFrameNanos { }
            } while (drawing.tick())
        }
    }

    val graphNow by rememberUpdatedState(shown)
    val select by rememberUpdatedState(onSelect)

    Canvas(
        modifier
            .fillMaxSize()
            .clipToBounds()
            .onSizeChanged { drawing.resize(it.toSize()) }
            .semantics {
                contentDescription = "Meaning Graph: ${shown.nodes.size} value cards, ${shown.edges.size} connections. " +
                    "The list has the same as text."
            }
            .pointerInput(drawing) {
                awaitEachGesture {
                    val down = awaitFirstDown(requireUnconsumed = false)
                    var held = drawing.bodyAt(down.position, graphNow.degree, slop = 24.dp.toPx())
                    val pressed = held
                    var moved = false
                    var travel = Offset.Zero
                    try {
                        while (true) {
                            val event = awaitPointerEvent()
                            val fingers = event.changes.count { it.pressed }
                            if (fingers == 0) break
                            if (fingers > 1) {
                                held?.held = false
                                held = null
                                moved = true
                                // No centre while every finger has only just landed.
                                val middle = event.calculateCentroid(useCurrent = false)
                                if (middle.isSpecified) drawing.zoomAround(event.calculateZoom(), middle)
                                drawing.panBy(event.calculatePan())
                            } else {
                                val by = event.calculatePan()
                                travel += by
                                if (!moved && travel.getDistance() > viewConfiguration.touchSlop) moved = true
                                if (moved) {
                                    val body = held
                                    if (body != null) drawing.drag(body, by) else drawing.panBy(by)
                                }
                            }
                            event.changes.forEach { it.consume() }
                        }
                        if (!moved) select(pressed?.id)
                    } finally {
                        held?.held = false
                    }
                }
            },
    ) {
        drawing.frame // redraw on every change of the picture
        val layout = drawing.layout ?: return@Canvas
        val bodies = layout.byId
        val zoom = drawing.zoom
        val scale = sqrt(zoom).coerceIn(0.7f, 1.7f)
        fun radius(id: String) = radiusFor(shown.degree[id]) * scale * density

        val centre = selected?.takeIf { it in shown.degree }
        val lit = buildSet {
            if (centre != null) {
                add(centre)
                for (edge in shown.edges) if (edge.touches(centre)) add(edge.other(centre))
            }
        }
        val searching = shown.found.size < shown.nodes.size
        fun bright(id: String) = if (centre != null) id in lit else !searching || id in shown.found

        for (edge in shown.edges) {
            val a = bodies[edge.a] ?: continue
            val b = bodies[edge.b] ?: continue
            val on = centre != null && edge.touches(centre)
            drawLine(
                color = if (on) colours.graphEdgeLit else colours.graphEdge,
                start = drawing.at(a),
                end = drawing.at(b),
                strokeWidth = (0.8f + 1.6f * edge.closeness.toFloat()).dp.toPx(),
                alpha = if (centre != null && !on) 0.2f else 1f,
            )
        }

        for (node in shown.nodes) {
            val body = bodies[node.id] ?: continue
            val at = drawing.at(body)
            val r = radius(node.id)
            val alpha = if (bright(node.id)) 1f else 0.22f
            val fill = colours.meaning(node.mode)
            val ring = Stroke(2.dp.toPx())
            if (node.owner.isGroup) {
                val half = r * 0.89f
                val topLeft = at - Offset(half, half)
                drawRect(fill, topLeft, Size(half * 2, half * 2), alpha = alpha)
                drawRect(surface, topLeft, Size(half * 2, half * 2), alpha = alpha, style = ring)
            } else {
                drawCircle(fill, r, at, alpha = alpha)
                drawCircle(surface, r, at, alpha = alpha, style = ring)
            }
            if (r >= 5.dp.toPx()) {
                val glyph = measurer.measure(
                    node.mode.glyph,
                    TextStyle(fontSize = (r * 1.15f).roundToInt().toFloat().toSp(), fontWeight = FontWeight.Bold),
                )
                drawText(glyph, surface, at - Offset(glyph.size.width / 2f, glyph.size.height / 2f), alpha = alpha)
            }
            if (node.id == centre) drawCircle(ink, r + 4.dp.toPx(), at, style = Stroke(2.dp.toPx()))
        }

        // Labels where they fit, covering no other label or node: the chosen card and its
        // neighbours first, then the most connected.
        val marks = shown.nodes.mapNotNull { node ->
            val body = bodies[node.id]?.takeIf { bright(node.id) } ?: return@mapNotNull null
            node.id to Rect(drawing.at(body), radius(node.id))
        }
        val wanted = shown.nodes
            .sortedWith(
                compareByDescending<GraphNode> { it.id == centre }
                    .thenByDescending { it.id in lit }
                    .thenByDescending { shown.degree[it.id] ?: 0 }
                    .thenBy { it.id },
            )
        val allow = if (centre != null || searching || zoom >= LABEL_ZOOM) wanted.size else max(6, wanted.size / 5)
        val halo = Stroke(width = 3.dp.toPx(), join = StrokeJoin.Round)
        val placed = ArrayList<Rect>()
        val buttons = Rect(size.width - BUTTONS_WIDE.toPx(), 0f, size.width, BUTTONS_HIGH.toPx())
        for (node in wanted) {
            if (placed.size >= allow) break
            val body = bodies[node.id]?.takeIf { bright(node.id) } ?: continue
            val at = drawing.at(body)
            val r = radius(node.id)
            val text = measurer.measure(short(node.title), labelStyle, maxLines = 1, softWrap = false)
            val width = text.size.width.toFloat()
            val height = text.size.height.toFloat()
            val box = listOf(at.y + r + 3.dp.toPx(), at.y - r - 3.dp.toPx() - height)
                .map { top -> Rect(Offset(at.x - width / 2, top), Size(width, height)) }
                .firstOrNull { box ->
                    node.id == centre || (
                        box.left >= 0 && box.right <= size.width && box.top >= 0 && box.bottom <= size.height &&
                            !box.overlaps(buttons) && placed.none { it.overlaps(box) } &&
                            marks.none { (id, mark) -> id != node.id && mark.overlaps(box) }
                        )
                } ?: continue
            placed += box
            drawText(text, surface, box.topLeft, drawStyle = halo)
            drawText(text, ink, box.topLeft, drawStyle = Fill)
        }
    }
}
