"""Questions for measuring policy search.

Each case says what a correct router would answer (intent) and which policy chunk
should be found (expected = "policy-slug/Section heading").

Add your own cases at the bottom, in OWN_CASES, in the words a real customer would
use. Keep them out of any tuning so they stay an honest held-out test.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SearchCase:
    id: str
    query: str
    intent: str
    expected: str
    tag: str


CASES = [
    # plain English
    SearchCase("en-01", "how many hours do I have to report a damaged product", "damaged_item", "damaged-item/Reporting window", "english"),
    SearchCase("en-02", "do I need to send a photo of the broken item", "damaged_item", "damaged-item/Evidence required", "english"),
    SearchCase("en-03", "can I get a replacement for my cracked phone", "damaged_item", "damaged-item/Resolution", "english"),
    SearchCase("en-04", "I got a different colour than I ordered, does that count as a wrong item", "wrong_item", "wrong-item/What counts as a wrong item", "english"),
    SearchCase("en-05", "how long can I wait before reporting the wrong product I received", "wrong_item", "wrong-item/Reporting window", "english"),
    SearchCase("en-06", "my order is 5 days past the expected date and not here, can I cancel", "late_delivery", "late-delivery/What the customer can ask for", "english"),
    SearchCase("en-07", "when does an order count as late", "late_delivery", "late-delivery/When an order counts as late", "english"),
    SearchCase("en-08", "when will the money reach my bank account", "refund_status", "refund-timing/When the money arrives", "english"),
    SearchCase("en-09", "how soon do you start my refund after it is approved", "refund_status", "refund-timing/When a refund starts", "english"),
    SearchCase("en-10", "my refund was started 8 business days ago and nothing arrived", "refund_status", "refund-timing/Customers asking about a refund", "english"),
    # Hinglish
    SearchCase("hi-01", "mera order abhi tak nahi aaya, kitne din baad cancel kar sakte hain", "late_delivery", "late-delivery/What the customer can ask for", "hinglish"),
    SearchCase("hi-02", "paisa bank account mein kab tak aayega", "refund_status", "refund-timing/When the money arrives", "hinglish"),
    SearchCase("hi-03", "phone ki screen toot gayi thi, kitne ghante mein batana hai", "damaged_item", "damaged-item/Reporting window", "hinglish"),
    SearchCase("hi-04", "galat item aaya hai, photo bhejni padegi kya", "wrong_item", "wrong-item/Evidence required", "hinglish"),
    SearchCase("hi-05", "order delivery date ke 4 din baad aaya, kya mujhe kuch milega", "late_delivery", "late-delivery/Orders that were already delivered late", "hinglish"),
    SearchCase("hi-06", "refund approve hone ke kitne ghante baad shuru hota hai", "refund_status", "refund-timing/When a refund starts", "hinglish"),
    # longer, realistic complaints
    SearchCase("long-01", "I ordered a blender and it reached with a crack in the jar. It was delivered yesterday evening. What can you do for me?", "damaged_item", "damaged-item/Resolution", "long"),
    SearchCase("long-02", "I received headphones but the box had speakers inside instead. Can I swap them?", "wrong_item", "wrong-item/Resolution", "long"),
    SearchCase("long-03", "The package was supposed to come on the 10th, today is the 15th and still nothing. I want my money back.", "late_delivery", "late-delivery/What the customer can ask for", "long"),
    SearchCase("long-04", "My order showed delivered two days after the promised date and I am really upset about it.", "late_delivery", "late-delivery/Orders that were already delivered late", "long"),
    # typos
    SearchCase("typo-01", "wen will mony reach my acount", "refund_status", "refund-timing/When the money arrives", "typo"),
    SearchCase("typo-02", "my order is delayd, can i cancle it", "late_delivery", "late-delivery/What the customer can ask for", "typo"),
    # tricky: the answer is a specific detail in the policy
    SearchCase("tricky-01", "is it ok to send only a photo of the box and not the item", "damaged_item", "damaged-item/Evidence required", "tricky"),
    SearchCase("tricky-02", "what if I report the damage after 2 days", "damaged_item", "damaged-item/Reporting window", "tricky"),
    SearchCase("tricky-03", "I got size M instead of L, is that a wrong item", "wrong_item", "wrong-item/What counts as a wrong item", "tricky"),
    SearchCase("tricky-04", "my refund reached the bank after 10 days, is that normal", "refund_status", "refund-timing/Customers asking about a refund", "tricky"),
]

# Your own cases go here (3 or 4 to start). Example:
# SearchCase("own-01", "your question", "damaged_item", "damaged-item/Reporting window", "own"),
OWN_CASES: list[SearchCase] = []

ALL_CASES = CASES + OWN_CASES
