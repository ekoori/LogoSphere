package com.krbavcic.logosphere.core.api

/** A picture to send as a multipart part: its bytes, a file name and its media type. */
class Upload(
    val bytes: ByteArray,
    val fileName: String = "picture.jpg",
    val mimeType: String = "image/jpeg",
)
