from mettledeck import Client

with Client.connect() as client:
    # list() can filter by workspace, column, planning_lane, and tags.
    for task in client.list():
        print(task.id, task.title)
