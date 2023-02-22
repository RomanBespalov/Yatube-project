from http import HTTPStatus

import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.paginator import Page
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Group, Post, User, Follow
from posts.tests import constants as cs
from posts.forms import PostForm

POSTS_PER_PAGE = 10
POSTS_SECOND_PAGE = 1

PAG_INDEX_URL = reverse('posts:index')
PAG_GROUP_LIST_URL = reverse('posts:group_list', args=[cs.GROUP_SLUG])
PAG_PROFILE_URL = reverse('posts:profile', args=[cs.AUTHOR_NAME])

POST_TEXT_OLD = 'First check'
POST_TEXT_NEW = 'Second check'
POST_USER = 'author_2'

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username=cs.AUTHOR_NAME)
        cls.user = User.objects.create_user(username=cs.USER_NAME)
        cls.group = Group.objects.create(
            title=cs.GROUP_TITLE,
            slug=cs.GROUP_SLUG,
            description=cs.GROUP_DESCRIPTION,
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text=cs.POST_TEXT,
            group=cls.group,
            image=SimpleUploadedFile(
                name=cs.IMAGE_NAME,
                content=cs.SMALL_GIF,
                content_type='image/gif',
            ),
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(self.author)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)
        self.guest_client = Client()

    def test_post_create_page_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.author_client.get(reverse(cs.POST_CREATE_URL))
        self.assertIsInstance(response.context.get('form'), PostForm)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = (self.author_client.get(
            reverse(cs.POST_DETAIL_URL, kwargs={'post_id': self.post.id}))
        )
        self.assertEqual(response.context.get('post').text, self.post.text)
        self.assertEqual(
            response.context.get('post').author, self.post.author
        )
        self.assertEqual(
            response.context.get('post').group, self.post.group
        )
        self.assertEqual(
            response.context.get('post').image, self.post.image
        )

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(cs.PROFILE_URL, kwargs={'username': self.author})
        )
        self.assertEqual(response.context['author'], self.author)
        self.assertEqual(response.context['page_obj'][0].text, self.post.text)
        self.assertEqual(response.context['page_obj'][0].author, self.author)
        self.assertEqual(response.context['page_obj'][0].group, self.group)
        self.assertEqual(
            response.context['page_obj'][0].image, self.post.image
        )

    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.author_client.get(
            reverse(cs.GROUP_URL, kwargs={'slug': self.group.slug})
        )
        self.assertEqual(
            response.context['page_obj'][0].group.title, self.group.title
        )
        self.assertEqual(
            response.context['page_obj'][0].group.description,
            self.group.description
        )
        self.assertEqual(response.context['page_obj'][0].group, self.group)
        self.assertEqual(response.context['page_obj'][0].text, self.post.text)
        self.assertEqual(response.context['page_obj'][0].author, self.author)
        self.assertEqual(
            response.context['page_obj'][0].image, self.post.image
        )

    def test_check_work_cache(self):
        """Проверка работы кэша на главной странице."""
        response_1 = self.guest_client.get(reverse(cs.INDEX_URL))
        Post.objects.create(
            author=self.author,
            text='Test post',
        )
        response_2 = self.guest_client.get(reverse(cs.INDEX_URL))
        self.assertEqual(response_1.content, response_2.content)
        cache.clear()
        response_3 = self.guest_client.get(reverse(cs.INDEX_URL))
        self.assertNotEqual(response_1.content, response_3.content)

    def test_create_picture_post(self):
        """Проверка, что картинка существует на страницах."""
        self.author_client.post(
            reverse(cs.POST_CREATE_URL)
        )
        post = Post.objects.get(pk=self.post.id)
        self.assertEqual(post.image, cs.IMAGE_FOLDER + cs.IMAGE_NAME)
        cache.clear()
        response_1 = self.author_client.get(reverse(cs.INDEX_URL))
        first_object = response_1.context['page_obj'].object_list[0].image
        self.assertEqual(first_object, cs.IMAGE_FOLDER + cs.IMAGE_NAME)

        response_2 = self.author_client.get(
            reverse(cs.PROFILE_URL, kwargs={'username': self.author})
        )
        second_object = response_2.context['page_obj'].object_list[0].image
        self.assertEqual(second_object, cs.IMAGE_FOLDER + cs.IMAGE_NAME)

        response_3 = self.author_client.get(
            reverse(cs.GROUP_URL, kwargs={'slug': self.group.slug})
        )
        third_object = response_3.context['page_obj'].object_list[0].image
        self.assertEqual(third_object, cs.IMAGE_FOLDER + cs.IMAGE_NAME)

        response_4 = self.author_client.get(
            reverse(cs.POST_DETAIL_URL, kwargs={'post_id': self.post.id})
        )
        fourth_object = response_4.context.get('post').image
        self.assertEqual(fourth_object, cs.IMAGE_FOLDER + cs.IMAGE_NAME)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username=cs.AUTHOR_NAME)
        cls.user = User.objects.create_user(username=cs.USER_NAME)
        cls.group = Group.objects.create(
            title=cs.GROUP_TITLE,
            slug=cs.GROUP_SLUG,
            description=cs.GROUP_DESCRIPTION,
        )
        Post.objects.bulk_create([
            Post(
                text=f'{cs.POST_TEXT} {i}', author=cls.author, group=cls.group
            ) for i in range(POSTS_PER_PAGE + POSTS_SECOND_PAGE)
        ])

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(self.user)

    def test_paginator(self):
        '''Проверка работы Пагинатора'''
        mount_of_posts_on_the_first_page = POSTS_PER_PAGE
        mount_of_posts_on_the_second_page = POSTS_SECOND_PAGE

        pages = (
            (1, mount_of_posts_on_the_first_page),
            (2, mount_of_posts_on_the_second_page),
        )

        urls_expected_post_number = (
            PAG_INDEX_URL,
            PAG_GROUP_LIST_URL,
            PAG_PROFILE_URL,
        )

        for url in urls_expected_post_number:
            for page, mount in pages:
                with self.subTest(url=url, page=page):
                    response = self.author_client.get(url, {'page': page})
                    page_obj = response.context.get('page_obj')
                    self.assertEqual(response.status_code, HTTPStatus.OK)
                    self.assertIsNotNone(page_obj)
                    self.assertIsInstance(page_obj, Page)
                    self.assertEqual(len(page_obj.object_list), mount)


class ProfileFollowTest(TestCase):
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

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_authorized_client_profile_follow_unfollow(self):
        """Авторизованный пользователь может подписываться
        на других пользователей и удалять их из подписок.
        Новая запись пользователя появляется в ленте тех,
        кто на него подписан и не появляется в ленте тех, кто не подписан."""
        response = self.authorized_client.get(
            reverse('posts:profile_follow', kwargs={'username': self.author})
        )
        self.assertRedirects(response, reverse('posts:follow_index'))
        subscriptions = Follow.objects.filter(user=self.user)
        author = [subscription.author for subscription in subscriptions]
        self.assertEqual(author, [self.author])
        response_1 = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertEqual(
            response_1.context.get('page_obj').object_list[0].text,
            cs.POST_TEXT
        )

        follow = Follow.objects.get(user=self.user, author=self.author)
        follow.delete()
        assert follow not in Follow.objects.filter(user=self.user)
        response_2 = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertNotIn(
            cs.POST_TEXT, response_2.context.get('page_obj').object_list
        )
