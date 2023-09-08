from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from . import views

urlpatterns = [
    path("job/add", csrf_exempt(views.AddView.as_view()), name="add"),
    path("job/get/<int:dish_id>", views.get_dish, name="get"),
    path("job/list/<str:status>", views.list_dishes, name="list"),
    path("job/list", views.list_dishes, name="list"),
    path("job/cancel/<int:dish_id>", views.cancel_dish, name="cancel"),
    path("job/rerun", csrf_exempt(views.RerunView.as_view()), name="rerun"),
]
