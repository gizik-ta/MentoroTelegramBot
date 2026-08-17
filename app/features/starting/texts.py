from dataclasses import dataclass


@dataclass
class StartTexts:
    GREETINGS_MESSAGE: str = (
        "\n    👋 <b>Добро пожаловать в UPGrade!</b>\n\n"
        "Здесь ты можешь найти ученика или репетитора, задать вопрос и "
        "получить понятный ответ от эксперта.\n    "
    )
