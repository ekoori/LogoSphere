package com.krbavcic.logosphere.data

import android.content.Context
import android.content.pm.PackageManager
import android.net.Uri
import androidx.core.content.FileProvider
import java.io.File
import java.util.concurrent.TimeUnit

/** Photos taken from inside the app: kept in the cache until they're sent, then swept. */
object Captures {
    private val KEEP_MS = TimeUnit.DAYS.toMillis(2)

    fun available(context: Context): Boolean =
        context.packageManager.hasSystemFeature(PackageManager.FEATURE_CAMERA_ANY)

    /** An empty file for the camera app to write into, as a content URI. */
    fun newFile(context: Context): Uri {
        val folder = File(context.cacheDir, "captures").apply { mkdirs() }
        val now = System.currentTimeMillis()
        folder.listFiles()?.forEach { if (now - it.lastModified() > KEEP_MS) it.delete() }
        val file = File.createTempFile("photo-", ".jpg", folder)
        return FileProvider.getUriForFile(context, "${context.packageName}.files", file)
    }
}
