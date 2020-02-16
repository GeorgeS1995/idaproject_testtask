from django.http import HttpResponse
from django.views.generic import ListView, FormView, View
from .models import Image
from .forms import ImageForm
from imagekit import ImageSpec
from io import BytesIO
from imagekit.processors import Resize
import magic
import logging
from django.shortcuts import render

lh = logging.getLogger('django')


# Create your views here.

class ImageList(ListView):
    paginate_by = 20
    model = Image
    template_name = "index.html"


def resize(img, width, height, size):
    def check_border(image, border, maxQ):
        image = ImageSpec(source=image)
        image.options = {'quality': border, 'optimize': True}
        image = image.generate()
        file_size = image.getbuffer().nbytes
        used_borders.add(border)
        result = file_size > int(size)
        if not result and maxQ < border:
            nonlocal max_in_size_quality
            max_in_size_quality = border
            nonlocal max_in_size_quality_img
            max_in_size_quality_img = image
        return result

    if width is None:
        width = img.width
    if height is None:
        height = img.height
    img = ImageSpec(source=img)
    img.processors = [Resize(int(width), int(height))]
    img.format = 'JPEG'
    img = img.generate()
    f_size = img.getbuffer().nbytes
    if size is not None and f_size > int(size):
        quality = 80
        upper_border = quality
        lower_border = quality // 2
        lower_from_last_iter = 0
        used_borders = set()
        max_in_size_quality = 0
        max_in_size_quality_img = BytesIO()
        for i in range(5):
            if lower_border not in used_borders:
                if check_border(img, lower_border, max_in_size_quality):
                    upper_border = lower_border
                    lower_border = (lower_border - lower_from_last_iter) // 2
                else:
                    lower_border = lower_border + (upper_border - lower_border) // 2
            if upper_border not in used_borders and check_border(img, upper_border, max_in_size_quality):
                upper_border = lower_border + (upper_border - lower_border) // 2
            lower_from_last_iter = lower_border
        if max_in_size_quality == 0:
            raise ValueError
        img = max_in_size_quality_img
    return img


class ImageDetail(View):
    http_method_names = ['get']

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() not in self.http_method_names:
            return self.http_method_not_allowed
        img = Image.objects.get(img_hash=kwargs['img_hash'])
        width = request.GET.get('width')
        height = request.GET.get('height')
        size = request.GET.get('size')
        try:
            img = resize(img.photo, width, height, size)
        except ValueError:
            lh.error('To big image compression')
            return render(request, template_name='error_resize.html')
        f_type = magic.from_buffer(img.read(2048), mime=True)
        img.seek(0)
        return HttpResponse(img.read(), f_type)


class ImageUploadView(FormView):
    form_class = ImageForm
    template_name = "img_upload_form.html"
    success_url = '/'

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)
