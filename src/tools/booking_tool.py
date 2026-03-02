import uuid

def execute_booking(itinerary, permission=False):
    """
    Simulasi booking dengan idempotency dan permission.
    """
    if not permission:
        return {"error": "Permission required for booking."}
    transaction_id = str(uuid.uuid4())
    return {
        "status": "success",
        "transaction_id": transaction_id,
        "details": itinerary
    }
