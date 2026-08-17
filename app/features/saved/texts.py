class SavedTexts:
    TITLE = "Сохраненные объявления"
    EMPTY_SAVED_MESSAGE = "💔 У тебя пока нет сохраненных объявлений."

    @staticmethod
    def contact_info_text(username: str | None) -> str:
        if username:
            return f"📝 Свяжись с репетитором: @{username}"
        return (
            "😥 У репетитора не указан username.\n"
            "Попробуй найти контактную информацию в тексте объявления."
        )
