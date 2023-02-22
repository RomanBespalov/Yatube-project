from django.core.paginator import Paginator


def pagination(request, posts_data, posts_per_page=10):
    paginator = Paginator(posts_data, posts_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
