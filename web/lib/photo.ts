// Shrink a phone photo before upload: a 12 MP camera photo is 3-8 MB, which takes minutes on 2G/3G and can hit
// the server's 10 MB limit. The server only keeps 1600 px anyway (server/main.py MAX_SIDE), so we send that.
// Upright: the phone's rotation tag is applied while decoding. If anything fails, the original file is sent.

type Decoded = { image: CanvasImageSource; width: number; height: number; close: () => void };

async function decode(file: Blob): Promise<Decoded> {
  if (typeof createImageBitmap === "function") {
    try {
      const b = await createImageBitmap(file, { imageOrientation: "from-image" });
      return { image: b, width: b.width, height: b.height, close: () => b.close() };
    } catch {
      // Older browsers: fall through to <img>, which also applies the rotation tag.
    }
  }
  const url = URL.createObjectURL(file);
  try {
    const img = new Image();
    img.src = url;
    await img.decode();
    return { image: img, width: img.naturalWidth, height: img.naturalHeight, close: () => URL.revokeObjectURL(url) };
  } catch (e) {
    URL.revokeObjectURL(url);
    throw e;
  }
}

export async function shrinkPhoto(file: File, maxSide = 1600, quality = 0.85): Promise<Blob> {
  try {
    const src = await decode(file);
    try {
      const { width, height } = src;
      if (!width || !height) return file;
      const k = Math.min(1, maxSide / Math.max(width, height));
      if (k === 1 && file.type === "image/jpeg" && file.size <= 1_500_000) return file;   // already small
      const canvas = document.createElement("canvas");
      canvas.width = Math.max(1, Math.round(width * k));
      canvas.height = Math.max(1, Math.round(height * k));
      const ctx = canvas.getContext("2d");
      if (!ctx) return file;
      ctx.imageSmoothingQuality = "high";
      ctx.drawImage(src.image, 0, 0, canvas.width, canvas.height);
      const blob = await new Promise<Blob | null>((r) => canvas.toBlob(r, "image/jpeg", quality));
      canvas.width = canvas.height = 0;        // free the pixels now (cheap phones have little memory)
      return blob && blob.size > 0 && blob.size < file.size ? blob : file;
    } finally {
      src.close();
    }
  } catch {
    return file;
  }
}
