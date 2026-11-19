package com.krbavcic.logosphere.core

import com.krbavcic.logosphere.core.api.LogoSphereJson

/** Responses recorded from the real API (demo seed data), under src/test/resources/fixtures. */
object Fixtures {
    fun text(name: String): String =
        requireNotNull(javaClass.classLoader.getResource("fixtures/$name")) { "missing fixture $name" }.readText()

    inline fun <reified T> decode(name: String): T = LogoSphereJson.decodeFromString<T>(text(name))
}
