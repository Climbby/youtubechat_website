import pytchat
import time

VIDEO_ID = "XSXEaikz0Bc"
chat = pytchat.create(video_id=VIDEO_ID)

while chat.is_alive():
    for c in chat.get().sync_items():
        print(f"{c.datetime} | {c.author.name}: {c.message}")

    time.sleep(1)