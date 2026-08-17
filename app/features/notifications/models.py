class Notification:
    def __init__(
        self,
        notification_id: int,
        user_id: int,
        notification_text: str,
        is_read: bool = False,
    ):
        self.notification_id = notification_id
        self.user_id = user_id
        self.notification_text = notification_text
        self.is_read = is_read
