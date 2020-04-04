from io import BytesIO
from django.test import TestCase, override_settings
import os
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from .models import Image
from http.server import SimpleHTTPRequestHandler
import socketserver
import threading
from functools import partial
from hashlib import md5
from django.core.files.images import ImageFile
import shutil

# Create your tests here.
test_img_storage_form = os.path.join(settings.BASE_DIR, 'img_form_test')
test_img_storage_view = os.path.join(settings.BASE_DIR, 'img_view_test')
test_sample_storage = os.path.join(settings.BASE_DIR, 'testfiles')


class MyHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=test_sample_storage, **kwargs)


class ThreadedHTTPServer(object):
    handler = MyHandler

    def __init__(self, host, port):
        self.server = socketserver.TCPServer((host, port), self.handler)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True

    def start(self):
        self.server_thread.start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


class ImageUploadTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.testing_server = ThreadedHTTPServer("", 8001)
        cls.testing_server.start()

    def setUp(self) -> None:
        imgfile = open(os.path.join(test_sample_storage, 'testimg.jpg'), 'rb')
        self.testimg = SimpleUploadedFile(imgfile.name, imgfile.read(), content_type="image/jpeg")
        self.url = 'http://127.0.0.1:8001/urlupload.jpg'
        self.not_img_url = 'http://127.0.0.1:8001/menya_nelzya_zagrujat.txt'

    @classmethod
    def tearDownClass(cls):
        cls.testing_server.stop()
        shutil.rmtree(test_img_storage_form)

    @override_settings(MEDIA_ROOT=test_img_storage_form)
    def test_both_field_fill(self):
        resp = self.client.post(reverse('img_upload'), {'url': self.url, 'photo': self.testimg})
        self.assertFormError(resp, 'form', None, 'fill in one form field at a time')

    @override_settings(MEDIA_ROOT=test_img_storage_form)
    def test_rawfile_upload(self):
        resp = self.client.post(reverse('img_upload'), {'photo': self.testimg})
        saved_img = Image.objects.get(id=1)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(saved_img.img_hash, "ec0356b6ba7b427a92c68d274cc6e444")

    @override_settings(MEDIA_ROOT=test_img_storage_form)
    def test_dublicate_upload(self):
        resp = self.client.post(reverse('img_upload'), {'photo': self.testimg})
        self.assertEqual(resp.status_code, 302)
        self.testimg.seek(0)
        resp = self.client.post(reverse('img_upload'), {'photo': self.testimg})
        self.assertFormError(resp, 'form', None, 'The image is already in the database')

    @override_settings(MEDIA_ROOT=test_img_storage_form)
    def test_url_upload(self):
        resp = self.client.post(reverse('img_upload'), {'url': self.url})
        saved_img = Image.objects.get(id=1)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(saved_img.img_hash, "e4718b5266bb4c931d006c16a8e624cf")

    @override_settings(MEDIA_ROOT=test_img_storage_form)
    def test_url_not_picture(self):
        resp = self.client.post(reverse('img_upload'), {'url': self.not_img_url})
        self.assertFormError(resp, 'form', None, "Can't download file")

    @override_settings(MEDIA_ROOT=test_img_storage_form,
                       MAX_UPLOAD_SIZE=20)
    def test_rawfile_max_filesize(self):
        resp = self.client.post(reverse('img_upload'), {'photo': self.testimg})
        self.assertFormError(resp, 'form', 'photo', "File size greater than 1.9073486328125e-05 mb")

    @override_settings(MEDIA_ROOT=test_img_storage_form,
                       MAX_UPLOAD_SIZE=20)
    def test_url_max_filesize(self):
        resp = self.client.post(reverse('img_upload'), {'url': self.url})
        self.assertFormError(resp, 'form', 'url', "File size greater than 1.9073486328125e-05 mb")


class ImageDetailTestCase(TestCase):

    @override_settings(MEDIA_ROOT=test_img_storage_view)
    def setUp(self) -> None:
        block_size = 65536
        imgfile = open(os.path.join(test_sample_storage, 'testimg.jpg'), 'rb')
        testimg = SimpleUploadedFile(imgfile.name, imgfile.read(), content_type="image/jpeg")
        testimg.seek(0)
        hasher = md5()
        for buf in iter(partial(imgfile.read, block_size), b''):
            hasher.update(buf)
        imgfile = ImageFile(testimg)
        self.hasher = hasher.hexdigest()
        self.original_w = imgfile.width
        self.origibal_h = imgfile.height
        img = Image.objects.create(name=testimg.name, photo=testimg, img_hash=self.hasher)
        img.save()

        self.list_resize = [{"width": 100, "height": 100},
                            {"width": 10, "height": 100},
                            {"width": 100, "height": 10},
                            {"width": 7680, "height": 4320},
                            {"size": 500000},
                            {"width": 100, "height": 100, "size": 500000},
                            {"width": 100, "height": 100, "size": 200000}, ]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(test_img_storage_view)

    @override_settings(MEDIA_ROOT=test_img_storage_view)
    def test_image_resize_err(self):
        resp = self.client.get(reverse('image', args=(self.hasher,)), {'size': 10})
        self.assertNotEqual(resp._container[0].decode().find("To big image compression."), -1)

    @override_settings(MEDIA_ROOT=test_img_storage_view)
    def test_image_resize_file_does_not_exist(self):
        resp = self.client.get(reverse('image', args=("111111",)), {'size': 10})
        self.assertNotEqual(resp._container[0].decode().find("Cant' find image."), -1)

    @override_settings(MEDIA_ROOT=test_img_storage_view)
    def test_image_view(self):
        resp = self.client.get(reverse('image', args=(self.hasher,)))
        down_img = BytesIO(resp.content)
        down_img = ImageFile(down_img)
        self.assertEqual(down_img.width, self.original_w)
        self.assertEqual(down_img.height, self.origibal_h)

    @override_settings(MEDIA_ROOT=test_img_storage_view)
    def test_image_view_resize(self):
        for p in self.list_resize:
            resp = self.client.get(reverse('image', args=(self.hasher,)), p)
            down_img = BytesIO(resp.content)
            down_img = ImageFile(down_img)
            if p.get("width"):
                self.assertEqual(down_img.width, p["width"])
            if p.get("height"):
                self.assertEqual(down_img.height, p["height"])
            if p.get("size"):
                self.assertGreaterEqual(p["size"], down_img.size)
