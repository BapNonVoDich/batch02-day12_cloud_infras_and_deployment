# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyễn Huy Bảo
- **Student ID**: 2A202600997
- **Date**: 6/1/2026
---

## I. Technical Contribution (15 Points)

*Describe your specific contribution to the codebase (e.g., implemented a specific tool, fixed the parser, etc.).*

- **Modules Implementated**: agent.py, frontend.
- **Code Highlights**: class ReActAgent
- **Documentation**: Build base Chatbot Agent with tool calls & UI UX

---

## II. Debugging Case Study (10 Points)

*Analyze a specific failure event you encountered during the lab using the logging system.*

- **Problem Description**: Agent renerate 1 dish per meal Menu
- **Log Source**: `logs/2026-06-01.log`
- **Diagnosis**: The prompt said to have only 1 dish per meal Menu.
- **Solution**: Changbe the Prompt.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Reflect on the reasoning capability difference.*

1.  **Reasoning**:  khổi Though giúp Chatbot Phân tích yêu cầu của người dùng, xác định xem cần làm gì tiếp theo hoặc đã có đủ thông tin chưa.
2.  **Reliability**: In which cases did the Agent actually perform *worse* than the Chatbot? In cases the Agent need to show some flexibility like adding a Prefered food or ingredient, the Agent will perform worse than the Chatbot.
3.  **Observation**: How did the environment feedback (observations) influence the next steps? The environment feedback (observations) influence the next steps by providing the Agent with the results of the tool calls, which it can then use to make decisions about what to do next.

---

## IV. Future Improvements (5 Points)

*How would you scale this for a production-level AI agent system?*

- **Scalability**: Use real food recipe with portion adjustment to calculate total nutrient more correctly. Use real Ingredient data with all micronutrients to perfectly fulfill User's Condition: allergies, intolerances, prefered food, Prescripttion,... Implement real database to store user data, recipe, history,.... 
- **Safety**: Implement a 'Supervisor' LLM to audit the agent's actions, Prevent Agent from accessing harmful sites or calling harmful tools.
- **Performance**: Use Vector DB for RAG to make it more flexible and powerful.

---

> [!NOTE]
> Submit this report by renaming it to `REPORT_[YOUR_NAME].md` and placing it in this folder.
