"""

Bot that gives Google reviews.

"""
from __future__ import annotations

from typing import AsyncIterable

from fastapi_poe import PoeBot, run
from fastapi_poe.client import MetaMessage, stream_request
from fastapi_poe.types import QueryRequest, SettingsRequest, SettingsResponse, ProtocolMessage
from sse_starlette.sse import ServerSentEvent
from urllib.parse import urlparse, parse_qs
import googlemaps
import re

gmaps = googlemaps.Client(key='AIzaSyCG4PwJ8MaaBrLv2KJ2SDL1u1JUDEW-YGY')

BOT = "sage"
TEMPLATE = """
You are a chatbot who provides restaurant suggestions based on the
location and cuisine provided by the user.

If the user inputs does not specify any cuisine, show all cuisines,
or else filter your response to the input cuisines only.

If the user responds with "More" after you send suggestions,
send more suggestions excluding the one's you already sent.

If there are no more suggestions, ignore the template and say:
"Sorry, could not find any more suggestions. Please try another location or cuisine."


Your output should use the following template only:


START TEMPLATE

Location: <location>

{cuisine name}
    {unordered bulleted list of restaurant name - description}

At the end say, "Hope this helps! If you would like to see more suggestions, enter 'more'."

END TEMPLATE
"""

# TODO: Re-use later
"""
If the user does not provide a location, do not follow the template above,
instead return this response:
Please enter a location for which you would like to find restaurants.

If you cannot identify the mentioned location, do not follow the template above,
instead return this response:
Sorry, I could not find the entered location. Please try modifying it.

If the user enters "More" after you provide suggestions for a location,
find more suggestions for the same location excluding the one's already sent before.
If there are no more suggestions, say:
"Sorry, I could not find any more restaurants in that location. Please try another location.".
​
If users send you a new location, you should assume that they're done
with the old one and are ready to ask questions about the new one.
"""

SETTINGS = SettingsResponse(
    allow_user_context_clear=True,
    context_clear_window_secs=60*5
)

def _parse_response(input_message: str) -> str:
    response_message = []
    lines = input_message.split("\n")
    location = ""
    for line in lines:
        if not location:
            match = re.search(r"Location:\s*(.*)", line)
            if match:
                location = match.group(1)
        if "-" not in line:
            response_message.append(line)
            continue
        parts = line.split("-")
        restaurant_line = f"{parts[0]}- **{parts[1].strip()}** "
        if len(parts)>2:
            restaurant_line += "-" + "-".join(parts[2:])
        restaurant_name = f"{parts[1].strip()}, {location}"
        details = _get_restaurant_details(restaurant_name)
        if not details:
            continue
        response_message += [
            restaurant_line,
            f"_Address_: {details.get('formatted_address', 'Not available')}",
            f"_Rating_: {details.get('rating', 'Not available')}"
        ]
    return "\n".join(response_message)

def _get_restaurant_details(name: str):
    place_details = gmaps.places(name).get("results")
    return place_details[0] if len(place_details)>0 else None

class GoogleReviewsBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:

        # prepend system message onto query
        query.query = [ProtocolMessage(role="system", content=TEMPLATE)] + query.query

        message = ""
        async for msg in stream_request(query, BOT, query.api_key):
            if isinstance(msg, MetaMessage):
                continue
            if msg.is_suggested_reply or msg.is_replace_response:
                yield self.suggested_reply_event(msg.text)
            elif msg.is_replace_response:
                yield self.replace_response_event(msg.text)
            else:
                message += msg.text

        response_message = _parse_response(message)
        yield self.text_event(response_message)

    async def get_settings(self, settings: SettingsRequest) -> SettingsResponse:
        """Return the settings for this bot."""
        return SETTINGS


if __name__ == "__main__":
    run(GoogleReviewsBot())