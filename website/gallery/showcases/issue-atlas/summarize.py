from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chatlas import Chat

MODEL = "claude-haiku-5-5"
SYSTEM_PROMPT = """\
You are reviewing GitHub issues from the Shiny ecosystem (R and Python Shiny, bslib, htmltools, \
shinywidgets, shinychat, shinytest2, shinydashboard, Shiny Server). You get the titles of a group \
of issues a maintainer selected on a map. In at most 3 short sentences of plain text (no lists, \
no markdown), say what these issues have in common and what single change would resolve the \
most of them."""


async def summarize(titles: list[str], chat: "Chat") -> str:
    prompt = "Issue titles:\n" + "\n".join(f"- {t}" for t in titles)
    try:
        response = await chat.chat_async(prompt, echo="none")
        return (await response.get_content()).strip()
    except Exception as e:
        reason = (str(e).splitlines() or [type(e).__name__])[0][:160]
        return f"Couldn't reach the model: {reason}"


def make_chat() -> "Chat":
    # Lazy: chatlas is only needed for the summarize button, which also
    # requires ANTHROPIC_API_KEY; the atlas itself runs without either.
    from chatlas import ChatAnthropic

    return ChatAnthropic(model=MODEL, system_prompt=SYSTEM_PROMPT)
