from flask import jsonify, request, Blueprint
from app.services.firebase import (
    add_schedule_firebase,
    delete_schedule_firebase,
    change_cycle_schedule_firebase,
    set_on_off_schedule_firebase,
    get_schedule_firebase,
    set_daily_schedule_firebase
)
from app.services.firestore import create_schedule, send_schedule_raspi

schedule_route = Blueprint("schedule", __name__)

@schedule_route.route("/add_schedule/<int:aquarium_id>", methods=["POST"])
def add_schedule(aquarium_id):
    """
    Add a new feeding schedule for the given aquarium.

    Expects JSON payload with:
      - time (str): Feeding time in HH:MM format
      - cycle (int): Amount or cycle number for feeding
      - switch (bool): Whether the schedule is enabled or not
      - food (str) : what type of food? pellet or flakes
      - daily (bool) : Wether the scheudle is daily or not
 
    Args:
        aquarium_id (int): The ID of the aquarium

    Returns:
        JSON: Result of the add operation (status, time, cycle, switch)
    """
    schedule = request.get_json()  
    result = add_schedule_firebase(aquarium_id, schedule)
    return jsonify(result)  


@schedule_route.route("/delete_schedule/<int:aquarium_id>/<string:time>", methods=["DELETE"])
def delete_schedule(aquarium_id, time):
    """
    Delete a feeding schedule by time for the given aquarium.

    Args:
        aquarium_id (int): The ID of the aquarium
        time (str): Feeding time in HH:MM format

    Returns:
        JSON: Result of the delete operation (status, time)
    """
    delete = delete_schedule_firebase(aquarium_id, time)
    return jsonify(delete) 


@schedule_route.route("/update_schedule_cycle/<int:aquarium_id>/<string:time>/<int:cycle>", methods=["PATCH"])
def update_cycle(aquarium_id, time, cycle):
    """
    Update the cycle value of a feeding schedule.

    Args:
        aquarium_id (int): The ID of the aquarium
        time (str): Feeding time in HH:MM format
        cycle (int): New cycle value

    Returns:
        JSON: Result of the update (status, time, cycle)
    """
    update = change_cycle_schedule_firebase(aquarium_id, time, cycle)
    return jsonify(update)  


@schedule_route.route("/update_schedule_switch/<int:aquarium_id>/<string:time>/<switch>", methods=["PATCH"])
def update_schedule_switch(aquarium_id, time, switch):
    """
    Update the switch (on/off) value of a feeding schedule.

    Args:
        aquarium_id (int): The ID of the aquarium
        time (str): Feeding time in HH:MM format
        switch (str): Switch state as string ('true', 'false', etc.)

    Returns:
        JSON: Result of the update (status, time, enabled)
    """
    switch_value = switch.lower() in ['true', '1', 't', 'y', 'yes']
    update = set_on_off_schedule_firebase(aquarium_id, switch_value, time)
    return jsonify(update)


@schedule_route.route("/get_schedules/<int:aquarium_id>", methods=["GET"])
def get_schedules(aquarium_id):
    """
    Retrieve all feeding schedules for a given aquarium.

    Args:
        aquarium_id (int): The ID of the aquarium

    Returns:
        JSON: List of schedules with their time, cycle, and switch values
    """
    schedules = get_schedule_firebase(aquarium_id)
    return jsonify(schedules)  

@schedule_route.route("/task/<int:aquarium_id>", methods=["POST"])
def add_task(aquarium_id):
    json_req = request.get_json()
    schedule_time = json_req.get("schedule_time")
    type_food = json_req.get("food")
    job_id = f"{aquarium_id}_schedule_at_{schedule_time}"
    try:

      create_schedule(
          aquarium_id=aquarium_id,
          cycle=json_req["cycle"],
          schedule_time=schedule_time,
          job_id = job_id,
          food=type_food
      )
      send_schedule_raspi(aquarium_id, json_req["cycle"],schedule_time, type_food, job_id)
      return jsonify({"message": "Sucessfully added the schedule"})
    except Exception as e:
      return jsonify({"Error" : e})
    

@schedule_route.route("/task/delete/<int:aquarium_id>", methods=["POST"])
def delete_task(aquarium_id):
    json_req = request.get_json()
    output = delete_schedule_by_time(aquarium_id= aquarium_id, schedule_time= json_req["schedule_time"])

    return jsonify({"message": "Sucessfully remove the schedule"})


