# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
FitFindr is an AI tool that allows users to shop for second-hand clothing based on the user's prompt. For instance, if a user is looking for a pair of jeans that cost $50 and a size 10, it will display items that meets the user's requirement, which will include the price and condition of the item, such as 'fair', 'excellent', and 'good'. In addition, it will display items that can be paired with the outfit for a complete look, for example 'green jeans pairs will with a white graphic T-shirt. However, if the no item matches the user's description, it (AI tool) will suggest to the user to refine the description prompt and try again.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): "black Levi jeans with flared legs"
- `size` (str): "in a size 8 or 10"
- `max_price` (float): "costing no more that $60"

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->
- Result show display black Levi jeans with flared legs in both sizes, 8 and 10, costing $60 or less.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->
- System failure - It will display a message stating that it's unable to complete the request and the user should try again later.
- Item not found - notifies the user that no item description matches user's prompt and will suggest that the user modify search parameters and try again.

---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
- In general, this functions as a clothing fitness look that displays several items that the user can pair with results from search listings. For example, 'pair jeans with this graphic tee and trainers for a night-out'.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): graphic tees, T-shirt, blouse, tank-tops, blazers
- `wardrobe` (dict): casual, retro, business-casual, formal
- `shoes` (dict): booths, trainers, high-heels, flats, 

**What it returns:**
<!-- Describe the return value -->
- Returns several suggested items that can be paired with jeans to create the user's desired look

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->
- System failure - It will display a message stating that it's unable to complete the request and the user should try again later.
- Item not found - notifies the user that it cannot provide any suggestions and ask the user for input modification.

---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
- Provides a summarized description of the completed outfit look based on user selections

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (description): Item selected from listing and suggested item pair to display a complete description of the OOTD (outfit-of-the-day).

**What it returns:**
<!-- Describe the return value -->
- Returns a completed description of all selected items as well as its associated price.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
- returns nothing, notifies user to modify its parameter in the search-listing.

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->
---
### Tool 4: Price Comparison tool

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
- Displays, based on user's chosen item, comparable price of a similar item, which includes, style and/or color. It will also include prices slightly higher than the user's preference. This will be based on search-listing tool (above)

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): "blue Levi jeans with flared legs"
- `size` (str): "in a size 8 or 10"
- `max_price` (float): "price shown will be capped at 20% more than the original price shown in the search-listing tool"

**What it returns:**
<!-- Describe the return value -->
- Returns a completed description of all selected items as well as its associated price.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
- returns nothing, notifies user to modify its parameter in the search-listing.

---

### Tool 5: Trend awareness 

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
- Generates trend context based on popular style based on user's preference as well as similar style suggestions based on search listing and price

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): "popular jeans pairings"

**What it returns:**
<!-- Describe the return value -->
- Returns popular styles that is based on user's preference in search-listing. This will reference the price comparison tool, which will allow the user to compare price of similar style items

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
- returns nothing, notifies user to modify its parameter in the search-listing.

---

### Tool 6: Style profile memory

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
- This saves user's preferences based on search listing and then uses it to make other style suggestion. The user is able to reference it at a later time. 

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `storage` (str): reference to saved user preferences in the search listing

**What it returns:**
<!-- Describe the return value -->
- Returns a description of saved preferences and suggestions from the search listing

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
- returns nothing, notifies user to modify its parameter in the search-listing.

---

### Tool 7: Retry logic with fallback

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
- If search_listing returns no results, the AI tool can remove filters and performs a new search. It will alert the user of the filters that were removed.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- It will be triggered when search_listing returns no items based on user input

**What it returns:**
<!-- Describe the return value -->
- Returns a generalized result, based on the modified search_listing input

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
- Alerts the user that no items were found after modification(s).

---
## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->
- Based on user prompt using search_listing, calls are made to suggest_outfit and price companion tool to show comparable prices of the same item as well as similar items. Once the user selects the desired item(s). Once the user selects desired items, it will call create_fit_card to create a look and save it in the style_profile_memory for future reference. It'll also reference trend awareness tool to provide additional styles and suggestions based on current trends. If the original prompts fails to produce any result, the retry_logic_with_fallback is activated, and the loop repeats again with the modified suggestions. If no result is generated after modifications from search_listing, then the retry_logic_with_fallback is called again with the message that no results were found.

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->
- If the user selects an item based on result from the search_listing, it saves the item in the suggest_outfit tool, which can be referenced by the trend_awareness tool to generated other suggestions. If no result are found,it will call the retry_logic_with_fallback to retry again with streamlined preference from search_listing. 

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | |
| suggest_outfit | Wardrobe is empty | |
| create_fit_card | Outfit input is missing or incomplete | |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->
- I used Claude as my AI tool of choice for the project. Before any code was generated, I reviewed project requirements as well as associated files to gain a full understanding. I made notes of files that needed to complete the project as well as template files that did not require any change. In addition, I reviewed stretch feature to determine what could be included in the project. Once the planning was completed, I uploaded required files to Claude and stated that I was still planning and no action is required. Once planning was complete, I uploaded my plan and received feedback on my plan.
For example, I created two create_fit_card, with the second to generate another fit. Claude suggested that it wasn't necessary, for I could incorporate fit choices into the main tool, therefore, it was removed. Once I made the modifications, I reviewed the architecture, ensuring that I understood the flow for each tool, and the anticipated results matches with the expected. As a result, I was able to build my project based on project requirements.

**Milestone 3 — Individual tool implementations:**
- Completed in the planning phase, since stretch features was included as part of the planning step. The project contains the following tools:
     - search_listings: searches database based on user input
     - suggest_outfit: suggests outfit pairings based on result from search
     - create_fit_card: creates outfit pairings 
     - retry_with_fallback: error handling 
     - compare_prices: compare prices based on search_listings
     - trend_awareness: suggest trends based on result from search_listing
     - style_profile_memory:saves results for future reference or creates a new list for a new user
- created a test file to test for each tool. All test, 41 in total, passed for each tool
- updated LLM model from `llama3-8b-8192` to `llama-3.1-8b-instant`, as llama3-8b-8192 has been decommissioned. This was flagged when running tools.py 

**Milestone 4 — Planning loop and state management:**
- Loop is initialized at the start of each `run_agent` and the user does not re-enter the same information as follows:
session = {
    "query": str,               # original user query
    "parsed": dict,             # description, size, max_price
    "search_results": list,     # all matching listings
    "selected_item": dict,      # top result → passed into suggest_outfit
    "wardrobe": dict,           # user's wardrobe → passed into suggest_outfit
    "similar_items": list,      # output of compare_prices
    "outfit_suggestion": str,   # output of suggest_outfit → passed into create_fit_card
    "trend_info": str,          # output of trend_awareness
    "fit_card": str,            # output of create_fit_card
    "fallback_message": str,    # set if retry_with_fallback loosened any filters
    "error": str | None,        # set on early exit; None on success
}

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "blue Levi jeans costing no more than $40"

**Step 1:**
<!-- What does the agent do first? Which tool is called? With what input? -->
- it searches the database matching the description, from search_listing
**Step 2:**
<!-- What happens next? What was returned from step 1? What tool is called now? -->
- based on results, it suggest top two styling pair options. It also reference trend_info to show how it compares to trend. 

**Step 3:**
<!-- Continue until the full interaction is complete -->
- If no result is generated, it automatically removes filters and tries again. The error messages generated stage is different from that generated if no item(s) is found.
- If no result after prompt modification, it notifies the user that the item is not found and ask the user to search for another item. 

**Final output to user:**
<!-- What does the user actually see at the end? -->
- Item based on the user's prompt. Also, it will display price comparison for the item as well as similar items that can be paired to create a final look. Furthermore, it'll display a message on recent trends based on the user's selection. Finally, it saves the complete look into profile memory or creates a new style memory for a new user for future reference.
