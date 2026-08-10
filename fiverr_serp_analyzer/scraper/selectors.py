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
    "h2",
    "p.text-display-seven",
    "span.co-grey-700",
    "span[class*='total']",
]

# Individual gig card container (CURRENT Fiverr HTML)
GIG_CARD_SELECTORS = [
    "div.basic-gig-card",
    "div.gig-card-layout",
    "div.gig-wrapper",
    "[data-cy='gig-card']",
    "div[class*='gig-card']",
    "a[href*='/gig/']",
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
    "a[href*='/user/'] span",
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
    "a[class*='_0ed0fc'] span span",
    "span[class*='co-grey-1200'] span",
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
    "li",
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

# --- Extra SERP-level fields (Tier 1) ---

SERP_EXTRA_SELECTORS = {
    "seller_country": [
        "img.flag-icon",
        "img[alt*='flag']",
        "img[class*='flag']",
        "span.seller-country",
        "span[class*='country']",
        "span.seller-location",
        "span[class*='location']",
        "div.seller-info span:last-child",
    ],
    "completed_orders": [
        "span.completed-orders",
        "span[class*='completed']",
        "span[class*='orders']",
        "li:contains('order')",
        "span:contains('order')",
        "div.gig-footer span:contains('order')",
    ],
    "delivery_time": [
        "span.delivery-time",
        "span[class*='delivery']",
        "span:contains('day')",
        "li:contains('day')",
        "span[class*='duration']",
    ],
    "fiverr_choice": [
        "span.fiverr-choice-badge",
        "[data-cy='fiverr-choice-badge']",
        "[data-track-tag='fiverr_choice_badge']",
        "span[class*='choice']",
        "span.badge:contains('Fiverr')",
        "div[class*='fiverr-choice']",
        "svg[class*='choice']",
    ],
    "pro_verified": [
        "span.pro-verified",
        "[data-cy='pro-verified-badge']",
        "span[class*='pro-verified']",
        "span[class*='pro_badge']",
        "span.badge:contains('Pro')",
        "div[class*='pro-verified']",
        "svg[class*='pro']",
    ],
    "response_time": [
        "span.response-time",
        "span[class*='response']",
        "span:contains('hour')",
        "span:contains('response')",
        "div[class*='response'] span",
    ],
    "is_online": [
        "span.online-status",
        "span[class*='online']",
        "div.online-dot",
        "span[class*='green-dot']",
        "div[class*='online-indicator']",
        "[data-cy='online-status']",
    ],
}

# --- Gig detail page selectors (Tier 2) ---

GIG_DETAIL_SELECTORS = {
    "full_description": [
        "div.gig-description",
        "div.description-content",
        "div[class*='description']",
        "section.gig-description",
        "[data-cy='gig-description']",
        "div.package-description",
        "article[class*='description']",
    ],
    "packages": [
        "div.pricing-package",
        "div[class*='package']",
        "div.package-card",
        "[data-cy='package-card']",
        "div.tab-content",
        "li.pricing-item",
    ],
    "package_name": [
        "h3.package-name",
        "span.package-title",
        "h3[class*='package']",
        "[data-cy='package-name']",
        "div.package-header h3",
    ],
    "package_price": [
        "span.price",
        "span.package-price",
        "[data-cy='package-price']",
        "span[class*='price']",
        "div.price span",
    ],
    "package_delivery": [
        "span.delivery-days",
        "li:contains('day')",
        "span[class*='delivery']",
        "[data-cy='delivery-time']",
    ],
    "package_revisions": [
        "span.revisions",
        "li:contains('revision')",
        "span[class*='revision']",
        "[data-cy='revisions']",
    ],
    "package_features": [
        "ul.features li",
        "ul[class*='feature'] li",
        "li.feature",
        "div[class*='feature'] li",
        "ul.package-features li",
    ],
    "tags": [
        "a.gig-tag",
        "span.tag",
        "a[class*='tag']",
        "[data-cy='gig-tag']",
        "div.tags a",
        "span[class*='skill']",
    ],
    "faq_section": [
        "div.faq-section",
        "section.faq",
        "div[class*='faq']",
        "[data-cy='faq-section']",
    ],
    "faq_question": [
        "h4",
        "h5",
        "div.faq-question",
        "span[class*='question']",
        "[data-cy='faq-question']",
        "button[class*='accordion']",
    ],
    "faq_answer": [
        "p",
        "div.faq-answer",
        "span[class*='answer']",
        "[data-cy='faq-answer']",
        "div[class*='panel']",
    ],
    "seller_bio": [
        "div.seller-description",
        "div.profile-description",
        "div[class*='seller-bio']",
        "[data-cy='seller-description']",
        "div.about-seller p",
        "section.about p",
    ],
    "seller_country": [
        "span.seller-country",
        "span[class*='location']",
        "span[class*='country']",
        "div.user-location",
        "[data-cy='seller-location']",
        "span:contains('From')",
    ],
    "completed_orders": [
        "span.completed-orders",
        "li:contains('order')",
        "span[class*='completed']",
        "[data-cy='completed-orders']",
    ],
    "languages": [
        "span.language",
        "li:contains('English')",
        "span[class*='language']",
        "div.languages span",
        "[data-cy='seller-languages']",
    ],
    "recent_reviews": [
        "div.review-item",
        "li.review",
        "div[class*='review']:not([class*='rating'])",
        "[data-cy='review-item']",
        "div.seller-review",
    ],
    "review_rating": [
        "span.review-rating",
        "div.stars",
        "span[class*='rating']",
        "svg[class*='star']",
        "[data-cy='review-rating']",
    ],
    "review_text": [
        "p.review-description",
        "div.review-content p",
        "p[class*='review']",
        "[data-cy='review-text']",
    ],
    "review_date": [
        "span.review-date",
        "time",
        "span[class*='date']",
        "[data-cy='review-date']",
        "span:last-child",
    ],
    "review_buyer_country": [
        "span.buyer-country",
        "span.reviewer-country",
        "img.flag-icon",
        "span[class*='country']",
    ],
    "portfolio_count": [
        "div.portfolio-item",
        "div.gallery-item",
        "img[class*='portfolio']",
        "[data-cy='portfolio-item']",
        "div[class*='portfolio'] img",
    ],
    "video": [
        "video",
        "iframe[src*='youtube']",
        "iframe[src*='vimeo']",
        "div.video-player",
        "[data-cy='gig-video']",
        "div[class*='video']",
    ],
}