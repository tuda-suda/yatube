from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Post(models.Model):
    """
    Stores a single Post entry, related to :model:`posts.Group` and
    :model:`auth.User`.
    """
    text = models.TextField()
    pub_date = models.DateTimeField('date published', auto_now_add=True)
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='posts'
    )
    group = models.ForeignKey(
        'Group',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='posts'
    )
    image = models.ImageField(upload_to='posts/', blank=True, null=True)

    class Meta:
        ordering = ['-pub_date']


class Group(models.Model):
    """
    Stores a single Group entry.
    """
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()

    def __str__(self):
        return self.title


class Comment(models.Model):
    """
    Stores a single comment entry of :model:`posts.Post`.
    Related to :model:`post.Post` and :model:`auth.User`.
    """
    post = models.ForeignKey(
        Post, 
        on_delete=models.CASCADE, 
        related_name='comments'
    )
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='comments'
    )
    text = models.TextField()
    created = models.DateTimeField('date created', auto_now_add=True)

    class Meta:
        ordering = ['-created']


class Follow(models.Model):
    """
    Stores a follow realation between two :model:`auth.User`.
    user follows author.
    """
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='follower'
    )
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='following'
    )

    class Meta:
        unique_together = ('user', 'author')
