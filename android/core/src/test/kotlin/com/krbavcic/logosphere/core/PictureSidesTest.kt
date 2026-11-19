package com.krbavcic.logosphere.core

import com.krbavcic.logosphere.core.api.LogoSphereJson
import com.krbavcic.logosphere.core.api.pictureSideFor
import com.krbavcic.logosphere.core.model.Exchange
import com.krbavcic.logosphere.core.model.LikeInfo
import com.krbavcic.logosphere.core.model.LikeTarget
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Small avatars ask for a small copy; what the viewer made offers no like button. */
class PictureSidesTest {
    @Test
    fun anAvatarAsksForTheSmallestCopyThatIsStillSharp() {
        assertEquals(160, pictureSideFor(126))   // 48 dp on the Note 9
        assertEquals(320, pictureSideFor(161))
        assertEquals(640, pictureSideFor(640))
        assertNull(pictureSideFor(641))          // bigger than any copy: the full picture
    }

    @Test
    fun yourOwnPartsOfAnExchangeAreNotYoursToLike() {
        val x = LogoSphereJson.decodeFromString<Exchange>(
            """{"exchange_id": "x1", "likes": {
                "exchange": {"count": 2, "liked": false, "by": [], "own": true},
                "user": {"count": 0, "liked": false, "by": []}}}""",
        )
        assertFalse(x.likesFor(LikeTarget.Exchange).canLike)
        assertEquals(2, x.likesFor(LikeTarget.Exchange).count)
        assertTrue(x.likesFor(LikeTarget.InitiatorNote).canLike)       // older payloads: no "own"
        assertTrue(LikeInfo(liked = true, own = true).canLike)         // an old self-like can come off
    }
}
