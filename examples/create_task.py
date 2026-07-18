from mettledeck import Client

with Client.connect() as client:
    task = client.create(
        title="New task",
        impact=3,
        difficulty=2,
    )
    print(task.id)
