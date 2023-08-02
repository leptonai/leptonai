from django.db import models
from django.utils.translation import gettext_lazy as _


class BaseModel(models.Model):
    pass


class Dish(BaseModel):
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    data_path = models.CharField(max_length=200)
    model_name_or_path = models.CharField(max_length=200)
    output_dir = models.CharField(max_length=200)

    task_id = models.CharField(max_length=100)

    class Status(models.TextChoices):
        PENDING = "P", _("Pending")
        RUNNING = "R", _("Running")
        CANCELLED = "C", _("Cancelled")
        SUCCESS = "S", _("Success")
        FAILED = "F", _("Failed")

    status = models.CharField(
        max_length=1, choices=Status.choices, default=Status.PENDING
    )

    def start_run(self):
        self.status = Dish.Status.RUNNING
        self.save()

    def cancel(self):
        self.status = Dish.Status.CANCELLED
        self.save()

    def failed(self):
        self.status = Dish.Status.FAILED
        self.save()

    def succeed(self):
        self.status = Dish.Status.SUCCESS
        self.save()

    def is_pending(self):
        return self.status == Dish.Status.PENDING

    def is_running(self):
        return self.status == Dish.Status.RUNNING

    def is_finished(self):
        return self.status in [
            Dish.Status.CANCELLED,
            Dish.Status.SUCCESS,
            Dish.Status.FAILED,
        ]

    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "status": self.status,
            "output_dir": self.output_dir,
        }
