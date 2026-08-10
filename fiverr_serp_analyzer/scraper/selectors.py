"""Centralized CSS/XPath selectors for Fiverr SERP scraping.

All selectors are defined here. Updating a broken selector is a one-line edit.
Each field has an ordered list of fallback selectors; parsers try them in order
and record which one matched.

Updated to match Fiverr's CURRENT HTML structure (verified from live page):
- Gig cards use class "basic-gig-card"
- Title is in <p class="gig-header">
- Seller name is in <a> with class "_1lc1p3l2"
- Rating is in <strong class="rating-score">
- Review count is in <span class="rating-count-number">
- Price is in <span class="text-bold co-grey-1200">
"""

# Fiverr search URL template
FIVERR_SEARCH_URL = "https://www.fiverr.com/search/gigs?query={query}"

# --- SERP-level selectors ---

# Total result count shown by Fiverr
TOTAL_RESULTS_SELECTORS = [
    "span.total-results",
    "[data-cy='total-results']",
    "div.search-results-header p",
    "h1 + p",
    "span[class*='total']",
]

# Individual gig card container (CURRENT Fiverr HTML)
GIG_CARD_SELECTORS = [
    "div.basic-gig-card",
    "div.gig-card-layout",
    "div.gig-wrapper",
    "[data-cy='gig-card']",
    "div[class*='gig-card']",
]

# --- Gig identity selectors ---

GIG_TITLE_SELECTORS = [
    "p.gig-header",
    "a.gig-link h3",
    "h3 a",
    "[data-cy='gig-title']",
    "a[title]",
    "h3",
]

GIG_URL_SELECTORS = [
    "a[aria-label='Go to gig']",
    "a.gig-link",
    "h3 a",
    "[data-cy='gig-link']",
    "a[href*='/gig/']",
]

GIG_ID_SELECTORS = [
    # Extract from URL or data attribute
    "[data-gig-id]",
    "[data-id]",
]

# --- Seller selectors ---

SELLER_NAME_SELECTORS = [
    "a[class*='_1lc1p3l2']",
    "a.seller-name",
    "[data-cy='seller-name']",
    "div.seller-info a",
    "a[href*='/user/']",
    "span.seller-name",
]

SELLER_PROFILE_URL_SELECTORS = [
    "a[class*='_1lc1p3l2']",
    "a.seller-name",
    "[data-cy='seller-name']",
    "a[href*='/user/']",
]

SELLER_LEVEL_SELECTORS = [
    "[data-cy='seller-level']",
    "span.seller-level",
    "div.seller-info span.badge",
    "span[class*='level']",
]

SELLER_RATING_SELECTORS = [
    "strong.rating-score",
    "span.rating-score",
    "[data-cy='seller-rating']",
    "div.rating span",
    "span[class*='rating']",
]

SELLER_REVIEW_COUNT_SELECTORS = [
    "span.rating-count-number",
    "span.rating-count",
    "[data-cy='review-count']",
    "div.rating a",
    "a[href*='reviews']",
]

# --- Gig detail selectors ---

STARTING_PRICE_SELECTORS = [
    "span.text-bold.co-grey-1200",
    "span.price",
    "[data-cy='gig-price']",
    "div.price-wrapper span",
    "span[class*='price']",
    "footer span",
]

CURRENCY_SELECTORS = [
    # Usually embedded in price text
]

DELIVERY_TIME_SELECTORS = [
    "span.delivery-time",
    "[data-cy='delivery-time']",
    "span[class*='delivery']",
    "li:contains('delivery')",
]

PACKAGE_COUNT_SELECTORS = [
    # Often not directly visible on SERP
]

BADGES_SELECTORS = [
    "span.badge",
    "[data-cy='gig-badge']",
    "div.badges span",
    "span[class*='badge']",
    "[data-track-tag='fiverr_choice_badge']",
]

CATEGORY_SELECTORS = [
    # Usually in breadcrumb or tag area
    "a.category-link",
    "[data-cy='category']",
]

SERVICE_TAGS_SELECTORS = [
    "span.tag",
    "[data-cy='service-tag']",
    "div.tags span",
    "span[class*='tag']",
]

# --- Challenge detection selectors ---

CHALLENGE_TITLE_MARKERS = [
    "verify you are human",
    "security check",
    "are you a robot",
    "captcha",
    "one more step",
    "please verify",
    "unusual traffic",
    "access denied",
    "just a moment",
]

CHALLENGE_DOM_SELECTORS = [
    "div#captcha",
    "div.captcha",
    "iframe[src*='captcha']",
    "iframe[src*='recaptcha']",
    "iframe[src*='hcaptcha']",
    "div.g-recaptcha",
    "div.h-captcha",
    "div[class*='challenge']",
    "div#challenge-stage",
    "div#px-captcha",
    "form#challenge-form",
]

CHALLENGE_BODY_MARKERS = [
    "verify you are human",
    "security check",
    "are you a robot",
    "unusual traffic from your computer",
    "we've detected unusual activity",
    "please verify you're a human",
    "complete the security check",
    "access to this page has been denied",
    "your request has been blocked",
]