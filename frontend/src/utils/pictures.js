// Photos straight from a phone camera are 3-10 MB each; three of them don't
// fit in one upload (12 MB). Small files go as they are; larger ones become a
// JPEG no more than 2048 px across, the right way up (as the app does).
export const KEEP_AS_IS_BYTES = 1_500_000;
export const MAX_SIDE = 2048;

export function fitWithin(width, height, max = MAX_SIDE) {
    const scale = Math.min(1, max / Math.max(width, height));
    return { width: Math.round(width * scale), height: Math.round(height * scale) };
}

export async function forUpload(file) {
    if (!file || file.size <= KEEP_AS_IS_BYTES || file.type === 'image/gif') return file;
    let bitmap;
    try {
        bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });
    } catch (_) {
        return file; // not one this browser can read: the server will say
    }
    const { width, height } = fitWithin(bitmap.width, bitmap.height);
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, width, height);
    ctx.drawImage(bitmap, 0, 0, width, height);
    bitmap.close();
    const blob = await new Promise((resolve) => { canvas.toBlob(resolve, 'image/jpeg', 0.85); });
    return blob ? new File([blob], 'photo.jpg', { type: 'image/jpeg' }) : file;
}
