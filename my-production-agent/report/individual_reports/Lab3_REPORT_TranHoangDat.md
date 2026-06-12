# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Trần Hoàng Đạt
- **Student ID**: 2A202600807
- **Date**: June 1, 2026

---

## I. Technical Contribution (15 Points)

I implemented the following components to build a production-grade AI Nutrition Agent:

1. **Nutrition Tools Implementation** (`src/tools/nutrition_tools.py`):

   - Created the core business logic functions (`get_user_profile`, `calculate_bmi`, `calculate_bmr`, `calculate_tdee`, `search_food`, `generate_meal_plan`, `validate_meal_plan`, `replace_food`) using strict typed parameters.
   - Built a robust `validate_meal_plan` logic comparing actual totals against target nutrition ranges within configurable tolerances (5% for calories, 10% for macronutrients).
2. **ReAct Agent Loop & Stop Sequences** (`src/agent/agent.py`):

   - Structured the ReAct loop parsing logic to detect `Thought`, `Action: tool_name(args)`, `Observation: ...`, and `Final Answer: ...` blocks using regex.
   - Resolved the critical LLM hallucination issue by incorporating custom `stop` tokens (`["Observation:", "Observation: "]`) passed to the LLMs. This forces the LLM to halt generation immediately after outputting an `Action:` statement, allowing the Python agent execution runtime to run the actual tool and append the real observation.
3. **Telemetry & Resilience Wrapper** (`src/core/gemini_provider.py`):

   - Added token metrics extraction and cost calculation.
   - Wrapped the generation call in a retry-with-exponential-backoff loop to handle Google Gemini rate limit (`ResourceExhausted` 429) errors gracefully.

### Code Highlights

**Gemini Provider Rate Limit Backoff:**

```python
import google.api_core.exceptions
max_retries = 5
retry_delay = 12.0
response = None
for attempt in range(max_retries):
    try:
        response = self.model.generate_content(full_prompt, generation_config=gen_config)
        break
    except google.api_core.exceptions.ResourceExhausted as e:
        if attempt == max_retries - 1:
            raise e
        logger.info(f"Gemini API rate limit hit. Retrying in {retry_delay} seconds...")
        time.sleep(retry_delay)
        retry_delay *= 1.5
```

---

## II. Debugging Case Study (10 Points)

### 1. The Observation Hallucination Bug

- **Problem Description**: During initial testing of Scenario 1 and 2, the agent completed the task in exactly 1 step without running any actual python tools. The LLM generated the entire ReAct loop (actions AND observations) in a single response block.
- **Log Source**: `logs/2026-06-01.log` (Line 18):
  ```json
  {"event": "LLM_RESPONSE", "data": {"content": "Thought: ... Action: get_user_profile(user_id_or_name=\"user_1\")\nObservation: {\"user_id\": \"user_1\", ...}\nFinal Answer: ..."}}
  ```
- **Diagnosis**: The LLM tried to autocomplete the few-shot examples present in the system prompt. Because the model didn't have stop sequences set, it kept writing the observations itself instead of yielding to the execution environment.
- **Solution**: Updated `LLMProvider` signature to accept a `stop` sequence parameter, implemented it across providers, and modified `agent.py` to pass `stop=["Observation:", "Observation: "]`. This forced the LLM to stop generating immediately after outputting `Action:...`.

### 2. Gemini 429 Rate Limits

- **Problem Description**: On the free tier (5 Requests Per Minute / 20 Requests Per Day), multi-step runs frequently throw `ResourceExhausted` exceptions midway.
- **Log Source**: `logs/2026-06-01.log` (Line 34):
  ```
  google.api_core.exceptions.ResourceExhausted: 429 You exceeded your current quota...
  ```
- **Diagnosis**: ReAct requires multiple sequential LLM calls. A single query can hit the LLM 4-5 times in quick succession, exceeding the 5 RPM limits.
- **Solution**: Implemented transient error catching and backoff retry mechanism inside `GeminiProvider.generate`.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning**: The `Thought` block acts as a scratchpad that allows the model to decompose complex goals (e.g. "Weight loss with crab noodle allergy") into structured step-by-step tasks (Profile Lookup -> TDEE calculation -> Diet plan creation -> Exclude ingredient -> Plan validation). A standard chatbot tries to generate the diet plan in one shot, which often leads to inaccurate math or allergen inclusion.
2. **Reliability**: The ReAct Agent performs worse when the LLM is constrained by low API rate limits (e.g., 20 requests per day) since it makes multiple sequential calls per prompt. In such resource-constrained scenarios, a standard chatbot is more cost-efficient and less prone to rate-limiting failures, though less accurate.
3. **Observation**: Observations from tools act as ground-truth feedback. For instance, when `validate_meal_plan` returned `FAIL` (due to being below target calories), the agent observed this result, adapted its plan, and called `generate_meal_plan` again in the next step to adjust the quantities.

---

## IV. Future Improvements (5 Points)

1. **Scalability**: For production, tool execution should be asynchronous or parallelized. For example, looking up the nutritional values of multiple food items in a meal plan should be done concurrently rather than sequentially.
2. **Safety**: Implement a secondary critic LLM or static validator to check that the final output matches all user allergens and macro targets before displaying it to the user.
3. **Performance**: Introduce caching (e.g., Redis) for food nutritional lookups and previous user profiles to avoid querying the LLM or DB for duplicate information, saving token usage and cost.
