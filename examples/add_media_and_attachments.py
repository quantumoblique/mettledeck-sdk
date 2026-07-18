from mettledeck import Client

media = input("Image or video path: ").strip()
attachment = input("Attachment path: ").strip()

with Client.connect() as client:
    task = client.create(
        title="New task with media",
        media=media,
        attachments=(attachment,),
    )
    print(task.id)
