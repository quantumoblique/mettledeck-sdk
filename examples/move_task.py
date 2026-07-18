from mettledeck import Client, Position, Workspace

task_id = input("Task ID: ").strip()

with Client.connect() as client:
    task = client.move(
        task_id,
        workspace=Workspace.PLANNING,
        planning_lane=2,
        position=Position.TOP,
    )
    print(task.id, task.location)
