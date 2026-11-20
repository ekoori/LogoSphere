// The framework's ExifInterface reads streams reliably from API 24 (minSdk is 26): no extra
// library for the one tag read here.
@file:SuppressLint("ExifInterface")

package com.krbavcic.logosphere.data

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.media.ExifInterface
import android.net.Uri
import android.provider.OpenableColumns
import androidx.compose.runtime.mutableStateMapOf
import com.krbavcic.logosphere.core.api.AppProblem
import com.krbavcic.logosphere.core.api.Upload
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream
import kotlin.math.max

/**
 * Pictures the member sends (a photo from the picker, ready to upload) and pictures the app shows
 * (marked with a version once replaced, so the new one is fetched instead of the cached copy).
 */
class Pictures(private val context: Context) {
    private val versions = mutableStateMapOf<String, Long>()

    /**
     * [url], with a version mark once its picture was replaced in this session. Read in
     * composition, so a replaced picture redraws. Every size of a picture shares one mark.
     */
    fun of(url: String): String {
        val version = versions[url.substringBefore('?')] ?: return url
        return url + (if ('?' in url) "&" else "?") + "v=$version"
    }

    /** The picture at [url] (any of its sizes) was just replaced on the server. */
    fun replaced(url: String) {
        versions[url.substringBefore('?')] = System.currentTimeMillis()
    }

    /**
     * Reads a picked photo for upload. Small JPEG/PNG/WebP/GIF files go as they are; anything
     * larger is scaled so its longer side is at most [MAX_SIDE], turned upright (cameras record
     * rotation in EXIF, which a re-encoded copy would lose) and saved as JPEG. The server makes
     * its own sizes either way.
     */
    suspend fun read(uri: Uri): Upload = withContext(Dispatchers.IO) {
        val resolver = context.contentResolver
        val type = resolver.getType(uri) ?: "image/jpeg"
        val size = resolver.query(uri, arrayOf(OpenableColumns.SIZE), null, null, null)?.use { c ->
            if (c.moveToFirst() && !c.isNull(0)) c.getLong(0) else null
        }
        if (size != null && size <= KEEP_AS_IS_BYTES && type in SENDABLE) {
            val bytes = resolver.openInputStream(uri)?.use { it.readBytes() } ?: throw AppProblem("Couldn't read that picture.")
            return@withContext Upload(bytes, "picture." + type.substringAfter('/').replace("jpeg", "jpg"), type)
        }
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        resolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, bounds) }
        if (bounds.outWidth <= 0 || bounds.outHeight <= 0) throw AppProblem("That file isn't a picture LogoSphere can read.")
        var sample = 1
        while (max(bounds.outWidth, bounds.outHeight) / (sample * 2) >= MAX_SIDE) sample *= 2
        val decoded = resolver.openInputStream(uri)?.use {
            BitmapFactory.decodeStream(it, null, BitmapFactory.Options().apply { inSampleSize = sample })
        } ?: throw AppProblem("Couldn't read that picture.")
        val rotation = runCatching {
            resolver.openInputStream(uri)?.use { ExifInterface(it).rotationDegrees() } ?: 0
        }.getOrDefault(0)
        val longer = max(decoded.width, decoded.height)
        val scale = if (longer > MAX_SIDE) MAX_SIDE.toFloat() / longer else 1f
        val matrix = Matrix().apply {
            if (scale != 1f) postScale(scale, scale)
            if (rotation != 0) postRotate(rotation.toFloat())
        }
        val upright = if (matrix.isIdentity) decoded else Bitmap.createBitmap(decoded, 0, 0, decoded.width, decoded.height, matrix, true)
        val out = ByteArrayOutputStream()
        upright.compress(Bitmap.CompressFormat.JPEG, 85, out)
        if (upright !== decoded) upright.recycle()
        decoded.recycle()
        Upload(out.toByteArray(), "picture.jpg", "image/jpeg")
    }

    private fun ExifInterface.rotationDegrees(): Int = when (getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)) {
        ExifInterface.ORIENTATION_ROTATE_90, ExifInterface.ORIENTATION_TRANSPOSE -> 90
        ExifInterface.ORIENTATION_ROTATE_180 -> 180
        ExifInterface.ORIENTATION_ROTATE_270, ExifInterface.ORIENTATION_TRANSVERSE -> 270
        else -> 0
    }

    private companion object {
        const val MAX_SIDE = 2048
        const val KEEP_AS_IS_BYTES = 1_500_000L
        val SENDABLE = setOf("image/jpeg", "image/png", "image/webp", "image/gif")
    }
}
