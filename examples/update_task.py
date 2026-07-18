from mettledeck import Client

task_id = input("Task ID: ").strip()
tag = input("Tag name or ID: ").strip()

with Client.connect() as client:
    # Editable fields: title, description, tags (or add_tags/remove_tags), impact,
    # difficulty, progress, time_estimate, planning_description_hidden, media,
    # clear_media, attachments, and remove_attachments. Omitted fields stay unchanged;
    # None clears nullable values.
    task = client.update(task_id, progress=50, add_tags=(tag,) if tag else ())
    print(task.id, task.title)
