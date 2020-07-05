from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_POST
from django.views.decorators.cache import cache_page

from .models import Post, Group, Follow
from .forms import PostForm, CommentForm


User = get_user_model()


def page_not_found(request, exception):
    """
    Display a page for 404 Not Found status code.
    """
    return render(request, 'misc/404.html', {'path': request.path}, status=404)


def server_error(request):
    """
    Display a page for 500 Internal Server Error status code.
    """
    return render(request, 'misc/500.html', status=500)


@cache_page(20, key_prefix='index_page')
def index(request):
    """
    Display most recent :model:`posts.Post`, 10 per page.

    **Context**

    ``page``
        A list of 10 :model:`posts.Post`.
    ``paginator``
        A Paginator object.

    **Template**

    :template:`index.html`
    """
    posts = Post.objects.all().select_related('author')
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)

    return render(
        request, 
        'index.html', 
        {
            'page': page,
            'paginator': paginator
        }
    )


def group_posts(request, slug):
    """
    Display most recent :model:`posts.Post` 
    of a given :model:`posts.Group`, 10 per page.

    **Context**

    ``group``
        An instance of :model:`posts.Group`.
    ``page``
        A list of 10 :model:`posts.Post`.
    ``paginator``
        A Paginator object.

    **Template**

    :template:`group.html`
    """
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all().select_related('author')

    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)

    context = {
            'group': group, 
            'page': page,
            'paginator': paginator,
    }

    return render(request, 'group.html', context)


@login_required
def new_post(request):
    """
    GET: Display a form for a new :model:`posts.Post`.
    
    POST: Validate and save the form to database.
    On successful save redirect to :view:`posts.index`,
    otherwise stay on page and show validation errors.

    **Context**

    ``form``
        An instance of `posts.PostForm`

    **Templates**

    :template:`posts/new_post.html`
    """
    form = PostForm(request.POST or None, files=request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect(reverse('index'))
        
    return render(request, 'posts/new_post.html', {'form': form})


def profile(request, username):
    """
    Display page of a given :model:`posts.User`, and
    all of their :model:`posts.Post`, 10 per page.

    **Context**

    ``author``
        An instance of :model:`posts.User`.
    ``page``
        A list of 10 :model:`posts.Post`.
    ``paginator``
        A Paginator object.
    ``following``
        A flag that checks whether the user follows the author.

    **Template**

    :template:`profile/profile.html`
    """
    
    author = get_object_or_404(User, username=username)
    author_posts = author.posts.all()

    following = not request.user.is_anonymous and Follow.objects.filter(
        user=request.user, author=author
    ).exists()

    paginator = Paginator(author_posts, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)

    context = {
            'author': author, 
            'page': page,
            'paginator': paginator,
            'following': following
    }

    return render(request, 'profile/profile.html', context)


def post_view(request, username, post_id):
    """
    Display a single :model:`posts.Post`, of given :model:`posts.User`
    with all of the posts :model:`posts.Comment`s.

    **Context**

    ``author``
        An instance of :model:`posts.User`.
    ``post``
        An instance of :model:`posts.Post`.
    ``comments``
        A list of :model:`posts.Comment` of this post.
    ``form``
        A form to post a comment for this post.

    **Template**

    :template:`post.html`
    """
    author = get_object_or_404(User, username=username)
    post = get_object_or_404(
        Post, 
        id=post_id, 
        author=author)
    comments = post.comments.select_related('author')
    form = CommentForm(request.POST or None)

    context = {
        'author': author,
        'post': post,
        'comments': comments,
        'form': form
    }

    return render(request, 'posts/post.html', context)


@login_required
def post_edit(request, username, post_id):
    """
    GET: Display a form to edit an instance of :model:`posts.Post`.
    If post author doesn't match the current user,
    redirect to :view:`posts.post_view`.
    
    POST: Validate and update the post.
    On successful save redirect to :view:`posts.post_view`,
    otherwise stay on page and show validation errors.

    **Context**

    ``form``
        An instance of `posts.PostForm`

    **Templates**

    :template:`posts/edit_post.html`
    """
    author = get_object_or_404(User, username=username)

    if request.user != author:
        return redirect('post', username=username, post_id=post_id)
    
    post = get_object_or_404(Post, id=post_id, author=author)

    form = PostForm(
        request.POST or None, 
        files=request.FILES or None, 
        instance=post
    )

    if form.is_valid():
        form.save()
        return redirect('post', username=username, post_id=post_id)

    return render(request, 'posts/new_post.html', {'form': form, 'post': post})


@login_required
@require_POST
def add_comment(request, username, post_id):
    """
    Create a :model:`posts.Comment` for a given :model:`posts.Post` 
    and redirect to :view:`posts.post_view` of this post.
    Only POST method is allowed.
    """
    form = CommentForm(request.POST)
    post = get_object_or_404(Post, id=post_id, author__username=username)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()

    return redirect('post', username=username, post_id=post_id)


@login_required
def follow_index(request):
    """
    Display most recent :model:`posts.Post` of all authors the user follows,
    10 per page.

    **Context**

    ``page``
        A list of 10 :model:`posts.Post`.
    ``paginator``
        A Paginator object.

    **Template**

    :template:`posts/follow.html`
    """
    posts = Post.objects.filter(
        author__following__user=request.user
    ).select_related('author')

    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)

    return render(
        request, 
        'posts/follow.html', 
        {
            'page': page,
            'paginator': paginator,
        }
    )


@login_required
def profile_follow(request, username):
    """
    Handle a follow request from user to author.
    A user can not follow themselves and can not follow the same author twice.
    """
    author = get_object_or_404(User, username=username)

    if request.user != author:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect('profile', username=username)


@login_required
def profile_unfollow(request, username):
    """
    Handle an unfollow request from user to author.
    """
    author = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user, author=author).delete()

    return redirect('profile', username=username)
