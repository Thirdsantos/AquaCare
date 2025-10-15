from flask import jsonify, request, Blueprint
import logging
from app.services.firebase import (
    add_schedule_firebase,
    delete_schedule_firebase,
    change_cycle_schedule_firebase,
    set_on_off_schedule_firebase,
    get_schedule_firebase,
    set_daily_schedule_firebase
)
from app.services.firestore import (
    create_schedule,
    send_schedule_raspi,
    delete_schedule_by_id,
    set_complete_task
)

schedule_route = Blueprint("schedule", __name__)
logger = logging.getLogger(__name__)




@schedule_route.route("/add_schedule/<int:aquarium_id>", methods=["POST"])
def add_schedule(aquarium_id):
    """
    Add a new feeding schedule for the given aquarium.

    JSON Body:
        - time (str): Feeding time in HH:MM format
        - cycle (int): Feeding cycle or quantity
        - switch (bool): Whether the schedule is enabled
        - food (str): Type of food (e.g., "pellets", "flakes")
        - daily (bool): Whether the schedule repeats daily

    Args:
        aquarium_id (int): The ID of the aquarium.

    Returns:
        JSON: Result of the add operation (status, message, or error)
    """
    try:
        schedule_data = request.get_json()
        result = add_schedule_firebase(aquarium_id, schedule_data)
        logger.info(f"Added new feeding schedule for Aquarium ID {aquarium_id}: {schedule_data}")
        return jsonify(result), 200
    except Exception as e:
        logger.exception(f"Failed to add feeding schedule for Aquarium ID {aquarium_id}")
        return jsonify({"error": str(e)}), 500


@schedule_route.route("/delete_schedule/<int:aquarium_id>/<string:time>", methods=["DELETE"])
def delete_schedule(aquarium_id, time):
    """
    Delete a feeding schedule by time for a given aquarium.

    Args:
        aquarium_id (int): The ID of the aquarium.
        time (str): Feeding time in HH:MM format.

    Returns:
        JSON: Result of the delete operation (status, message, or error)
    """
    try:
        result = delete_schedule_firebase(aquarium_id, time)
        logger.info(f"Deleted feeding schedule for Aquarium ID {aquarium_id} at {time}")
        return jsonify(result), 200
    except Exception as e:
        logger.exception(f"Failed to delete schedule for Aquarium ID {aquarium_id} at {time}")
        return jsonify({"error": str(e)}), 500


@schedule_route.route("/update_schedule_cycle/<int:aquarium_id>/<string:time>/<int:cycle>", methods=["PATCH"])
def update_cycle(aquarium_id, time, cycle):
    """
    Update the cycle value of a feeding schedule.

    Args:
        aquarium_id (int): The ID of the aquarium.
        time (str): Feeding time in HH:MM format.
        cycle (int): New feeding cycle value.

    Returns:
        JSON: Result of the update (status, message, or error)
    """
    try:
        result = change_cycle_schedule_firebase(aquarium_id, time, cycle)
        logger.info(f"Updated feeding cycle for Aquarium ID {aquarium_id} at {time} to {cycle}")
        return jsonify(result), 200
    except Exception as e:
        logger.exception(f"Failed to update feeding cycle for Aquarium ID {aquarium_id}")
        return jsonify({"error": str(e)}), 500


@schedule_route.route("/update_schedule_switch/<int:aquarium_id>/<string:time>/<switch>", methods=["PATCH"])
def update_schedule_switch(aquarium_id, time, switch):
    """
    Update the on/off switch state of a feeding schedule.

    Args:
        aquarium_id (int): The ID of the aquarium.
        time (str): Feeding time in HH:MM format.
        switch (str): Switch state as string ('true', 'false', etc.)

    Returns:
        JSON: Result of the update (status, message, or error)
    """
    try:
        switch_value = switch.lower() in ['true', '1', 't', 'y', 'yes']
        result = set_on_off_schedule_firebase(aquarium_id, switch_value, time)
        logger.info(f"Updated switch for Aquarium ID {aquarium_id} at {time} to {switch_value}")
        return jsonify(result), 200
    except Exception as e:
        logger.exception(f"Failed to update schedule switch for Aquarium ID {aquarium_id}")
        return jsonify({"error": str(e)}), 500


@schedule_route.route("/get_schedules/<int:aquarium_id>", methods=["GET"])
def get_schedules(aquarium_id):
    """
    Retrieve all feeding schedules for a given aquarium.

    Args:
        aquarium_id (int): The ID of the aquarium.

    Returns:
        JSON: List of schedules or error message.
    """
    try:
        schedules = get_schedule_firebase(aquarium_id)
        logger.debug(f"Retrieved schedules for Aquarium ID {aquarium_id}")
        return jsonify(schedules), 200
    except Exception as e:
        logger.exception(f"Failed to retrieve schedules for Aquarium ID {aquarium_id}")
        return jsonify({"error": str(e)}), 500



@schedule_route.route("/task/<int:aquarium_id>", methods=["POST"])
def add_task(aquarium_id):
    """
    Add a scheduled feeding task to Firestore and send it to Raspberry Pi.

    JSON Body:
        - schedule_time (str): The scheduled feeding time (e.g. '2025-10-20 15:30:00')
        - cycle (int): Feeding cycle count
        - food (str): Type of food (e.g., 'pellets')

    Args:
        aquarium_id (int): The aquarium ID.

    Returns:
        JSON: Success message or error details.
    """
    try:
        json_req = request.get_json()
        schedule_time = json_req.get("schedule_time")
        food = json_req.get("food")
        job_id = f"{aquarium_id}_schedule_at_{schedule_time}"

        create_schedule(
            aquarium_id=aquarium_id,
            cycle=json_req["cycle"],
            schedule_time=schedule_time,
            job_id=job_id,
            food=food
        )
        send_schedule_raspi(aquarium_id, json_req["cycle"], schedule_time, food, job_id)

        logger.info(f"Created and sent schedule for Aquarium ID {aquarium_id} at {schedule_time}")
        return jsonify({"message": "Successfully added the schedule"}), 200
    except Exception as e:
        logger.exception(f"Failed to create schedule for Aquarium ID {aquarium_id}")
        return jsonify({"error": str(e)}), 500


@schedule_route.route("/task/delete/<int:aquarium_id>", methods=["POST"])
def delete_task(aquarium_id):
    """
    Delete a scheduled feeding task from Firestore.

    JSON Body:
        - document_id (str): The Firestore document ID of the schedule to delete.

    Args:
        aquarium_id (int): The aquarium ID.

    Returns:
        JSON: Success or error message.
    """
    try:
        json_req = request.get_json()
        document_id = json_req.get("document_id")

        if not document_id:
            logger.warning(f"Missing 'document_id' in delete_task request for Aquarium ID {aquarium_id}")
            return jsonify({"error": "Missing required field 'document_id'"}), 400

        delete_schedule_by_id(aquarium_id=aquarium_id, document_id=document_id)

        logger.info(f"Deleted schedule for Aquarium ID {aquarium_id}, Document ID: {document_id}")
        return jsonify({"message": "Successfully removed the schedule"}), 200
    except Exception as e:
        logger.exception(f"Failed to delete schedule for Aquarium ID {aquarium_id}")
        return jsonify({"error": str(e)}), 500


@schedule_route.route("/task_complete/<string:document_id>", methods=["POST"])
def task_complete(document_id):
    """
    Mark a task as complete in Firestore.

    Args:
        document_id (str): Firestore document ID of the completed schedule.

    Returns:
        JSON: Confirmation message or error details.
    """
    try:
        response = set_complete_task(document_id)
        logger.info(f"Task completed for Document ID: {document_id}")
        return jsonify({"message": response}), 200
    except Exception as e:
        logger.exception(f"Failed to mark task complete for Document ID: {document_id}")
        return jsonify({"error": str(e)}), 500
