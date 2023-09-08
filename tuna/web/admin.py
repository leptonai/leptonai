from django.contrib import admin
from django.utils.html import format_html

from .models import Dish


class DishAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status_with_cancel",
        "task_id",
        "output_dir",
        "model_name_or_path",
        "data_path",
    )
    list_filter = ("status",)
    search_fields = (
        "id",
        "status",
        "task_id",
        "output_dir",
        "model_name_or_path",
        "data_path",
    )
    ordering = ("-id",)

    def status_with_cancel(self, dish):
        if dish.is_finished():
            return dish.get_status_display()
        else:
            return format_html(
                '{}<a class="deletelink" href="/job/cancel/{}"></a>',
                dish.get_status_display(),
                dish.id,
            )

    status_with_cancel.short_description = "status"


admin.site.register(Dish, DishAdmin)
