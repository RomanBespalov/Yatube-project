import shutil
import tempfile

from http import HTTPStatus

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.forms import PostForm
from posts.models import Comment, Group, Post, User
from posts.tests import constants as cs

POST_TEXT_OLD = 'First check'
POST_TEXT_NEW = 'Second check'

COMMENT_TEXT_1 = 'Новый комментарий'
COMMENT_TEXT_2 = 'Комментарий которого нет'

ADD_COMMENT_URL = 'posts:add_comment'

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username=cs.AUTHOR_NAME)
        cls.user = User.objects.create_user(username=cs.USER_NAME)
        cls.post = Post.objects.create(
            author=cls.author,
            text=cs.POST_TEXT,
        )
        cls.group = Group.objects.create(
            title=cs.GROUP_TITLE,
            slug=cs.GROUP_SLUG,
            description=cs.GROUP_DESCRIPTION,
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.author_client = Client()
        self.author_client.force_login(self.author)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Валидная форма создает пост в Post."""
        posts_count = Post.objects.count()
        uploaded = SimpleUploadedFile(
            name=cs.IMAGE_NAME,
            content=cs.SMALL_GIF,
            content_type='image/gif'
        )
        form_data = {
            'text': POST_TEXT_OLD,
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.author_client.post(
            reverse(cs.POST_CREATE_URL),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response, reverse(
                cs.PROFILE_URL, kwargs={'username': self.post.author.username}
            )
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.text, POST_TEXT_OLD)
        self.assertEqual(first_object.group, self.group)
        self.assertEqual(first_object.author, self.author)
        self.assertEqual(first_object.image, cs.IMAGE_FOLDER + cs.IMAGE_NAME)

    def test_edit_post(self):
        """Валидная форма редактирует пост в Post."""
        form_data = {
            'text': POST_TEXT_NEW,
            'group': self.group.id,
        }
        response = self.author_client.post(
            reverse(cs.POST_EDIT_URL, kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        update_object = response.context['post']
        self.assertEqual(update_object.text, POST_TEXT_NEW)
        self.assertEqual(update_object.group, self.group)
        self.assertEqual(update_object.author, self.author)

    def test_make_comment_authorized_client(self):
        '''Комментировать посты может только авторизованный пользователь,
        После успешной отправки комментарий появляется на странице поста'''
        form_data = {
            'text': COMMENT_TEXT_1,
        }
        self.authorized_client.post(
            reverse(ADD_COMMENT_URL, kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True,
        )
        self.assertTrue(Comment.objects.filter(
            text=COMMENT_TEXT_1,
        ).exists())

    def test_make_comment_guest_client(self):
        '''Анонимный пользователь не может создать комментарий.'''
        form_data_2 = {
            'text': COMMENT_TEXT_2,
        }
        self.guest_client.post(
            reverse(ADD_COMMENT_URL, kwargs={'post_id': self.post.id}),
            data=form_data_2,
            follow=True,
        )
        self.assertFalse(Comment.objects.filter(
            text=COMMENT_TEXT_2,
        ).exists())
