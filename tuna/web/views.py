import uuid

from celery import current_app
from loguru import logger
from django.http import HttpResponse, HttpResponseBadRequest
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
                <option value="llama2/7b-chat" selected>llama2/7b-chat</option>
                <option value="vicuna/7B">vicuna/7B</option>
                <option value="vicuna/7B_v1.3">vicuna/7B_v1.3</option>
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
    if dish.is_finished():
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


class RerunView(View):
    @staticmethod
    def get(request):
        html = """
            <form method="post" enctype="multipart/form-data">
              <input type='text' style='display:none;' value='%s' name='csrfmiddlewaretoken'/>
              <label for="dish_id">Dish Id</label>
              <input type="number" id="dish_id", name="dish_id">
              <label for="task_id">Task Id</label>
              <input type="text" id="task_id", name="task_id">
              <button type="submit">Run Again</button>
            </form>
        """ % (get_token(request))
        return HttpResponse(html)

    @staticmethod
    def post(request):
        dish_id = request.POST.get("dish_id")
        task_id = request.POST.get("task_id")
        logger.info(f"Received dish_id={dish_id} and task_id={task_id}")
        if not dish_id and not task_id:
            return HttpResponseBadRequest("dish_id or task_id must be provided")

        if dish_id:
            try:
                dish = Dish.objects.get(id=dish_id)
            except Dish.DoesNotExist:
                logger.error(f"Dish with id {dish_id} does not exist")
                return HttpResponseBadRequest(f"Dish with id {dish_id} does not exist")
        else:
            logger.info(f"Finding dish_id for task_id={task_id}")
            try:
                dish = Dish.objects.get(task_id=task_id)
            except Dish.DoesNotExist:
                logger.error(f"Dish with task_id={task_id} does not exist")
                return HttpResponseBadRequest(
                    f"Dish with task_id={task_id} does not exist"
                )

        logger.info(
            f"Requested to re-cook a previous dish_id={dish.id} (status={dish.status})"
        )
        if not dish.is_finished:
            logger.error(f"Dish with id {dish.id} is not finished")
            return HttpResponseBadRequest(f"Dish with id {dish.id} is not finished")

        data_path = dish.data_path
        logger.info(f"Previous data_path={data_path}")
        model_name_or_path = dish.model_name_or_path
        logger.info(f"Previous model_name_or_path={model_name_or_path}")
        output_dir = dish.output_dir
        logger.info(f"Previous output_dir={output_dir}")

        new_task = cook.delay(
            data_path=data_path,
            model_name_or_path=model_name_or_path,
            output_dir=output_dir,
        )
        logger.info(f"Re-cook dish with task_id={new_task.id}")
        dish.task_id = new_task.id
        dish.save()
        logger.info("Updated dish with new task_id")
        return json_response(dish)
