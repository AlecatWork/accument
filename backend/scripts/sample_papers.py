"""Built-in fictional demo papers, so you can ask the AI questions without uploading anything.

They deliberately come in five different file formats to show that Accument can read them all.

Each sample has:
  * the paper itself (`pages` for PDFs, `text` for the other formats)
  * `reading_status`  - where it sits in the "To read / Reading / Done" donut
  * `notes`           - a few example notes
  * `chats`           - example questions: (question, answer, page, days_ago, thumbs)
                        These fill the dashboard charts with believable history.
"""

SAMPLES = [
    {
        "filename": "widget-learning.pdf",
        "format": "pdf",
        "pages": [
            "Widget Learning for Small Labs\nAuthor: Ada Example\nYear: 2024\n\n"
            "Main idea: a widget is trained on 500 labeled diagrams so a small lab can classify captions "
            "without a huge dataset. Small labs rarely have thousands of labeled examples, so this paper asks "
            "how far a modest, carefully labeled collection can go. Earlier approaches needed far more data "
            "and far more computing power than a small lab can afford.",
            "Method: the model uses a 3-layer encoder. The learning rate is 0.001. The batch size is 16. "
            "Each diagram has an English caption label. Training runs for 20 rounds over the data. Diagrams "
            "were drawn by lab members and checked by a second person, which kept labeling mistakes low. "
            "No outside data was used for pre-training.",
            "Results: accuracy is 91.5% on the test set. The test set holds 100 diagrams that were never used "
            "for training. Limitation: it only works on English captions. We did not test other languages. "
            "Future work: try more languages and test whether 250 diagrams would be enough.",
        ],
        "reading_status": "done",
        "notes": [
            "Great example of doing a lot with little data. Cite in the literature review.",
            "Check: would 250 diagrams really be enough? The authors only suggest it.",
            "Limitation to remember: English captions only.",
        ],
        "chats": [
            ("How many diagrams were used to train the widget?", "The widget was trained on 500 labeled diagrams [1].", 1, 1, "up"),
            ("What accuracy did it reach?", "It reached 91.5% accuracy on the test set of 100 unseen diagrams [1].", 3, 3, "up"),
            ("Does it work in other languages?", "No. It only works on English captions, and other languages were not tested [1].", 3, 9, "up"),
            ("What learning rate and batch size were used?", "The learning rate was 0.001 and the batch size was 16 [1].", 2, 12, None),
        ],
    },
    {
        "filename": "gadget-classification.pdf",
        "format": "pdf",
        "pages": [
            "Gadget Classification at Home\nAuthor: Ben Sample\nYear: 2023\n\n"
            "Main idea: a gadget classifier trained on 120 photos taken with ordinary phones. The goal is a "
            "tool a hobbyist can build in an afternoon, without special equipment or a large photo archive.",
            "Method: the model uses a 2-layer encoder. The learning rate is 0.01. The batch size is 8. "
            "Photos were taken in kitchens and garages, then labeled by the author. Results: accuracy is 84% "
            "on the test set. Limitation: photos must be well lit, because accuracy drops sharply in dim rooms.",
        ],
        "reading_status": "done",
        "notes": ["Compare the 84% accuracy here with the widget paper's 91.5%. Different data, but interesting."],
        "chats": [
            ("What accuracy does the gadget classifier get?", "It reaches 84% accuracy on the test set [1].", 2, 5, "up"),
            ("What is the main limitation?", "Photos must be well lit, because accuracy drops sharply in dim rooms [1].", 2, 15, "down"),
        ],
    },
    {
        "filename": "sleep-and-memory.docx",
        "format": "docx",
        "text": (
            "Sleep and Memory in University Students\n\n"
            "Author: Priya Sample. Year: 2022.\n\n"
            "Introduction\n\n"
            "Students often trade sleep for study time before exams. This study asks whether that trade pays "
            "off, by measuring how well students remember new material after nights of different lengths.\n\n"
            "Method\n\n"
            "We followed 240 university students for 8 weeks. Each week they learned a list of 40 new words "
            "and were tested on recall the next day. Students kept a sleep diary, noting bedtime, wake-up time "
            "and any naps.\n\n"
            "Results\n\n"
            "Students who slept at least 7 hours scored 12% higher on the recall test than students who slept "
            "less. A nap of about 20 minutes in the afternoon improved evening recall by 5%. The effect of "
            "sleep was larger for harder word lists than for easy ones.\n\n"
            "Limits\n\n"
            "Sleep was self-reported in diaries, so some entries may be inaccurate. All participants came from "
            "one university, which may limit how far the findings apply elsewhere."
        ),
        "reading_status": "reading",
        "notes": [
            "Useful for the wellbeing chapter: 7 hours is the threshold they highlight.",
            "Self-reported sleep is a weakness. Look for a study with wearable data.",
        ],
        "chats": [
            ("How many students took part and for how long?", "The study followed 240 university students for 8 weeks [1].", 1, 0, "up"),
            ("What did sleeping 7 hours or more change?", "Students who slept at least 7 hours scored 12% higher on the recall test [1].", 1, 2, "up"),
            ("Did naps help?", "Yes. A nap of about 20 minutes improved evening recall by 5% [1].", 1, 6, "up"),
            ("How was sleep measured?", "Sleep was self-reported in diaries, which is one of the study's limits [1].", 1, 20, None),
        ],
    },
    {
        "filename": "urban-bees.md",
        "format": "md",
        "text": (
            "# Urban Beekeeping and Local Pollination\n\n"
            "**Author:** Tomas Fictional  \n**Year:** 2021\n\n"
            "## Summary\n\n"
            "Cities are not only for pigeons. This paper asks whether rooftop beehives help the plants growing "
            "in nearby community gardens.\n\n"
            "## Method\n\n"
            "We placed 14 rooftop hives across 3 neighborhoods and compared nearby community gardens with "
            "similar gardens that had no hives within 500 metres. We counted how many flowers turned into "
            "fruit over one growing season.\n\n"
            "## Results\n\n"
            "Fruit set was 18% higher in gardens within 500 metres of a hive. However, 22% of the hives were "
            "lost over the winter, mostly to cold and to a shortage of late-season flowers.\n\n"
            "## Recommendation\n\n"
            "Cities should plant a diverse mix of flowers that bloom from early spring to late autumn, so "
            "bees have food all season and fewer hives are lost."
        ),
        "reading_status": "to_read",
        "notes": [],
        "chats": [
            ("How much did fruit production improve near the hives?", "Fruit set was 18% higher in gardens within 500 metres of a hive [1].", 1, 4, "up"),
            ("How many hives were lost in winter?", "22% of the hives were lost over the winter [1].", 1, 21, "up"),
        ],
    },
    {
        "filename": "cold-brew-coffee.html",
        "format": "html",
        "text": (
            "<html><head><title>Cold Brew Coffee: Extraction and Taste</title>"
            "<style>body{font-family:sans-serif}</style></head><body>"
            "<h1>Cold Brew Coffee: Extraction and Taste</h1>"
            "<p>Author: L. Okafor-Demo. Year: 2023.</p>"
            "<h2>Question</h2>"
            "<p>Does steeping coffee for longer in the fridge beat a quicker steep at room temperature?</p>"
            "<h2>Method</h2>"
            "<p>We brewed coffee two ways with the same coarse grind and a 1 to 8 coffee-to-water ratio: "
            "12 hours at 4 degrees Celsius in the fridge, and 8 hours at room temperature. Then 48 tasters "
            "compared the two without knowing which was which.</p>"
            "<h2>Results</h2>"
            "<p>Of the 48 tasters, 31 preferred the 12-hour fridge brew. The fridge brew also contained "
            "about 9% less caffeine per cup, and tasters described it as smoother and less bitter.</p>"
            "<h2>Limitations</h2>"
            "<p>Only one kind of bean was tested, and all tasters were office workers.</p>"
            "<script>console.log('ignored')</script></body></html>"
        ),
        "reading_status": "to_read",
        "notes": ["Try this at home: 12 hours in the fridge, 1 to 8 ratio."],
        "chats": [
            ("Which brew did tasters prefer?", "31 of the 48 tasters preferred the 12-hour fridge brew [1].", 1, 7, "up"),
            ("Was there a caffeine difference?", "The fridge brew had about 9% less caffeine per cup [1].", 1, 26, None),
        ],
    },
]
