from mettledeck import Client

with Client.connect() as client:
    for tasks in client.watch_tasks(interval=1.0):
        print(f"Project changed ({len(tasks)} tasks)")
        for task in tasks:
            print(task.id, task.title)
