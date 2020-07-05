import tempfile

from PIL import Image

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile

from .models import User, Post, Group, Follow, Comment


DUMMY_CACHE = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}


class TestMisc(TestCase):
    def setUp(self):
        self.client = Client()

    def test_404(self):
        response = self.client.get('/not/found')
        self.assertEqual(response.status_code, 404)

    def test_cache(self):
        user = User.objects.create_user(
            username='pickle',
            email='rick.s@test.com',
            password='fungi123'
        )
        self.client.force_login(user)

        response = self.client.get(reverse('index'))

        self.client.post(reverse('new_post'), {'text': 'cache test'})
        response = self.client.get(reverse('index'))
        self.assertNotContains(response, 'cache test')

        cache.clear()
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'cache test')


class TestPostsUnauthorized(TestCase):
    def setUp(self):
        self.client = Client()
    
    def test_new_redirect(self):
        response = self.client.get(reverse('new_post'))
        self.assertRedirects(response, '/auth/login/?next=/new/')

        response = self.client.post(
            reverse('new_post'),
            data={'group': '', 'text': 'Test123'}
        )
        self.assertRedirects(response, '/auth/login/?next=/new/')
        self.assertEqual(Post.objects.all().count(), 0)

    def test_cant_comment(self):
        someuser = User.objects.create_user(
            username='random',
            email='random@user.net',
            password='nopass',
        )
        post = Post.objects.create(
            text='test target post',
            author=someuser
        )

        response = self.client.post(
            reverse(
                'add_comment',
                kwargs={
                    'username': someuser.username,
                    'post_id': post.id
                }),
                data={'text': 'test comment'}
            )
        self.assertRedirects(
            response,
            f'/auth/login/?next=/{someuser.username}/{post.id}/comment'
        )
        self.assertEqual(Comment.objects.all().count(), 0)


class TestPostsAuthorized(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='pickle',
            email='rick.s@test.com',
            password='fungi123',
        )
        self.client.force_login(self.user)
        self.group = Group.objects.create(
            title='Test Group',
            slug='test-group'
        )

    @override_settings(CACHE=DUMMY_CACHE)
    def _check_pages_content(self, text, author, id, group, image=False):
        links = {
            'index': reverse('index'),
            'profile': reverse('profile', kwargs={'username': author}),
            'post': reverse('post', kwargs={
                'username': author,
                'post_id': id,
            }),
            'group': reverse('group_posts', kwargs={'slug': group.slug}),
        }

        for k,v in links.items():
            cache.clear()
            response = self.client.get(v)

            if image:
                self.assertContains(response, '<img')

            if k == 'post':
                self.assertEqual(response.context['post'].text, text)
                self.assertEqual(response.context['post'].author, author)
            else:
                self.assertEqual(response.context['page'][0].text, text)
                self.assertEqual(response.context['page'][0].author, author)

            if k in ('post', 'profile'):
                self.assertEqual(response.context['author'], author)

            if k == 'group':
                self.assertEqual(response.context['group'], group)

    def _create_image(self):
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            image = Image.new('RGB', (200, 200), 'white')
            image.save(f, 'PNG')
            
        return open(f.name, mode='rb')
    
    def test_profile(self):
        response = self.client.get(reverse(
            'profile',
            kwargs={'username': self.user.username}
            ))
        self.assertEqual(response.status_code, 200)

    def test_post_new(self):
        response = self.client.get(reverse('new_post'))
        self.assertEqual(response.status_code, 200)

        post_data = {
            'group': self.group.id,
            'text': 'Test message',
            'author': self.user,
        }

        response = self.client.post(reverse('new_post'), data=post_data)
        self.assertRedirects(response, reverse('index'))
        self.assertTrue(Post.objects.filter(**post_data).exists())
                
    def test_post_published(self):
        post = Post.objects.create(
            group=self.group,
            text='Test Post',
            author=self.user
        )
        self._check_pages_content(post.text, self.user, post.id, self.group)
    
    def test_post_edit(self):
        post = Post.objects.create(
            group=self.group,
            text='Test Post Edit',
            author=self.user
        )
        url = reverse('post_edit', kwargs={
            'username': post.author,
            'post_id': post.id,
            })

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        new_group = Group.objects.create(
            title='New test group', 
            slug='new-test-group'
        )
        post_data = {
            'group': new_group.id,
            'text': 'edited test message',
        }

        self.client.post(url, data=post_data)
        
        self._check_pages_content(
            id=post.id, 
            author=post.author, 
            group=new_group, 
            text=post_data['text']
        )

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp(), CACHE=DUMMY_CACHE)
    def test_image(self):
        img = self._create_image()
        resp = self.client.post(
            reverse('new_post'),
            data={
                'author': self.user,
                'text': 'post with image',
                'group': self.group.id,
                'image': img
            }
        )

        post = Post.objects.get(
            author=self.user,
            text='post with image',
            group=self.group.id
        )

        self.assertTrue(post.image)
        
        self._check_pages_content(
            post.text,
            self.user, 
            post.pk, 
            self.group, 
            image=True
        )
    
    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_invalid_image(self):
        img = SimpleUploadedFile('test.txt', b'not an image', 'text/plain')
        response = self.client.post(
            reverse('new_post'),
            data={
                'author': self.user,
                'text': 'post with an invalid image',
                'image': img
            },
        )

        error_msg = "Загрузите правильное изображение. Файл, который вы загрузили, поврежден или не является изображением."
        
        self.assertFormError(response, 'form', 'image', error_msg)
        self.assertNotContains(response, '<img')

    def test_follow(self):
        user2 = User.objects.create(
            username='scnd_usr',
            email='scnd@test.com',
            password='pa$$',
        )

        self.client.get(reverse('profile_follow', args=[user2.username]))
        self.assertTrue(
            Follow.objects.filter(user=self.user, author=user2).exists()
        )

    def test_unfollow(self):
        user2 = User.objects.create(
            username='scnd_usr',
            email='scnd@test.com',
            password='pa$$',
        )

        Follow.objects.create(user=self.user, author=user2)

        self.client.get(reverse('profile_unfollow', args=[user2.username]))
        self.assertFalse(
            Follow.objects.filter(user=self.user, author=user2).exists()
        )

    def test_feed_subscribed(self):
        user2 = User.objects.create(
            username='scnd_usr',
            email='scnd@test.com',
            password='pa$$',
        )

        post = Post.objects.create(
            text='Test Post form user2',
            author=user2
        )

        Follow.objects.create(user=self.user, author=user2)

        response_following = self.client.get(reverse('follow_index'))
        self.assertContains(response_following, post.text)

    def test_feed_not_subscribed(self):
        user2 = User.objects.create(
            username='scnd_usr',
            email='scnd@test.com',
            password='pa$$',
        )

        post = Post.objects.create(
            text='Test Post form user2',
            author=user2
        )

        response_not_following = self.client.get(reverse('follow_index'))
        self.assertNotContains(response_not_following, post.text)    
    
    def test_can_comment(self):
        post = Post.objects.create(
            text='Test post text',
            author=self.user
        )

        response = self.client.post(
            reverse(
                'add_comment', 
                kwargs={
                    'username': self.user.username,
                    'post_id': post.id
                }
            ),
            data={'text': 'test comment'}
        )
        
        self.assertRedirects(
            response, 
            reverse(
                'post', 
                kwargs={
                    'username': self.user.username,
                    'post_id': post.id
                }
            )
        )

        self.assertTrue(Comment.objects.filter(
            text='test comment', 
            author=self.user.id, 
            post=post.id).exists()
        )

        resp_comment = self.client.get(
            reverse(
                'post', 
                kwargs={
                    'username': self.user.username,
                    'post_id': post.id
                }
            )
        )

        comment = resp_comment.context['comments'][0]

        self.assertEqual(comment.text, 'test comment')
        self.assertEqual(comment.author, self.user)
        self.assertEqual(comment.post, post)
