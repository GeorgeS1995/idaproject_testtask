from functools import partial
from django import forms
from .models import Image
from hashlib import md5
from io import BytesIO
from django.core.files.images import ImageFile
import requests
import logging
import magic
from django.conf import settings

lh = logging.getLogger('django')


def check_filesize(url):
    try:
        r = requests.head(url)
        r.raise_for_status()
    except requests.exceptions.ReadTimeout:
        lh.error("request read timeout")
        return
    except requests.exceptions.ConnectTimeout:
        lh.error("request connection timeout")
        return
    except requests.exceptions.ConnectionError as err:
        lh.error("connection error: {}".format(err))
        return
    except requests.exceptions.HTTPError as err:
        lh.error("HTTP error. {}".format(err))
        return
    except requests.exceptions as err:
        lh.error("Unhandled error: {}".format(err))
        return
    return int(r.headers["content-length"]) <= settings.MAX_UPLOAD_SIZE


def img_download(url):
    img = BytesIO()
    try:
        r = requests.get(url, stream=True)
        r.raise_for_status()
    except requests.exceptions.ReadTimeout:
        lh.error("request read timeout")
        return
    except requests.exceptions.ConnectTimeout:
        lh.error("request connection timeout")
        return
    except requests.exceptions.ConnectionError as err:
        lh.error("connection error: {}".format(err))
        return
    except requests.exceptions.HTTPError as err:
        lh.error("HTTP error. {}".format(err))
        return
    except requests.exceptions as err:
        lh.error("Unhandled error: {}".format(err))
        return
    for chunk in r.iter_content(chunk_size=4096):
        img.write(chunk)
    img.seek(0)
    f_type = magic.from_buffer(img.read(2048), mime=True)
    if not f_type.startswith('image'):
        lh.error("file is not a picture")
        return
    img = ImageFile(img)
    img.name = url.split("/")[-1]
    return img


class ImageForm(forms.ModelForm):
    url = forms.CharField(label='url upload', required=False, widget=forms.URLInput(attrs={'class': 'form-control'}))
    photo = forms.ImageField(label='rawfile upload', required=False, widget=forms.FileInput(
        attrs={'class': 'form-control-file'}))

    class Meta:
        model = Image
        fields = ["photo"]

    field_order = ["url", "photo"]
    block_size = 65536

    def save(self, commit=True):
        m = super(ImageForm, self).save(commit=False)
        rawfile = self.cleaned_data.get("photo")
        img_hash = self.cleaned_data["hash"]
        m.name = rawfile.name
        m.photo = rawfile
        m.img_hash = img_hash
        if commit:
            m.save()
        return m

    def clean_url(self):
        url = self.cleaned_data['url']
        if url == "" or check_filesize(url):
            return url
        lh.error(f"File size greater than {settings.MAX_UPLOAD_SIZE / (1024 * 1024)} mb")
        raise forms.ValidationError(f"File size greater than {settings.MAX_UPLOAD_SIZE / (1024 * 1024)} mb")

    def clean_photo(self):
        rawfile = self.cleaned_data['photo']
        if rawfile is not None and rawfile.size > settings.MAX_UPLOAD_SIZE:
            lh.error(f"File size greater than {settings.MAX_UPLOAD_SIZE / (1024 * 1024)} mb")
            raise forms.ValidationError(f"File size greater than {settings.MAX_UPLOAD_SIZE / (1024 * 1024)} mb")
        return rawfile

    def clean(self):
        if self._errors:
            return
        url = self.cleaned_data.get("url")
        rawfile = self.cleaned_data.get("photo")
        if (url != "" and rawfile is not None) or (url == "" and rawfile is None):
            msg = "fill in one form field at a time"
            raise forms.ValidationError(msg)
        if url != "":
            rawfile = img_download(url)
            if rawfile is None:
                msg = "Can't download file"
                raise forms.ValidationError(msg)
            self.cleaned_data["photo"] = rawfile
        hasher = md5()
        for buf in iter(partial(rawfile.read, ImageForm.block_size), b''):
            hasher.update(buf)
        hasher = hasher.hexdigest()
        img = Image.objects.filter(img_hash=hasher)
        if img:
            msg = 'The image is already in the database'
            raise forms.ValidationError(msg)
        self.cleaned_data["hash"] = hasher
