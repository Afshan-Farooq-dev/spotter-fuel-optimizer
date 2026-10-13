# Postman collection

1. Start Django from the repository root:
   `./backend/.venv/Scripts/python.exe backend/manage.py runserver`.
2. In Postman, click **Import**, then select
   `docs/postman/Spotter-Fuel-Optimizer.postman_collection.json`.
3. Open the imported collection. Its `base_url` defaults to
   `http://127.0.0.1:8000`; no environment import or authentication is required.
4. Run **List stations and capture an ID** before **Station detail**.
   The list's test script sets the collection's `station_id` automatically.
5. Run the entire collection in order using Postman's Collection Runner.

The collection contains health, station-list, station-detail, Texas filtering
and invalid-state requests with response assertions. Expected invalid-state status
is 400; the other requests expect 200. These are read-only requests. Import the
assessment CSV first if the station list is empty.

The generated collection and its resolved HTTP requests were checked locally.
The Postman desktop runner itself was not executed in the automated verification.
