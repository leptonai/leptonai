import uuid

from celery import current_app
from loguru import logger
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.views import View

from .models import Dish
from .tasks import cook
from .utils import json_response, upload_dataset, get_output_dir


class AddView(View):
    @staticmethod
    def get(request):
        html = """
            <form method="post" enctype="multipart/form-data">
              <input type='text' style='display:none;' value='%s' name='csrfmiddlewaretoken'/>
              <label for="data">Data</label>
              <input type="file" name="data" accept=".json">
              <label for="model">Model(base):</label>
              <select id="model" name="model">
                <option value="llama2/7b-chat selected">llama2/7b-chat</option>
                <option value="vicuna/7B">vicuna/7B</option>
                <option value="baichuan">baichuan</option>
              </select>
              <button type="submit">Submit</button>
            </form>
        """ % (get_token(request))
        return HttpResponse(html)

    @staticmethod
    def post(request):
        data = request.FILES["data"]
        logger.info(f"Received data file {data}")

        sesssion_id = uuid.uuid4().hex
        logger.info(f"Using session_id {sesssion_id}")

        data_path = upload_dataset(data.file, id_=sesssion_id)
        logger.info(f"Using data_path {data_path}")

        model_name_or_path = request.POST.get("model", "llama2/7b-chat")
        logger.info(f"Using model {model_name_or_path}")

        output_dir = get_output_dir(id_=sesssion_id)
        logger.info(f"Using output_dir {output_dir}")

        cook_task = cook.delay(
            data_path=data_path,
            model_name_or_path=model_name_or_path,
            output_dir=output_dir,
        )
        dish = Dish.objects.create(
            data_path=data_path,
            model_name_or_path=model_name_or_path,
            output_dir=output_dir,
            task_id=cook_task.id,
        )
        dish.save()
        return json_response(dish)


def get_dish(request, dish_id):
    logger.info(f"Getting dish with id {dish_id}")
    dish = Dish.objects.get(id=dish_id)
    return json_response(dish)


def cancel_dish(request, dish_id):
    logger.info(f"Canceling dish with id {dish_id}")
    dish = Dish.objects.get(id=dish_id)
    if dish.is_finished:
        logger.info(
            f"Trying to cancel dish with id {dish_id} but it is already finished"
        )
        return json_response(dish)
    task_id = dish.task_id
    logger.info(f"Revoking celery task with task_id {task_id}")
    current_app.control.revoke(task_id, terminate=True)
    logger.info(f"Revoked celery task with task_id {task_id}")
    dish.cancel()
    return json_response(dish)


def list_dishes(request, status=None):
    logger.info(f"Listing dishes with status {status}")
    if status is None:
        dishes = Dish.objects.all()
    else:
        dishes = Dish.objects.filter(status=status)
    return json_response(list(dishes))
