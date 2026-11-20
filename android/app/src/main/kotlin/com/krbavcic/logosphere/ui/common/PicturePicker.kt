package com.krbavcic.logosphere.ui.common

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.AddPhotoAlternate
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.krbavcic.logosphere.core.model.CommunityKind

private val imagesOnly = PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)

/** The system photo picker for one picture; returns what opens it. */
@Composable
fun rememberPicturePicker(onPicked: (Uri) -> Unit): () -> Unit {
    val latest by rememberUpdatedState(onPicked)
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri -> uri?.let { latest(it) } }
    return { launcher.launch(imagesOnly) }
}

/** The photo picker for up to [max] pictures (two or more). */
@Composable
fun rememberPicturesPicker(max: Int, onPicked: (List<Uri>) -> Unit): () -> Unit {
    val latest by rememberUpdatedState(onPicked)
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.PickMultipleVisualMedia(max)) { uris ->
        if (uris.isNotEmpty()) latest(uris.take(max))
    }
    return { launcher.launch(imagesOnly) }
}

/**
 * A banner picture in a form: the one just picked, or the current one, or the kind's gradient —
 * with a button to choose another.
 */
@Composable
fun BannerField(
    picked: Uri?,
    currentUrl: String?,
    kind: CommunityKind?,
    onPick: () -> Unit,
    modifier: Modifier = Modifier,
    label: String = "banner picture",
    height: Dp = 140.dp,
) {
    Column(modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Box(Modifier.fillMaxWidth().height(height).clip(MaterialTheme.shapes.large)) {
            if (picked != null) {
                AsyncImage(model = picked, contentDescription = null, contentScale = ContentScale.Crop, modifier = Modifier.fillMaxSize())
            } else {
                Banner(imageUrl = currentUrl, kind = kind, height = height)
            }
        }
        OutlinedButton(onClick = onPick, modifier = Modifier.fillMaxWidth()) {
            Icon(Icons.Outlined.AddPhotoAlternate, contentDescription = null, modifier = Modifier.size(18.dp))
            Text(
                "  " + when {
                    picked != null -> "Choose another picture"
                    currentUrl != null -> "Change the $label"
                    else -> "Add a $label"
                },
            )
        }
    }
}

/** A round photo in a form: the one just picked or the current avatar, with a choose button beside it. */
@Composable
fun PhotoField(picked: Uri?, userId: String?, name: String?, onPick: () -> Unit, modifier: Modifier = Modifier) {
    Row(modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp)) {
        if (picked != null) {
            AsyncImage(
                model = picked,
                contentDescription = "Your new photo",
                contentScale = ContentScale.Crop,
                modifier = Modifier.size(72.dp).clip(CircleShape).background(MaterialTheme.colorScheme.surfaceVariant),
            )
        } else {
            Avatar(userId, name, size = 72.dp)
        }
        TextButton(onClick = onPick) {
            Icon(Icons.Outlined.AddPhotoAlternate, contentDescription = null, modifier = Modifier.size(18.dp))
            Text(if (picked != null) "  Choose another photo" else "  Choose a new photo")
        }
    }
}
