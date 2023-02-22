from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page

from .forms import CommentForm, PostForm
from .models import Group, Post, User, Follow
from .utils import pagination


@cache_page(20)
def index(request):
    context = {
        'page_obj': pagination(
            request,
            Post.objects.select_related('author', 'group').all()
        ),
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    context = {
        'page_obj': pagination(request, group.posts.all()),
        'group': group,
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts_profile_list = Post.objects.filter(author=author)
    page_obj = pagination(request, posts_profile_list)
    context = {
        'page_obj': page_obj,
        'author': author,
        'following': (request.user.is_authenticated
                      and request.user != username
                      and Follow.objects.filter(
                          user=request.user, author=author
                      ).exists()),
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    template = 'posts/post_detail.html'
    post = Post.objects.get(id=post_id)
    form = CommentForm()
    context = {
        'post': post,
        'form': form,
    }
    return render(request, template, context)


@login_required
def post_create(request):
    template = 'posts/create_post.html'
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
    )
    if not form.is_valid():
        return render(request, template, {'form': form})
    post = form.save(commit=False)
    post.author = request.user
    post.save()
    return redirect('posts:profile', request.user)


@login_required
def post_edit(request, post_id):
    template = 'posts/create_post.html'
    post = Post.objects.get(pk=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post,
    )
    if request.user != post.author:
        return redirect('posts:post_detail', post_id)
    if request.user == post.author:
        if request.method == 'POST':
            form.save()
            return redirect('posts:post_detail', post_id)
        context = {
            'form': form,
            'is_edit': True,
            'post': post,
        }
    return render(request, template, context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    subscriptions = Follow.objects.filter(user=request.user)
    authors = [subscription.author for subscription in subscriptions]
    posts = Post.objects.filter(author__in=authors)
    page_obj = pagination(request, posts)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    # Подписаться на автора
    author = get_object_or_404(User, username=username)
    if request.user != author:
        Follow.objects.get_or_create(user=request.user, author=author)
        return redirect('posts:follow_index')
    return redirect('posts:index')


@login_required
def profile_unfollow(request, username):
    # Дизлайк, отписка
    get_object_or_404(
        Follow, user=request.user, author__username=username
    ).delete()
    return redirect('posts:follow_index')
