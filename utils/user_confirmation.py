def confirm(question: str, default_answer: bool | None = None) -> bool:
    prompt: str = f"{question} "
    match default_answer:
        case True:
            prompt += "[Y/n]"
        case False:
            prompt += "[y/N]"
        case _:
            prompt += "[y/n]"
    prompt += "\n"

    while True:
        answer = input(prompt).strip().lower()

        if not answer and default_answer is not None:
            return default_answer

        if answer in ["y", "yes"]:
            return True

        if answer in ["n", "no"]:
            return False

        print("Choose 'yes' or 'no'")
