package com.krbavcic.logosphere.core.logic

import com.krbavcic.logosphere.core.model.GraphEdge
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * A small force layout for the Meaning Graph: cards push each other apart, closeness pulls,
 * everything leans to the middle. The twin of the site's utils/forceLayout.js, constants and all:
 * no randomness, so the same cards settle into the same picture on both.
 */
class ForceLayout(
    ids: Collection<String>,
    edges: List<GraphEdge>,
    previous: Map<String, Point> = emptyMap(),
) {
    data class Point(val x: Double, val y: Double)

    class Body(val id: String, var x: Double, var y: Double) {
        internal var vx = 0.0
        internal var vy = 0.0

        /** Under someone's finger: forces don't move it. */
        var held = false
    }

    private class Spring(val a: Body, val b: Body, val length: Double, val pull: Double)

    val bodies: List<Body> = ids.sorted().mapIndexed { i, id ->
        val was = previous[id]
        val radius = 26 * sqrt(i + 0.5)
        Body(id, was?.x ?: (radius * cos(i * GOLDEN_ANGLE)), was?.y ?: (radius * sin(i * GOLDEN_ANGLE)))
    }
    val byId: Map<String, Body> = bodies.associateBy { it.id }

    private val springs: List<Spring>
    private var heat = if (previous.isEmpty()) 1.0 else 0.45

    init {
        val joined = edges.filter { it.a in byId && it.b in byId }
        val count = HashMap<String, Int>()
        for (edge in joined) {
            count.merge(edge.a, 1, Int::plus)
            count.merge(edge.b, 1, Int::plus)
        }
        springs = joined.map { edge ->
            // The square root spreads out the low end, where most closeness is.
            val t = sqrt(edge.closeness.coerceIn(0.0, 1.0))
            Spring(
                a = byId.getValue(edge.a),
                b = byId.getValue(edge.b),
                length = NEAR + SPAN * (1 - t),
                // A card with many connections mustn't drag its whole neighbourhood into one knot.
                pull = (PULL + MORE_PULL * t) / sqrt(min(count.getValue(edge.a), count.getValue(edge.b)).toDouble()),
            )
        }.sortedWith(compareBy({ it.a.id }, { it.b.id }))
    }

    val moving: Boolean get() = heat > SETTLED

    fun reheat() {
        heat = max(heat, 0.3)
    }

    fun positions(): Map<String, Point> = bodies.associate { it.id to Point(it.x, it.y) }

    fun settle() {
        var steps = 0
        while (moving && steps < 400) {
            step()
            steps++
        }
    }

    fun step() {
        for (i in bodies.indices) {
            val p = bodies[i]
            for (j in i + 1 until bodies.size) {
                val q = bodies[j]
                var dx = q.x - p.x
                var dy = q.y - p.y
                var squared = dx * dx + dy * dy
                if (squared < 0.01) {
                    dx = cos((i + j).toDouble())
                    dy = sin((i + j).toDouble())
                    squared = 1.0
                }
                val d = sqrt(squared)
                val force = PUSH * heat / max(squared, 120.0)
                p.vx -= dx / d * force
                p.vy -= dy / d * force
                q.vx += dx / d * force
                q.vy += dy / d * force
            }
        }
        for (spring in springs) {
            val a = spring.a
            val b = spring.b
            val dx = b.x - a.x
            val dy = b.y - a.y
            val d = sqrt(dx * dx + dy * dy).let { if (it == 0.0) 1.0 else it }
            val force = (d - spring.length) * spring.pull * heat
            a.vx += dx / d * force
            a.vy += dy / d * force
            b.vx -= dx / d * force
            b.vy -= dy / d * force
        }
        for (body in bodies) {
            if (body.held) {
                body.vx = 0.0
                body.vy = 0.0
                continue
            }
            body.vx = (body.vx - body.x * LEAN * heat) * KEEP_SPEED
            body.vy = (body.vy - body.y * LEAN * heat) * KEEP_SPEED
            val speed = sqrt(body.vx * body.vx + body.vy * body.vy)
            val brake = if (speed > TOP_SPEED) TOP_SPEED / speed else 1.0
            body.x += body.vx * brake
            body.y += body.vy * brake
        }
        heat *= COOLING
    }

    private companion object {
        val GOLDEN_ANGLE = PI * (3 - sqrt(5.0))
        const val COOLING = 0.985
        const val SETTLED = 0.012
        const val PUSH = 6000.0
        const val LEAN = 0.012
        const val NEAR = 16.0
        const val SPAN = 40.0
        const val PULL = 0.03
        const val MORE_PULL = 0.4
        const val KEEP_SPEED = 0.58
        const val TOP_SPEED = 30.0
    }
}
