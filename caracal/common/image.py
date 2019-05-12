
from io import BytesIO
from PIL import Image, ImageOps


def get_image_bufer(image):
    buffer = BytesIO()
    image.save(buffer, 'PNG')
    buffer.seek(0)
    return buffer


def get_rgba_image(obj_body):
    image = Image.open(BytesIO(obj_body))
    if image.format.lower() in ['jpg', 'jpeg']:
        image = image.convert('RGBA')
    return image