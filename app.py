"""
app.py

Gradio interface for FitFindr.

Run with:
    python app.py

Then open the localhost URL shown in your terminal (usually http://localhost:7860).
"""

import gradio as gr

from agent import run_agent
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ── wardrobe choice constants ─────────────────────────────────────────────────

WARDROBE_EXAMPLE = "Example wardrobe"
WARDROBE_EMPTY = "Empty wardrobe (new user)"


# ── query handler ─────────────────────────────────────────────────────────────

def handle_query(user_query: str, wardrobe_choice: str) -> tuple[str, str, str, str, str]:
    """
    Called by Gradio when the user submits a query.

    Returns a tuple of five strings:
        (listing_text, similar_items_text, outfit_suggestion, trend_info, fit_card)
    """
    if not user_query or not user_query.strip():
        return "Please enter a search query.", "", "", "", ""

    wardrobe = (
        get_example_wardrobe()
        if wardrobe_choice == WARDROBE_EXAMPLE
        else get_empty_wardrobe()
    )

    session = run_agent(query=user_query, wardrobe=wardrobe)

    # ── Error: no results found even after fallback ──────────────────────────
    if session["error"]:
        return session["error"], "", "", "", ""

    item = session["selected_item"]

    # ── Format top listing ───────────────────────────────────────────────────
    listing_lines = [
        f"✅ {item['title']}",
        f"💰 ${item['price']} — {item['condition'].capitalize()} condition",
        f"📦 {item['platform'].capitalize()}   |   Size: {item['size']}",
        f"🎨 Colors: {', '.join(item['colors'])}",
        f"🏷️  Tags: {', '.join(item['style_tags'])}",
    ]
    if item.get("brand"):
        listing_lines.append(f"👕 Brand: {item['brand']}")
    if session.get("fallback_message"):
        listing_lines.append(f"\n⚠️  {session['fallback_message']}")
    listing_text = "\n".join(listing_lines)

    # ── Format similar items ─────────────────────────────────────────────────
    similar = session.get("similar_items", [])
    if similar:
        sim_lines = ["Similar items you might also like:\n"]
        for s in similar:
            sim_lines.append(
                f"• {s['title']}\n"
                f"  ${s['price']} — {s['condition']} — {s['platform']}"
            )
        similar_text = "\n".join(sim_lines)
    else:
        similar_text = "No similar items found in this price range."

    outfit_text = session.get("outfit_suggestion") or "No outfit suggestion available."
    trend_text = session.get("trend_info") or "No trend info available."
    fitcard_text = session.get("fit_card") or "No fit card generated."

    return listing_text, similar_text, outfit_text, trend_text, fitcard_text


# ── interface ─────────────────────────────────────────────────────────────────

EXAMPLE_QUERIES = [
    "vintage graphic tee under $30",
    "90s track jacket in size M",
    "flowy midi skirt under $40",
    "black combat boots size 8",
    "designer ballgown size XXS under $5",
]


def build_interface():
    with gr.Blocks(title="FitFindr 🛍️", theme=gr.themes.Soft()) as demo:
        gr.Markdown("""
# FitFindr 🛍️
**Find secondhand pieces and get outfit ideas based on your wardrobe.**
Describe what you're looking for — include size and price if you want to filter.
        """)

        with gr.Row():
            query_input = gr.Textbox(
                label="What are you looking for?",
                placeholder="e.g. vintage graphic tee under $30, size M",
                lines=2,
                scale=3,
            )
            wardrobe_choice = gr.Radio(
                choices=[WARDROBE_EXAMPLE, WARDROBE_EMPTY],
                value=WARDROBE_EXAMPLE,
                label="Wardrobe",
                scale=1,
            )

        submit_btn = gr.Button("Find it ✨", variant="primary")

        with gr.Row():
            listing_output = gr.Textbox(
                label="🛍️ Top listing found",
                lines=9,
                interactive=False,
            )
            similar_output = gr.Textbox(
                label="💸 Price comparison",
                lines=9,
                interactive=False,
            )

        with gr.Row():
            outfit_output = gr.Textbox(
                label="👗 Outfit idea",
                lines=9,
                interactive=False,
            )
            trend_output = gr.Textbox(
                label="📈 Trend context",
                lines=9,
                interactive=False,
            )

        fitcard_output = gr.Textbox(
            label="✨ Your fit card",
            lines=5,
            interactive=False,
        )

        gr.Examples(
            examples=[[q, WARDROBE_EXAMPLE] for q in EXAMPLE_QUERIES],
            inputs=[query_input, wardrobe_choice],
            label="Try these queries",
        )

        outputs = [listing_output, similar_output, outfit_output, trend_output, fitcard_output]

        submit_btn.click(
            fn=handle_query,
            inputs=[query_input, wardrobe_choice],
            outputs=outputs,
        )
        query_input.submit(
            fn=handle_query,
            inputs=[query_input, wardrobe_choice],
            outputs=outputs,
        )

    return demo


if __name__ == "__main__":
    demo = build_interface()
    demo.launch()