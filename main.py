from fastapi_poe import make_app
from google_reviews import GoogleReviewsBot

bot = GoogleReviewsBot()
app = make_app(bot, allow_without_key=True)
