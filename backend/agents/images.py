"""Banners for persona-posted openings: OpenAI's cheapest image model at low
quality, resized to a small JPEG (images live in Cassandra rows until object
storage arrives, and big blobs are what stalled the driver)."""
import base64
import io

from PIL import Image

from agents import config

STYLE = ('Warm, natural light; a lived-in solarpunk neighbourhood with plants, tools and handmade things. '
         'No people, no faces, no hands. No text, letters, numbers, signs or logos anywhere in the picture.')
MAX_SIZE = (1280, 720)


def shrink(raw, max_size=MAX_SIZE, quality=80):
    """Any image bytes -> a progressive JPEG no larger than max_size."""
    img = Image.open(io.BytesIO(raw)).convert('RGB')
    img.thumbnail(max_size)
    out = io.BytesIO()
    img.save(out, 'JPEG', quality=quality, optimize=True, progressive=True)
    return out.getvalue()


class Illustrator:
    def __init__(self, client=None, model=None):
        if client is None:
            from openai import OpenAI
            client = OpenAI()
        self.client = client
        self.model = model or config.IMAGE_MODEL

    def banner(self, subject):
        """A landscape banner of `subject` (an opening's title and gist)."""
        result = self.client.images.generate(
            model=self.model,
            prompt=f'A banner for a community noticeboard post: {subject}. {STYLE}',
            size='1536x1024',
            quality='low',
            output_format='jpeg',
            output_compression=80,
            n=1,
        )
        return shrink(base64.b64decode(result.data[0].b64_json))
